#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenAI Vectorizer - Dedicated to OpenAI Embedding API
"""

import os
import sys
import json
import logging
import time
from typing import Dict, List, Optional, Any
from pathlib import Path
from dataclasses import dataclass

from openai import OpenAI
import chromadb
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class VectorizeTask:
    """Vectorization task"""
    text: str
    doc_id: str
    metadata: Dict[str, Any]

@dataclass  
class VectorizeResult:
    """Vectorization result"""
    doc_id: str
    embedding: List[float]
    success: bool
    provider: str = ""  # API provider used
    error: Optional[str] = None

class HybridVectorizer:
    """OpenAI Vectorizer - Dedicated to OpenAI Embedding API"""
    
    def __init__(self, config_path: str = "config.json"):
        """Initialize OpenAI vectorizer"""
        # Load configuration
        self.config = self._load_config(config_path)
        
        # API configuration
        ai_config = self.config.get("ai_settings", {})
        openai_config = ai_config.get("openai", {})
        
        # OpenAI settings
        self.openai_api_key = os.getenv(openai_config.get("api_key_env", "OPENAI_API_KEY"))
        self.openai_embedding_model = openai_config.get("embedding_model", "text-embedding-3-small")
        
        # Initialize OpenAI client
        self.openai_client = None
        self.openai_available = self._init_openai()
        
        # ChromaDB settings
        self.persist_dir = "./data/chroma_db/"
        self.collection_name = "qnx_functions_hybrid"
        self.chroma_client = chromadb.PersistentClient(path=self.persist_dir)
        self.collection = None
        
        logger.info("OpenAI vectorizer initialization completed")
        logger.info(f"OpenAI available: {self.openai_available}")
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration file"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Configuration file loading failed: {e}")
            return {}
    
    
    def _init_openai(self) -> bool:
        """Initialize OpenAI client"""
        try:
            if not self.openai_api_key:
                logger.warning("OpenAI API key not found")
                return False
            
            # Check proxy configuration
            import httpx
            proxy_config = self.config.get("network_settings", {}).get("proxy", {})
            client_kwargs = {"api_key": self.openai_api_key}
            
            if proxy_config.get("enabled", False):
                https_proxy = proxy_config.get("https_proxy")
                if https_proxy:
                    logger.info(f"Using proxy: {https_proxy}")
                    client_kwargs["http_client"] = httpx.Client(proxy=https_proxy)
            
            self.openai_client = OpenAI(**client_kwargs)
            
            # Test embedding functionality (using new API format)
            test_result = self.openai_client.embeddings.create(
                model=self.openai_embedding_model,
                input="test"
            )
            
            if test_result and test_result.data:
                logger.info("OpenAI embedding API available")
                return True
            else:
                logger.warning("OpenAI embedding API test failed")
                return False
                
        except Exception as e:
            logger.warning(f"OpenAI initialization failed: {e}")
            return False
    
    
    def get_embedding_openai(self, text: str) -> Optional[List[float]]:
        """Get embedding using OpenAI"""
        try:
            if not self.openai_client:
                return None
                
            response = self.openai_client.embeddings.create(
                model=self.openai_embedding_model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.debug(f"OpenAI embedding failed: {e}")
            return None
    
    def get_single_embedding(self, text: str) -> VectorizeResult:
        """Get embedding for single text"""
        doc_id = f"text_{hash(text) % 10000}"
        
        # Get embedding using OpenAI
        if self.openai_available:
            embedding = self.get_embedding_openai(text)
            if embedding:
                return VectorizeResult(
                    doc_id=doc_id,
                    embedding=embedding,
                    success=True,
                    provider="openai"
                )
        
        # Failed
        return VectorizeResult(
            doc_id=doc_id,
            embedding=[],
            success=False,
            error="OpenAI embedding failed"
        )
    
    def get_batch_embeddings(self, tasks: List[VectorizeTask]) -> List[VectorizeResult]:
        """Batch get embeddings with true batch processing"""
        results = []
        
        logger.info(f"Starting optimized batch processing of {len(tasks)} embedding tasks")
        
        # Use OpenAI batch API for better performance
        if self.openai_available:
            batch_size = 20  # OpenAI allows up to 2048 texts per batch
            
            for i in range(0, len(tasks), batch_size):
                batch_tasks = tasks[i:i+batch_size]
                batch_texts = [task.text for task in batch_tasks]
                
                logger.info(f"Processing batch {i//batch_size + 1}/{(len(tasks) + batch_size - 1)//batch_size} ({len(batch_tasks)} items)")
                
                try:
                    # Single API call for the entire batch
                    response = self.openai_client.embeddings.create(
                        model=self.openai_embedding_model,
                        input=batch_texts
                    )
                    
                    # Process batch results
                    for j, task in enumerate(batch_tasks):
                        if j < len(response.data):
                            embedding = response.data[j].embedding
                            result = VectorizeResult(
                                doc_id=task.doc_id,
                                embedding=embedding,
                                success=True,
                                provider="openai"
                            )
                        else:
                            result = VectorizeResult(
                                doc_id=task.doc_id,
                                embedding=[],
                                success=False,
                                error="OpenAI batch result missing"
                            )
                        results.append(result)
                        
                except Exception as e:
                    logger.error(f"Batch embedding failed: {e}")
                    # Fallback to individual processing for this batch
                    for task in batch_tasks:
                        embedding = self.get_embedding_openai(task.text)
                        if embedding:
                            result = VectorizeResult(
                                doc_id=task.doc_id,
                                embedding=embedding,
                                success=True,
                                provider="openai"
                            )
                        else:
                            result = VectorizeResult(
                                doc_id=task.doc_id,
                                embedding=[],
                                success=False,
                                error="OpenAI embedding failed"
                            )
                        results.append(result)
                
                # Rate limiting between batches (much less delay needed)
                time.sleep(0.5)
        else:
            # Fallback to original method if OpenAI not available
            for i, task in enumerate(tasks):
                logger.debug(f"Processing {i+1}/{len(tasks)}: {task.text[:50]}...")
                result = VectorizeResult(
                    doc_id=task.doc_id,
                    embedding=[],
                    success=False,
                    error="OpenAI not available"
                )
                results.append(result)
                time.sleep(0.1)
        
        successful = [r for r in results if r.success]
        logger.info(f"Batch processing completed: {len(successful)}/{len(tasks)} successful")
        
        # Count usage statistics
        provider_stats = {}
        for result in successful:
            provider = result.provider
            provider_stats[provider] = provider_stats.get(provider, 0) + 1
        
        logger.info(f"API usage statistics: {provider_stats}")
        
        return results
    
    def create_or_get_collection(self, reset: bool = False) -> chromadb.Collection:
        """Create or get ChromaDB collection"""
        if reset:
            try:
                self.chroma_client.delete_collection(name=self.collection_name)
                logger.info(f"Deleted existing collection: {self.collection_name}")
            except (ValueError, Exception):
                pass
        
        try:
            self.collection = self.chroma_client.get_collection(name=self.collection_name)
            logger.info(f"Retrieved existing collection: {self.collection_name}")
        except (ValueError, Exception):
            self.collection = self.chroma_client.create_collection(
                name=self.collection_name,
                metadata={"description": "QNX function documentation vector database - Hybrid API version"}
            )
            logger.info(f"Created new collection: {self.collection_name}")
        
        return self.collection
    
    def store_vectors(self, results: List[VectorizeResult], documents: List[str], metadatas: List[Dict[str, Any]]) -> bool:
        """Store vectors to database"""
        try:
            # Filter successful results
            valid_indices = [i for i, r in enumerate(results) if r.success]
            
            if not valid_indices:
                logger.warning("No valid vectors to store")
                return False
            
            doc_ids = [results[i].doc_id for i in valid_indices]
            embeddings = [results[i].embedding for i in valid_indices]
            valid_documents = [documents[i] for i in valid_indices]
            valid_metadatas = [metadatas[i] for i in valid_indices]
            
            # Add provider information to metadata
            for i, idx in enumerate(valid_indices):
                valid_metadatas[i]["embedding_provider"] = results[idx].provider
            
            # Create or get collection
            collection = self.create_or_get_collection()
            
            # Store to ChromaDB
            collection.add(
                ids=doc_ids,
                embeddings=embeddings,
                documents=valid_documents,
                metadatas=valid_metadatas
            )
            
            logger.info(f"Successfully stored {len(doc_ids)} vectors to database")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store vectors: {e}")
            return False
    
    def query_similar(self, query_text: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """Query similar documents"""
        if not self.collection:
            self.create_or_get_collection()
        
        # Get query vector
        query_result = self.get_single_embedding(query_text)
        if not query_result.success:
            logger.error("Unable to get query vector")
            return []
        
        try:
            results = self.collection.query(
                query_embeddings=[query_result.embedding],
                n_results=n_results,
                include=["documents", "metadatas", "distances"]
            )
            
            formatted_results = []
            for i in range(len(results["documents"][0])):
                formatted_results.append({
                    "document": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i],
                    "similarity": 1 - results["distances"][0][i]
                })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Query failed: {e}")
            return []

    def vectorize_functions_from_file(self, json_file_path: str) -> bool:
        """Vectorize QNX functions from JSON file"""
        logger.info(f"Starting vectorization of functions from {json_file_path}")
        
        try:
            # Load JSON data
            with open(json_file_path, 'r', encoding='utf-8') as f:
                functions_data = json.load(f)
            
            logger.info(f"Loaded {len(functions_data)} functions from JSON file")
            
            # Create vectorization tasks
            tasks = []
            for func_name, func_data in functions_data.items():
                # Create text content for vectorization
                text_content = self._create_function_text(func_name, func_data)
                
                # Create metadata
                metadata = {
                    "function_name": func_name,
                    "return_type": func_data.get("return_type", ""),
                    "classification": func_data.get("classification", ""),
                    "libraries": json.dumps(func_data.get("libraries", [])),
                    "headers": json.dumps([h.get("filename", "") for h in func_data.get("headers", [])]),
                    "parameter_count": len(func_data.get("parameters", [])),
                    "has_gdb_enhancement": any(p.get("enhanced", False) for p in func_data.get("parameters", []))
                }
                
                task = VectorizeTask(
                    text=text_content,
                    doc_id=func_name,
                    metadata=metadata
                )
                tasks.append(task)
            
            # Process in batches
            batch_size = 100
            total_batches = (len(tasks) + batch_size - 1) // batch_size
            all_results = []
            
            for i in range(0, len(tasks), batch_size):
                batch_tasks = tasks[i:i + batch_size]
                batch_num = i // batch_size + 1
                
                logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch_tasks)} functions)")
                
                # Get embeddings
                batch_results = self.get_batch_embeddings(batch_tasks)
                all_results.extend(batch_results)
                
                # Store to database
                successful_results = [r for r in batch_results if r.success]
                if successful_results:
                    documents = [tasks[i + j].text for j, r in enumerate(batch_results) if r.success]
                    metadatas = [tasks[i + j].metadata for j, r in enumerate(batch_results) if r.success]
                    
                    self.store_vectors(successful_results, documents, metadatas)
                
                # Small delay between batches
                if batch_num < total_batches:
                    time.sleep(1)
            
            # Summary
            successful_count = sum(1 for r in all_results if r.success)
            failed_count = len(all_results) - successful_count
            
            logger.info("=" * 60)
            logger.info("Vectorization Complete!")
            logger.info(f"Total functions: {len(functions_data)}")
            logger.info(f"Successfully vectorized: {successful_count}")
            logger.info(f"Failed: {failed_count}")
            logger.info(f"Success rate: {successful_count/len(functions_data)*100:.1f}%")
            logger.info("=" * 60)
            
            return successful_count > 0
            
        except Exception as e:
            logger.error(f"Failed to vectorize functions from file: {e}")
            return False
    
    def _create_function_text(self, func_name: str, func_data: Dict[str, Any]) -> str:
        """Create searchable text content from function data"""
        parts = []
        
        # Function name and synopsis
        parts.append(f"Function: {func_name}")
        if func_data.get("synopsis"):
            parts.append(f"Synopsis: {func_data['synopsis']}")
        
        # Description
        if func_data.get("description"):
            parts.append(f"Description: {func_data['description']}")
        
        # Parameters
        if func_data.get("parameters"):
            params_text = []
            for param in func_data["parameters"]:
                param_desc = f"{param.get('name', '')} ({param.get('type', '')})"
                if param.get("description"):
                    param_desc += f": {param['description']}"
                params_text.append(param_desc)
            
            if params_text:
                parts.append(f"Parameters: {'; '.join(params_text)}")
        
        # Return type and description
        if func_data.get("return_type"):
            return_text = f"Returns: {func_data['return_type']}"
            if func_data.get("return_description"):
                return_text += f" - {func_data['return_description']}"
            parts.append(return_text)
        
        # Headers and libraries
        if func_data.get("headers"):
            headers = [h.get("filename", "") for h in func_data["headers"]]
            parts.append(f"Headers: {', '.join(headers)}")
        
        if func_data.get("libraries"):
            parts.append(f"Libraries: {', '.join(func_data['libraries'])}")
        
        # Classification
        if func_data.get("classification"):
            parts.append(f"Classification: {func_data['classification']}")
        
        # See also
        if func_data.get("see_also"):
            parts.append(f"Related: {', '.join(func_data['see_also'])}")
        
        return "\n".join(parts)


def main():
    """Main function for command line usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description='QNX Functions Vectorizer')
    parser.add_argument('--input', '-i', help='Input JSON file with QNX functions')
    parser.add_argument('--test', action='store_true', help='Run test mode')
    parser.add_argument('--query', '-q', help='Test query for similarity search')
    parser.add_argument('--config', '-c', default='config.json', help='Configuration file path')
    
    args = parser.parse_args()
    
    vectorizer = HybridVectorizer(args.config)
    
    if args.test:
        # Test single embedding
        test_text = "printf function is used for formatted output"
        result = vectorizer.get_single_embedding(test_text)
        
        print(f"Test text: {test_text}")
        print(f"Success: {result.success}")
        print(f"Provider: {result.provider}")
        print(f"Vector length: {len(result.embedding) if result.embedding else 0}")
        
        # Test batch processing
        tasks = [
            VectorizeTask("abort", "abort", {"function": "abort"}),
            VectorizeTask("malloc", "malloc", {"function": "malloc"}),
            VectorizeTask("printf", "printf", {"function": "printf"})
        ]
        
        results = vectorizer.get_batch_embeddings(tasks)
        
        print(f"\nBatch test results:")
        for result in results:
            print(f"  {result.doc_id}: {'✓' if result.success else '✗'} ({result.provider})")
        
        return 0
    
    if args.query:
        # Test similarity search
        results = vectorizer.query_similar(args.query, n_results=5)
        print(f"\nQuery: {args.query}")
        print("Similar functions:")
        for result in results:
            print(f"  {result['metadata'].get('function_name', 'Unknown')}: {result['similarity']:.3f}")
        return 0
    
    if args.input:
        # Vectorize functions from file
        if not os.path.exists(args.input):
            print(f"Error: Input file not found: {args.input}")
            return 1
        
        success = vectorizer.vectorize_functions_from_file(args.input)
        return 0 if success else 1
    
    print("No action specified. Use --input to vectorize functions, --test for testing, or --query for search.")
    return 1


if __name__ == "__main__":
    main()