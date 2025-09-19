#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QNX Step-by-Step Processor
Supports processing from existing discovery and crawl data with configurable steps
"""

import os
import sys
import json
import logging
import time
import argparse
from typing import Dict, List, Optional, Any, Set
from pathlib import Path
from dataclasses import dataclass, asdict

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from qnx_web_crawler import QNXWebCrawler, QNXFunction
from openai_json_extractor import OpenAIJSONExtractor
from claude_json_extractor import ClaudeJSONExtractor
from hybrid_vectorizer import HybridVectorizer, VectorizeTask, VectorizeResult
from qnx_gdb_type_enhancer import QNXGDBTypeEnhancer

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class ProcessingStep:
    """Processing step configuration"""
    name: str
    enabled: bool = True
    description: str = ""

class QNXStepProcessor:
    """QNX Step-by-Step Processor with configurable pipeline"""
    
    def __init__(self, config_path: str = "config.json"):
        """Initialize processor"""
        self.config_path = config_path
        self.config = self._load_config(config_path)
        
        # Data directories
        self.cache_dir = Path("./data/qnx_web_cache")
        self.output_dir = Path("./data/processed_functions")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Processing steps
        self.steps = {
            "discover": ProcessingStep("discover", True, "Discover QNX functions from documentation"),
            "crawl": ProcessingStep("crawl", True, "Crawl function documentation"),
            "extract": ProcessingStep("extract", True, "Extract JSON data with OpenAI"),
            "vectorize": ProcessingStep("vectorize", True, "Vectorize function names"),
            "store": ProcessingStep("store", True, "Store to vector database"),
            "gdb": ProcessingStep("gdb", True, "GDB type enhancement (async)")
        }
        
        # Initialize components (lazy loading)
        self.crawler = None
        self.json_extractor = None
        self.vectorizer = None
        self.gdb_enhancer = None
        
        logger.info("QNX Step Processor initialized")
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration file"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load config file: {e}")
            return {}
    
    def _init_crawler(self):
        """Initialize crawler (lazy loading)"""
        if self.crawler is None:
            self.crawler = QNXWebCrawler(self.config_path)
        return self.crawler
    
    def _init_json_extractor(self):
        """Initialize JSON extractor (lazy loading)"""
        if self.json_extractor is None:
            # Check AI provider configuration
            ai_config = self.config.get("ai_settings", {})
            provider = ai_config.get("provider", "openai")
            
            # Enable GDB enhancement only if GDB step is enabled
            enable_gdb = self.steps["gdb"].enabled
            
            if provider == "claude":
                # Use Claude extractor (faster and more efficient)
                self.json_extractor = ClaudeJSONExtractor(self.config_path, enable_gdb_in_extraction=enable_gdb)
            else:
                # Use OpenAI extractor as fallback
                self.json_extractor = OpenAIJSONExtractor(self.config_path, enable_gdb_in_extraction=enable_gdb)
        return self.json_extractor
    
    def _init_vectorizer(self):
        """Initialize vectorizer (lazy loading)"""
        if self.vectorizer is None:
            self.vectorizer = HybridVectorizer(self.config_path)
        return self.vectorizer
    
    def _init_gdb_enhancer(self):
        """Initialize GDB enhancer (lazy loading)"""
        if self.gdb_enhancer is None:
            self.gdb_enhancer = QNXGDBTypeEnhancer(self.config_path)
        return self.gdb_enhancer
    
    def configure_steps(self, **step_configs):
        """Configure which steps to run"""
        for step_name, enabled in step_configs.items():
            if step_name in self.steps:
                self.steps[step_name].enabled = enabled
                logger.info(f"Step '{step_name}': {'enabled' if enabled else 'disabled'}")
    
    def check_existing_data(self) -> Dict[str, Any]:
        """Check what data already exists"""
        status = {
            "discovered_functions": None,
            "crawled_functions": None,
            "extracted_functions": None,
            "cache_exists": False,
            "processed_count": 0
        }
        
        # Check cache directory
        if self.cache_dir.exists():
            cache_files = list(self.cache_dir.glob("*.html"))
            status["cache_exists"] = len(cache_files) > 0
            logger.info(f"Found {len(cache_files)} cached HTML files")
        
        # Check if we have discovered functions list
        discovered_file = self.output_dir / "discovered_functions.json"
        if discovered_file.exists():
            try:
                with open(discovered_file, 'r', encoding='utf-8') as f:
                    status["discovered_functions"] = json.load(f)
                logger.info(f"Found {len(status['discovered_functions'])} discovered functions")
            except Exception as e:
                logger.warning(f"Failed to load discovered functions: {e}")
        
        # If no discovered functions found, check cache directory for all cached functions
        if status["discovered_functions"] is None and status["cache_exists"]:
            try:
                # Extract function names from cached HTML files
                cache_files = list(self.cache_dir.glob("*.html"))
                discovered_functions = []
                
                for cache_file in cache_files:
                    func_name = cache_file.stem  # Get filename without extension
                    discovered_functions.append(func_name)
                
                if discovered_functions:
                    status["discovered_functions"] = discovered_functions
                    logger.info(f"Found {len(discovered_functions)} functions from cache directory")
            except Exception as e:
                logger.warning(f"Failed to extract functions from cache directory: {e}")
        
        # Fallback: check qnx_structure_analysis.json
        if status["discovered_functions"] is None:
            analysis_file = Path(self.config_path).parent / "data" / "qnx_structure_analysis.json"
            if analysis_file.exists():
                try:
                    with open(analysis_file, 'r', encoding='utf-8') as f:
                        analysis_data = json.load(f)
                    
                    # Extract function names from url_patterns
                    discovered_functions = []
                    url_patterns = analysis_data.get("url_patterns", {})
                    for letter_group in url_patterns.values():
                        for func_info in letter_group:
                            if "function_name" in func_info:
                                discovered_functions.append(func_info["function_name"])
                    
                    if discovered_functions:
                        status["discovered_functions"] = discovered_functions
                        logger.info(f"Found {len(discovered_functions)} functions from qnx_structure_analysis.json (fallback)")
                except Exception as e:
                    logger.warning(f"Failed to load qnx_structure_analysis.json: {e}")
        
        # Check if we have crawled functions
        crawled_file = self.output_dir / "crawled_functions.json"
        if crawled_file.exists():
            try:
                with open(crawled_file, 'r', encoding='utf-8') as f:
                    status["crawled_functions"] = json.load(f)
                logger.info(f"Found {len(status['crawled_functions'])} crawled functions")
            except Exception as e:
                logger.warning(f"Failed to load crawled functions: {e}")
        
        # Check existing processed data
        processed_file = self.output_dir / "qnx_functions_processed.json"
        if processed_file.exists():
            try:
                with open(processed_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                status["extracted_functions"] = data
                status["processed_count"] = len(data)
                logger.info(f"Found {len(data)} already processed functions")
            except Exception as e:
                logger.warning(f"Failed to load processed functions: {e}")
        
        return status
    
    def step_discover(self, max_functions: Optional[int] = None) -> List[str]:
        """Step 1: Discover QNX functions"""
        logger.info("=== Step 1: Discovering QNX functions ===")
        
        discovered_file = self.output_dir / "discovered_functions.json"
        
        # Check if already exists
        if discovered_file.exists():
            try:
                with open(discovered_file, 'r', encoding='utf-8') as f:
                    functions = json.load(f)
                logger.info(f"Loaded {len(functions)} existing discovered functions")
                if max_functions:
                    functions = functions[:max_functions]
                return functions
            except Exception as e:
                logger.warning(f"Failed to load existing discovered functions: {e}")
        
        # Discover new functions
        crawler = self._init_crawler()
        functions = crawler.discover_functions_from_index()
        
        if max_functions:
            functions = functions[:max_functions]
            logger.info(f"Limited to {max_functions} functions")
        
        # Save discovered functions
        with open(discovered_file, 'w', encoding='utf-8') as f:
            json.dump(functions, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Discovered and saved {len(functions)} functions")
        return functions
    
    def step_crawl(self, function_names: List[str]) -> List[QNXFunction]:
        """Step 2: Crawl function documentation"""
        logger.info("=== Step 2: Crawling function documentation ===")
        
        crawled_file = self.output_dir / "crawled_functions.json"
        
        # Check if already exists
        if crawled_file.exists():
            try:
                with open(crawled_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Convert back to QNXFunction objects
                functions = []
                for item in data:
                    func = QNXFunction(
                        name=item["name"],
                        url=item["url"],
                        html_content=item.get("html_content", "")
                    )
                    functions.append(func)
                
                logger.info(f"Loaded {len(functions)} existing crawled functions")
                return functions
            except Exception as e:
                logger.warning(f"Failed to load existing crawled functions: {e}")
        
        # Crawl new functions
        crawler = self._init_crawler()
        functions = crawler.crawl_functions(function_names)
        
        # Save crawled functions
        crawled_data = []
        for func in functions:
            crawled_data.append({
                "name": func.name,
                "url": func.url,
                "html_content": func.html_content
            })
        
        with open(crawled_file, 'w', encoding='utf-8') as f:
            json.dump(crawled_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Crawled and saved {len(functions)} functions")
        return functions
    
    def step_extract(self, functions: List[QNXFunction]) -> Dict[str, Dict[str, Any]]:
        """Step 3: Extract JSON data one by one (no batch processing)"""
        logger.info("=== Step 3: Extracting JSON data ===")
        
        extracted_file = self.output_dir / "extracted_functions.json"
        
        # Check existing data
        existing_data = {}
        if extracted_file.exists():
            try:
                with open(extracted_file, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
                logger.info(f"Loaded {len(existing_data)} existing extracted functions")
            except Exception as e:
                logger.warning(f"Failed to load existing extracted data: {e}")
        
        # Filter functions that need processing
        functions_to_process = [f for f in functions if f.name not in existing_data]
        logger.info(f"Need to process {len(functions_to_process)} new functions")
        
        if not functions_to_process:
            logger.info("All functions already extracted")
            return existing_data
        
        # Initialize extractor
        extractor = self._init_json_extractor()
        
        # Process one by one to avoid connection issues
        extracted_data = existing_data.copy()
        
        for i, func in enumerate(functions_to_process, 1):
            try:
                logger.info(f"Extracting {i}/{len(functions_to_process)}: {func.name}")
                function_info = extractor.extract_function_info(func.html_content, func.name)
                
                if function_info:
                    # Convert to serializable format
                    from qnx_batch_processor import serialize_function_info
                    extracted_data[func.name] = serialize_function_info(function_info)
                    logger.info(f"✓ Extracted: {func.name}")
                else:
                    logger.warning(f"✗ Failed to extract: {func.name}")
                
                # Save progress after each function
                with open(extracted_file, 'w', encoding='utf-8') as f:
                    json.dump(extracted_data, f, indent=2, ensure_ascii=False)
                logger.info(f"Saved progress: {len(extracted_data)} functions extracted")
                
                # Add delay between functions to avoid API rate limits
                if i < len(functions_to_process):  # Don't delay after last function
                    import random
                    delay = random.uniform(1.0, 3.0)  # Reduced delay: 1-3 seconds (Claude is fast!)
                    logger.info(f"Waiting {delay:.1f}s before next function...")
                    time.sleep(delay)
                        
            except Exception as e:
                logger.error(f"Error extracting {func.name}: {e}")
                # Continue with next function even if one fails
                continue
        
        logger.info(f"Extraction complete: {len(extracted_data)} total functions")
        return extracted_data
    
    def step_vectorize(self, function_names: List[str]) -> Dict[str, List[float]]:
        """Step 4: Vectorize function names"""
        logger.info("=== Step 4: Vectorizing function names ===")
        
        vectorizer = self._init_vectorizer()
        
        # Create vectorization tasks
        tasks = []
        for func_name in function_names:
            task = VectorizeTask(
                text=func_name,
                doc_id=func_name,
                metadata={"function_name": func_name, "type": "function_name"}
            )
            tasks.append(task)
        
        # Execute batch vectorization
        results = vectorizer.get_batch_embeddings(tasks)
        
        # Process results
        embeddings = {}
        for result in results:
            if result.success:
                embeddings[result.doc_id] = result.embedding
        
        logger.info(f"Vectorized {len(embeddings)} function names")
        return embeddings
    
    def step_store(self, json_data: Dict[str, Dict[str, Any]], embeddings: Dict[str, List[float]]) -> bool:
        """Step 5: Store to vector database"""
        logger.info("=== Step 5: Storing to vector database ===")
        
        vectorizer = self._init_vectorizer()
        
        # Prepare storage data
        results = []
        documents = []
        metadatas = []
        
        for func_name in json_data.keys():
            if func_name in embeddings:
                result = VectorizeResult(
                    doc_id=func_name,
                    embedding=embeddings[func_name],
                    success=True,
                    provider="hybrid"
                )
                results.append(result)
                
                documents.append(json.dumps(json_data[func_name], ensure_ascii=False))
                
                metadatas.append({
                    "function_name": func_name,
                    "type": "qnx_function",
                    "category": func_name[0].lower()
                })
        
        if results:
            success = vectorizer.store_vectors(results, documents, metadatas)
            if success:
                logger.info(f"Successfully stored {len(results)} functions to vector database")
                return True
            else:
                logger.error("Failed to store to vector database")
                return False
        else:
            logger.warning("No valid data to store")
            return False
    
    def step_gdb_enhance(self, json_data: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Step 6: GDB type enhancement"""
        logger.info("=== Step 6: GDB type enhancement ===")
        
        enhancer = self._init_gdb_enhancer()
        enhanced_data = {}
        
        for func_name, func_data in json_data.items():
            try:
                logger.info(f"Enhancing: {func_name}")
                
                if 'parameters' in func_data:
                    enhanced_params = enhancer.enhance_function_parameters(func_data['parameters'])
                    func_data['parameters'] = enhanced_params
                
                enhanced_data[func_name] = func_data
                logger.info(f"✓ Enhanced: {func_name}")
                
            except Exception as e:
                logger.error(f"GDB enhancement failed for {func_name}: {e}")
                enhanced_data[func_name] = func_data  # Keep original data
        
        logger.info(f"GDB enhancement complete: {len(enhanced_data)} functions")
        return enhanced_data
    
    def process(self, function_names: Optional[List[str]] = None, max_functions: Optional[int] = None) -> Dict[str, Any]:
        """Execute the configured processing pipeline"""
        logger.info("=" * 60)
        logger.info("Starting QNX Step-by-Step Processing")
        logger.info("=" * 60)
        
        # Show enabled steps
        enabled_steps = [name for name, step in self.steps.items() if step.enabled]
        logger.info(f"Enabled steps: {', '.join(enabled_steps)}")
        
        # Check existing data
        existing_data = self.check_existing_data()
        
        start_time = time.time()
        result = {"success": True, "steps_completed": [], "errors": []}
        
        try:
            # Step 1: Discover
            if self.steps["discover"].enabled:
                if function_names:
                    discovered_functions = function_names
                    logger.info(f"Using provided function list: {len(discovered_functions)} functions")
                else:
                    discovered_functions = self.step_discover(max_functions)
                result["steps_completed"].append("discover")
            else:
                if existing_data["discovered_functions"]:
                    discovered_functions = existing_data["discovered_functions"]
                    if max_functions:
                        discovered_functions = discovered_functions[:max_functions]
                    logger.info(f"Using existing discovered functions: {len(discovered_functions)}")
                else:
                    raise ValueError("Discovery step disabled but no existing discovered functions found")
            
            # Step 2: Crawl
            if self.steps["crawl"].enabled:
                crawled_functions = self.step_crawl(discovered_functions)
                result["steps_completed"].append("crawl")
            else:
                if existing_data["crawled_functions"]:
                    # Filter by discovered_functions
                    discovered_set = set(discovered_functions)
                    crawled_functions = [f for f in existing_data["crawled_functions"] 
                                       if f["name"] in discovered_set]
                    logger.info(f"Using existing crawled functions: {len(crawled_functions)}")
                elif existing_data["cache_exists"]:
                    # Build crawled functions from cache files
                    logger.info("Building crawled functions from cache files...")
                    crawled_functions = []
                    discovered_set = set(discovered_functions)
                    
                    for func_name in discovered_functions:
                        cache_file = self.cache_dir / f"{func_name}.html"
                        if cache_file.exists():
                            try:
                                with open(cache_file, 'r', encoding='utf-8') as f:
                                    html_content = f.read()
                                
                                # Create QNXFunction object
                                func = QNXFunction(
                                    name=func_name,
                                    url=f"https://www.qnx.com/developers/docs/7.1/com.qnx.doc.neutrino.lib_ref/topic/x/{func_name}.html",
                                    html_content=html_content
                                )
                                crawled_functions.append(func)
                            except Exception as e:
                                logger.warning(f"Failed to load cached HTML for {func_name}: {e}")
                    
                    logger.info(f"Built {len(crawled_functions)} crawled functions from cache")
                else:
                    raise ValueError("Crawl step disabled but no existing crawled functions or cache found")
            
            # Step 3: Extract
            if self.steps["extract"].enabled:
                if isinstance(crawled_functions[0], dict):
                    # Convert from dict to QNXFunction
                    func_objects = []
                    for item in crawled_functions:
                        func = QNXFunction(
                            name=item["name"],
                            url=item["url"],
                            html_content=item.get("html_content", "")
                        )
                        func_objects.append(func)
                    crawled_functions = func_objects
                
                extracted_data = self.step_extract(crawled_functions)
                result["steps_completed"].append("extract")
            else:
                if existing_data["extracted_functions"]:
                    extracted_data = existing_data["extracted_functions"]
                    # Filter by discovered functions
                    discovered_set = set(discovered_functions)
                    extracted_data = {k: v for k, v in extracted_data.items() if k in discovered_set}
                    logger.info(f"Using existing extracted functions: {len(extracted_data)}")
                else:
                    raise ValueError("Extract step disabled but no existing extracted functions found")
            
            # Step 4: Vectorize
            if self.steps["vectorize"].enabled:
                embeddings = self.step_vectorize(list(extracted_data.keys()))
                result["steps_completed"].append("vectorize")
            else:
                embeddings = {}
                logger.info("Vectorize step disabled, using empty embeddings")
            
            # Step 5: Store
            if self.steps["store"].enabled and embeddings:
                store_success = self.step_store(extracted_data, embeddings)
                if store_success:
                    result["steps_completed"].append("store")
                else:
                    result["errors"].append("Failed to store to vector database")
            
            # Step 6: GDB Enhancement
            if self.steps["gdb"].enabled:
                enhanced_data = self.step_gdb_enhance(extracted_data)
                result["steps_completed"].append("gdb")
            else:
                enhanced_data = extracted_data
                logger.info("GDB step disabled, using original data")
            
            # Save final results
            final_output = self.output_dir / "qnx_functions_processed.json"
            with open(final_output, 'w', encoding='utf-8') as f:
                json.dump(enhanced_data, f, indent=2, ensure_ascii=False)
            
            # Processing summary
            processing_time = time.time() - start_time
            result.update({
                "total_functions": len(discovered_functions),
                "extracted_functions": len(extracted_data),
                "vectorized_functions": len(embeddings),
                "processing_time": processing_time,
                "output_file": str(final_output)
            })
            
            logger.info("=" * 60)
            logger.info("Processing Complete!")
            logger.info(f"Total functions: {result['total_functions']}")
            logger.info(f"Extracted: {result['extracted_functions']}")
            logger.info(f"Vectorized: {result['vectorized_functions']}")
            logger.info(f"Steps completed: {', '.join(result['steps_completed'])}")
            logger.info(f"Processing time: {processing_time:.2f}s")
            logger.info("=" * 60)
            
        except Exception as e:
            result["success"] = False
            result["error"] = str(e)
            logger.error(f"Processing failed: {e}")
        
        return result

