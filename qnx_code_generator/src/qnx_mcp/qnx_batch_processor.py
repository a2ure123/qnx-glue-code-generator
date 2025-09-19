#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QNX Batch Processor Final - Hybrid API Mode
Complete pipeline: Web Crawl -> JSON Extract -> Hybrid Embed -> Store
"""

import os
import sys
import json
import logging
import time
import threading
import sqlite3
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from queue import Queue, Empty

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from qnx_web_crawler import QNXWebCrawler, QNXFunction
from claude_json_extractor import ClaudeJSONExtractor
from hybrid_vectorizer import HybridVectorizer, VectorizeTask, VectorizeResult
from qnx_gdb_type_enhancer import QNXGDBTypeEnhancer

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class ProcessingStats:
    """Processing statistics"""
    total_functions: int = 0
    crawled: int = 0
    json_extracted: int = 0
    vectorized: int = 0
    stored: int = 0
    failed: int = 0
    processing_time: float = 0.0
    api_usage: Dict[str, int] = None
    errors: List[str] = None
    
    def __post_init__(self):
        if self.api_usage is None:
            self.api_usage = {}
        if self.errors is None:
            self.errors = []

def serialize_function_info(obj):
    """Custom JSON serialization function"""
    # Handle dataclass objects
    if hasattr(obj, '__dataclass_fields__'):
        return asdict(obj)
    # Handle objects with __dict__ attribute
    elif hasattr(obj, '__dict__'):
        return {k: serialize_function_info(v) for k, v in obj.__dict__.items()}
    # Handle namedtuple
    elif hasattr(obj, '_asdict'):
        return obj._asdict()
    # Handle lists and tuples
    elif isinstance(obj, (list, tuple)):
        return [serialize_function_info(item) for item in obj]
    # Handle dictionaries
    elif isinstance(obj, dict):
        return {key: serialize_function_info(value) for key, value in obj.items()}
    # Other basic types
    else:
        return obj

class QNXBatchProcessor:
    """QNX Batch Processor - Supports complete A-Z function crawling"""
    
    def __init__(self, config_path: str = "config.json"):
        """Initialize processor"""
        # Save config path for multithreading
        self.config_path = config_path
        
        # Load configuration
        self.config = self._load_config(config_path)
        
        # Initialize components
        self.crawler = QNXWebCrawler(config_path)
        # Enable GDB enhancement by default
        self.json_extractor = ClaudeJSONExtractor(config_path, enable_gdb_in_extraction=True)
        self.vectorizer = HybridVectorizer(config_path)
        
        # Output settings
        self.output_dir = Path("./data/processed_functions")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize GDB type enhancer
        self.gdb_enhancer = QNXGDBTypeEnhancer(config_path)
        
        # GDB async processing setup
        self.gdb_queue = Queue()
        self.gdb_results = {}
        self.gdb_thread = None
        self.gdb_stop_flag = threading.Event()
        self.gdb_db_path = self.output_dir / "gdb_tasks.db"
        
        # Statistics
        self.stats = ProcessingStats()
        
        # Processing settings
        processing_config = self.config.get("processing_settings", {})
        self.max_worker_threads = processing_config.get("max_worker_threads", 3)
        self.api_delay_range = processing_config.get("api_request_delay_range", [0.5, 2.0])
        self.enable_multithreading = processing_config.get("enable_multithreading", True)
        
        # Batch settings
        self.embedding_batch_size = 10  # Process 10 function names per embedding batch
        
        logger.info("QNX Batch Processor Final initialized")
        logger.info(f"Embedding batch size: {self.embedding_batch_size}")
        logger.info(f"Output directory: {self.output_dir}")
        logger.info(f"Max worker threads: {self.max_worker_threads}")
        logger.info(f"Multithreading enabled: {self.enable_multithreading}")
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration file"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load config file: {e}")
            return {}

    def _init_gdb_database(self):
        """Initialize SQLite database for GDB task queue"""
        try:
            conn = sqlite3.connect(str(self.gdb_db_path))
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS gdb_tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    function_name TEXT UNIQUE,
                    json_data TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    processed_at TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS gdb_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    function_name TEXT UNIQUE,
                    enhanced_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("GDB database initialized")
        except Exception as e:
            logger.error(f"Failed to initialize GDB database: {e}")

    def _gdb_consumer_worker(self):
        """GDB consumer worker thread"""
        logger.info("GDB consumer worker started")
        
        while not self.gdb_stop_flag.is_set():
            try:
                # Check for tasks in database
                conn = sqlite3.connect(str(self.gdb_db_path))
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT function_name, json_data FROM gdb_tasks 
                    WHERE status = 'pending' 
                    ORDER BY created_at 
                    LIMIT 1
                ''')
                
                task = cursor.fetchone()
                
                if task:
                    function_name, json_data_str = task
                    logger.info(f"Processing GDB enhancement for: {function_name}")
                    
                    try:
                        # Parse JSON data
                        json_data = json.loads(json_data_str)
                        
                        # Enhance function parameters using GDB
                        if 'parameters' in json_data:
                            enhanced_params = self.gdb_enhancer.enhance_function_parameters(
                                json_data['parameters']
                            )
                            json_data['parameters'] = enhanced_params
                        
                        # Mark task as processed
                        cursor.execute('''
                            UPDATE gdb_tasks 
                            SET status = 'completed', processed_at = CURRENT_TIMESTAMP 
                            WHERE function_name = ?
                        ''', (function_name,))
                        
                        # Store enhanced result
                        cursor.execute('''
                            INSERT OR REPLACE INTO gdb_results 
                            (function_name, enhanced_data) 
                            VALUES (?, ?)
                        ''', (function_name, json.dumps(json_data)))
                        
                        conn.commit()
                        logger.debug(f"GDB enhancement completed for: {function_name}")
                        
                    except Exception as e:
                        logger.error(f"GDB enhancement failed for {function_name}: {e}")
                        cursor.execute('''
                            UPDATE gdb_tasks 
                            SET status = 'failed', processed_at = CURRENT_TIMESTAMP 
                            WHERE function_name = ?
                        ''', (function_name,))
                        conn.commit()
                
                conn.close()
                
                # Sleep before checking for next task
                time.sleep(1.0)
                
            except Exception as e:
                logger.error(f"GDB worker error: {e}")
                time.sleep(5.0)
        
        logger.info("GDB consumer worker stopped")

    def start_gdb_processing(self):
        """Start async GDB processing"""
        if self.gdb_thread and self.gdb_thread.is_alive():
            return
        
        # Initialize database
        self._init_gdb_database()
        
        # Start worker thread
        self.gdb_stop_flag.clear()
        self.gdb_thread = threading.Thread(target=self._gdb_consumer_worker, daemon=True)
        self.gdb_thread.start()
        logger.info("GDB async processing started")

    def stop_gdb_processing(self):
        """Stop async GDB processing"""
        if self.gdb_thread and self.gdb_thread.is_alive():
            self.gdb_stop_flag.set()
            self.gdb_thread.join(timeout=10)
            logger.info("GDB async processing stopped")

    def enqueue_gdb_task(self, function_name: str, json_data: Dict[str, Any]):
        """Enqueue function for GDB enhancement"""
        try:
            conn = sqlite3.connect(str(self.gdb_db_path))
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO gdb_tasks 
                (function_name, json_data, status) 
                VALUES (?, ?, 'pending')
            ''', (function_name, json.dumps(json_data)))
            
            conn.commit()
            conn.close()
            logger.debug(f"Enqueued GDB task for: {function_name}")
        except Exception as e:
            logger.error(f"Failed to enqueue GDB task for {function_name}: {e}")

    def get_gdb_results(self) -> Dict[str, Dict[str, Any]]:
        """Get all completed GDB enhancement results"""
        try:
            conn = sqlite3.connect(str(self.gdb_db_path))
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT function_name, enhanced_data 
                FROM gdb_results
            ''')
            
            results = {}
            for function_name, enhanced_data_str in cursor.fetchall():
                try:
                    results[function_name] = json.loads(enhanced_data_str)
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse GDB result for {function_name}")
            
            conn.close()
            return results
        except Exception as e:
            logger.error(f"Failed to get GDB results: {e}")
            return {}
    
    def crawl_functions(self, function_names: List[str]) -> List[QNXFunction]:
        """Crawl function documentation"""
        logger.info(f"Starting to crawl {len(function_names)} functions")
        
        functions = self.crawler.crawl_functions(function_names)
        
        self.stats.crawled = len(functions)
        logger.info(f"Successfully crawled {self.stats.crawled} functions")
        
        return functions
    
    def extract_json_data(self, functions: List[QNXFunction]) -> Dict[str, Dict[str, Any]]:
        """Extract JSON data (multithreaded version configurable)"""
        if self.enable_multithreading and len(functions) > 1:
            logger.info(f"Extracting JSON data for {len(functions)} functions using {self.max_worker_threads} threads")
            return self._extract_json_data_multithreaded(functions)
        else:
            logger.info(f"Extracting JSON data for {len(functions)} functions using single thread")
            return self._extract_json_data_sequential(functions)
    
    def _extract_json_data_sequential(self, functions: List[QNXFunction]) -> Dict[str, Dict[str, Any]]:
        """Single-threaded JSON extraction"""
        json_data = {}
        
        for i, func in enumerate(functions):
            logger.info(f"Processing JSON {i+1}/{len(functions)}: {func.name}")
            
            try:
                function_info = self.json_extractor.extract_function_info(
                    func.html_content, 
                    func.name
                )
                
                if function_info:
                    serializable_info = serialize_function_info(function_info)
                    json_data[func.name] = serializable_info
                    self.stats.json_extracted += 1
                    logger.debug(f"✓ Extracted JSON for {func.name}")
                    
                    # Enqueue for async GDB enhancement
                    self.enqueue_gdb_task(func.name, serializable_info)
                else:
                    logger.warning(f"✗ Failed to extract JSON for {func.name}")
                    self.stats.errors.append(f"JSON extraction failed: {func.name}")
                    
            except Exception as e:
                error_msg = f"Error extracting JSON for {func.name}: {str(e)}"
                logger.error(error_msg)
                self.stats.errors.append(error_msg)
        
        logger.info(f"Successfully extracted JSON for {len(json_data)} functions")
        return json_data
    
    def _extract_json_data_multithreaded(self, functions: List[QNXFunction]) -> Dict[str, Dict[str, Any]]:
        """Multithreaded JSON extraction"""
        json_data = {}
        max_workers = self.max_worker_threads
        api_delay_range = self.api_delay_range  # Copy to local variable
        config_path = self.config_path
        
        def extract_single_function(func_data):
            """Single function JSON extraction task"""
            func, index = func_data
            try:
                logger.info(f"Processing JSON {index+1}/{len(functions)}: {func.name}")
                
                # Add random delay to avoid concurrent API request issues
                import random
                delay_min, delay_max = api_delay_range
                time.sleep(random.uniform(delay_min, delay_max))
                
                # Create a separate JSON extractor instance for each thread with GDB enhancement enabled
                thread_extractor = ClaudeJSONExtractor(config_path, enable_gdb_in_extraction=True)
                
                function_info = thread_extractor.extract_function_info(
                    func.html_content, 
                    func.name
                )
                
                # Close thread-specific extractor
                thread_extractor.close()
                
                if function_info:
                    # Convert to serializable dict
                    serializable_info = serialize_function_info(function_info)
                    logger.debug(f"✓ Extracted JSON for {func.name}")
                    return func.name, serializable_info, None
                else:
                    error_msg = f"JSON extraction failed: {func.name}"
                    logger.warning(f"✗ Failed to extract JSON for {func.name}")
                    return func.name, None, error_msg
                    
            except Exception as e:
                error_msg = f"JSON extraction error: {func.name}: {str(e)}"
                logger.error(f"Error extracting JSON for {func.name}: {e}")
                return func.name, None, error_msg
        
        # Use ThreadPoolExecutor for parallel processing
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Prepare task data (function and index)
            tasks = [(func, i) for i, func in enumerate(functions)]
            
            # Submit all tasks
            futures = [executor.submit(extract_single_function, task) for task in tasks]
            
            # Collect results
            for future in as_completed(futures):
                try:
                    func_name, result, error = future.result()
                    
                    if result:
                        json_data[func_name] = result
                        self.stats.json_extracted += 1
                        
                        # Enqueue for async GDB enhancement
                        self.enqueue_gdb_task(func_name, result)
                    else:
                        self.stats.errors.append(error)
                        
                except Exception as e:
                    logger.error(f"Thread execution error: {e}")
                    self.stats.errors.append(f"Thread execution error: {str(e)}")
        
        logger.info(f"Successfully extracted JSON for {len(json_data)} functions")
        return json_data
    
    def create_embedding_batches(self, function_names: List[str]) -> List[List[str]]:
        """Create embedding batches"""
        batches = []
        for i in range(0, len(function_names), self.embedding_batch_size):
            batch = function_names[i:i + self.embedding_batch_size]
            batches.append(batch)
        
        logger.info(f"Created {len(batches)} embedding batches")
        return batches
    
    def vectorize_function_names(self, function_names: List[str]) -> Dict[str, List[float]]:
        """Vectorize function names"""
        logger.info(f"Vectorizing {len(function_names)} function names")
        
        # Create vectorization tasks
        tasks = []
        for func_name in function_names:
            task = VectorizeTask(
                text=func_name,  # Vectorize function name
                doc_id=func_name,
                metadata={"function_name": func_name, "type": "function_name"}
            )
            tasks.append(task)
        
        # Execute batch vectorization
        results = self.vectorizer.get_batch_embeddings(tasks)
        
        # Process results
        embeddings = {}
        api_usage = {}
        
        for result in results:
            if result.success:
                embeddings[result.doc_id] = result.embedding
                # Count API usage
                provider = result.provider
                api_usage[provider] = api_usage.get(provider, 0) + 1
                self.stats.vectorized += 1
            else:
                logger.warning(f"✗ Failed to embed {result.doc_id}: {result.error}")
                self.stats.errors.append(f"Embedding failed: {result.doc_id}")
        
        # Update statistics
        self.stats.api_usage.update(api_usage)
        
        logger.info(f"Successfully vectorized {len(embeddings)} function names")
        logger.info(f"API usage: {api_usage}")
        
        return embeddings
    
    def store_vector_database(self, json_data: Dict[str, Dict[str, Any]], embeddings: Dict[str, List[float]]) -> bool:
        """Store to vector database"""
        logger.info("Storing data to vector database")
        
        try:
            # Prepare storage data
            results = []
            documents = []
            metadatas = []
            
            for func_name in json_data.keys():
                if func_name in embeddings:
                    # Create VectorizeResult object
                    result = VectorizeResult(
                        doc_id=func_name,
                        embedding=embeddings[func_name],
                        success=True,
                        provider="hybrid"
                    )
                    results.append(result)
                    
                    # Document content stores JSON string
                    documents.append(json.dumps(json_data[func_name], ensure_ascii=False))
                    
                    # Metadata
                    metadatas.append({
                        "function_name": func_name,
                        "type": "qnx_function",
                        "category": func_name[0].lower()
                    })
            
            if results:
                # Use hybrid vectorizer for storage
                success = self.vectorizer.store_vectors(results, documents, metadatas)
                
                if success:
                    self.stats.stored = len(results)
                    logger.info(f"Successfully stored {len(results)} functions to vector database")
                    return True
                else:
                    logger.error("Failed to store to vector database")
                    return False
            else:
                logger.warning("No valid data to store")
                return False
                
        except Exception as e:
            error_msg = f"Error storing to vector database: {str(e)}"
            logger.error(error_msg)
            self.stats.errors.append(error_msg)
            return False
    
    def save_results(self, json_data: Dict[str, Dict[str, Any]], embeddings: Dict[str, List[float]], output_file: str):
        """Save processing results to file"""
        try:
            # Combine final results
            final_result = {}
            
            for func_name, func_data in json_data.items():
                final_result[func_name] = {
                    "function_data": func_data,
                    "embedding": embeddings.get(func_name, []),
                    "has_embedding": func_name in embeddings
                }
            
            # Save to file
            output_path = self.output_dir / output_file
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(final_result, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Results saved to {output_path}")
            
            # Also save statistics
            stats_file = output_path.with_suffix('.stats.json')
            with open(stats_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "processing_stats": asdict(self.stats),
                    "summary": {
                        "success_rate": self.stats.stored / max(1, self.stats.total_functions) * 100,
                        "avg_time_per_function": self.stats.processing_time / max(1, self.stats.total_functions),
                        "errors_count": len(self.stats.errors)
                    }
                }, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Stats saved to {stats_file}")
            
        except Exception as e:
            logger.error(f"Failed to save results: {e}")
    
    def load_existing_data(self) -> Dict[str, Dict[str, Any]]:
        """Load existing processed data for incremental processing"""
        existing_file = self.output_dir / "qnx_functions_processed.json"
        if existing_file.exists():
            try:
                with open(existing_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                logger.info(f"Loaded {len(data)} existing processed functions")
                return data
            except Exception as e:
                logger.warning(f"Failed to load existing data: {e}")
        return {}

    def process_functions(self, function_names: List[str], output_file: str = "qnx_functions_final.json") -> Dict[str, Any]:
        """Complete processing pipeline with incremental support"""
        start_time = time.time()
        
        # Load existing data for incremental processing
        existing_data = self.load_existing_data()
        
        # Filter out already processed functions
        new_functions = [name for name in function_names if name not in existing_data]
        skipped_count = len(function_names) - len(new_functions)
        
        logger.info("=" * 60)
        logger.info("Starting QNX Batch Processing Final (Incremental Mode)")
        logger.info(f"Total functions: {len(function_names)}")
        logger.info(f"Already processed: {skipped_count}")
        logger.info(f"New functions to process: {len(new_functions)}")
        logger.info("=" * 60)
        
        if not new_functions:
            logger.info("All functions already processed! Using existing data.")
            return {
                "success": True,
                "data": existing_data,
                "stats": {
                    "total_functions": len(function_names),
                    "skipped": skipped_count,
                    "processed": 0,
                    "stored": len(existing_data)
                }
            }
        
        self.stats.total_functions = len(new_functions)
        
        # Start async GDB processing
        self.start_gdb_processing()
        
        try:
            # Step 1: Crawl function documentation (only for new functions)
            logger.info("Step 1: Crawling function documentation")
            functions = self.crawl_functions(new_functions)
            
            if not functions:
                logger.error("No functions crawled successfully")
                return {"error": "No functions crawled"}
            
            # Step 2: Extract JSON data
            logger.info("Step 2: Extracting JSON data with OpenAI")
            json_data = self.extract_json_data(functions)
            
            if not json_data:
                logger.error("No JSON data extracted")
                return {"error": "No JSON data extracted"}
            
            # Step 3: Vectorize function names (hybrid API)
            logger.info("Step 3: Vectorizing function names with Hybrid API")
            embeddings = self.vectorize_function_names(list(json_data.keys()))
            
            # Step 4: Store to vector database
            logger.info("Step 4: Storing to vector database")
            store_success = self.store_vector_database(json_data, embeddings)
            
            # Step 5: Wait for GDB processing to complete and merge results
            logger.info("Step 5: Waiting for GDB processing and merging results")
            
            # Allow some time for GDB processing
            logger.info("Allowing time for GDB processing to complete...")
            wait_time = min(30, len(json_data) * 2)  # Maximum 30 seconds or 2 seconds per function
            time.sleep(wait_time)
            
            # Get GDB enhanced results
            gdb_results = self.get_gdb_results()
            if gdb_results:
                logger.info(f"Merging {len(gdb_results)} GDB enhanced results")
                for func_name, enhanced_data in gdb_results.items():
                    if func_name in json_data:
                        json_data[func_name] = enhanced_data
                        logger.debug(f"Merged GDB enhancement for: {func_name}")
            
            # Stop GDB processing
            self.stop_gdb_processing()
            
            # Step 6: Save results file
            logger.info("Step 6: Saving results")
            self.save_results(json_data, embeddings, output_file)
            
            # Calculate final statistics
            self.stats.processing_time = time.time() - start_time
            self.stats.failed = self.stats.total_functions - max(self.stats.stored, len(json_data))
            
            # Output summary
            logger.info("=" * 60)
            logger.info("Processing Complete!")
            logger.info(f"Total functions: {self.stats.total_functions}")
            logger.info(f"Crawled: {self.stats.crawled}")
            logger.info(f"JSON extracted: {self.stats.json_extracted}")
            logger.info(f"Vectorized: {self.stats.vectorized}")
            logger.info(f"Stored: {self.stats.stored}")
            logger.info(f"Failed: {self.stats.failed}")
            logger.info(f"Processing time: {self.stats.processing_time:.2f}s")
            logger.info(f"Success rate: {(self.stats.stored/self.stats.total_functions*100):.1f}%")
            logger.info(f"API usage: {self.stats.api_usage}")
            logger.info("=" * 60)
            
            return {
                "success": True,
                "stats": asdict(self.stats),
                "json_data": json_data,
                "embeddings": embeddings,
                "output_file": output_file
            }
            
        except Exception as e:
            error_msg = f"Processing failed: {str(e)}"
            logger.error(error_msg)
            self.stats.errors.append(error_msg)
            return {"error": error_msg}
        finally:
            # Ensure GDB processing is stopped
            self.stop_gdb_processing()
    
    def query_functions(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """Query functions"""
        logger.info(f"Querying: '{query}'")
        
        try:
            results = self.vectorizer.query_similar(query, n_results)
            
            formatted_results = []
            for result in results:
                # Parse stored JSON data
                try:
                    function_data = json.loads(result.get('document', '{}'))
                    formatted_results.append({
                        "function_name": result.get('metadata', {}).get('function_name', 'unknown'),
                        "similarity": result.get('similarity', 0),
                        "function_data": function_data
                    })
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse JSON for result: {result}")
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Query failed: {e}")
            return []


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="QNX Batch Processor")
    parser.add_argument("--functions", nargs="+", help="Specific function names to process")
    parser.add_argument("--max-functions", type=int, help="Maximum number of functions to process")
    parser.add_argument("--all", action="store_true", help="Process all discovered QNX functions from A-Z")
    parser.add_argument("--letters", nargs="+", help="Process functions from specific letters (e.g., --letters a b c)")
    parser.add_argument("--output", default="qnx_functions_processed.json", help="Output file")
    parser.add_argument("--test-query", help="Test query after processing")
    parser.add_argument("--continue-on-error", action="store_true", help="Continue processing even if some functions fail")
    
    args = parser.parse_args()
    
    try:
        # Initialize processor
        processor = QNXBatchProcessor()
        
        # Determine function list to process
        if args.functions:
            # User-specified functions
            function_names = args.functions
            logger.info(f"Processing {len(function_names)} user-specified functions")
            
        elif args.all:
            # Process all discovered functions
            logger.info("Starting to discover all QNX functions...")
            all_functions = processor.crawler.discover_functions_from_index()
            
            if args.max_functions:
                function_names = all_functions[:args.max_functions]
                logger.info(f"Processing first {len(function_names)} functions (limit: {args.max_functions})")
            else:
                function_names = all_functions
                logger.info(f"Processing all {len(function_names)} discovered functions")
                
        elif args.letters:
            # Process functions from specified letters
            function_names = []
            for letter in args.letters:
                letter = letter.lower()
                if letter in 'abcdefghijklmnopqrstuvwxyz':
                    letter_functions = processor.crawler._get_backup_functions_for_letter(letter)
                    function_names.extend(letter_functions)
                    logger.info(f"Letter '{letter}': added {len(letter_functions)} functions")
                else:
                    logger.warning(f"Ignored invalid letter: {letter}")
            
            function_names = sorted(list(set(function_names)))  # Deduplicate and sort
            
            if args.max_functions:
                function_names = function_names[:args.max_functions]
            
            logger.info(f"Processing {len(function_names)} functions under letters {args.letters}")
            
        else:
            # Default: process a few test functions
            default_functions = ["abort", "abs", "malloc", "free", "printf"]
            max_funcs = args.max_functions or 5
            function_names = default_functions[:max_funcs]
            logger.info(f"Processing {len(function_names)} default test functions")
        
        if not function_names:
            logger.error("No functions found to process")
            sys.exit(1)
        
        # Execute processing
        result = processor.process_functions(function_names, args.output)
        
        if result.get("success"):
            print(f"\n✓ Processing completed successfully!")
            print(f"Output: {args.output}")
            print(f"Functions processed: {result['stats']['stored']}/{result['stats']['total_functions']}")
            print(f"API usage: {result['stats']['api_usage']}")
            
            # Test query
            if args.test_query:
                print(f"\nTesting query: '{args.test_query}'")
                query_results = processor.query_functions(args.test_query, 3)
                for i, res in enumerate(query_results):
                    print(f"  {i+1}. {res['function_name']} (similarity: {res['similarity']:.3f})")
        else:
            print(f"\\n✗ Processing failed: {result.get('error')}")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Main execution failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()