def main():
    """Main function with command line interface"""
    parser = argparse.ArgumentParser(description="QNX Step-by-Step Processor")
    
    # Step configuration
    parser.add_argument("--skip-discover", action="store_true", help="Skip discovery step")
    parser.add_argument("--skip-crawl", action="store_true", help="Skip crawl step")
    parser.add_argument("--skip-extract", action="store_true", help="Skip extraction step")
    parser.add_argument("--skip-vectorize", action="store_true", help="Skip vectorization step")
    parser.add_argument("--skip-store", action="store_true", help="Skip storage step")
    parser.add_argument("--skip-gdb", action="store_true", help="Skip GDB enhancement step")
    
    # Function selection
    parser.add_argument("--functions", nargs="+", help="Specific function names to process")
    parser.add_argument("--max-functions", type=int, help="Maximum number of functions to process")
    
    # Other options
    parser.add_argument("--check-data", action="store_true", help="Check existing data and exit")
    parser.add_argument("--config", default="config.json", help="Configuration file path")
    
    args = parser.parse_args()
    
    # Initialize processor
    processor = QNXStepProcessor(args.config)
    
    # Configure steps
    processor.configure_steps(
        discover=not args.skip_discover,
        crawl=not args.skip_crawl,
        extract=not args.skip_extract,
        vectorize=not args.skip_vectorize,
        store=not args.skip_store,
        gdb=not args.skip_gdb
    )
    
    # Check existing data if requested
    if args.check_data:
        status = processor.check_existing_data()
        print("\n=== Existing Data Status ===")
        for key, value in status.items():
            if isinstance(value, list):
                print(f"{key}: {len(value)} items" if value else f"{key}: None")
            elif isinstance(value, dict):
                print(f"{key}: {len(value)} items" if value else f"{key}: None")
            else:
                print(f"{key}: {value}")
        return
    
    # Execute processing
    result = processor.process(args.functions, args.max_functions)
    
    if result["success"]:
        print(f"\n✓ Processing completed successfully!")
        print(f"Steps completed: {', '.join(result['steps_completed'])}")
        print(f"Functions processed: {result['extracted_functions']}")
        print(f"Output: {result['output_file']}")
    else:
        print(f"\n✗ Processing failed: {result['error']}")
        if result["errors"]:
            print("Additional errors:")
            for error in result["errors"]:
                print(f"  - {error}")

if __name__ == "__main__":
    main()