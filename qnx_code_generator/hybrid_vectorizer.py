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
        """Batch get embeddings"""
        results = []
        
        logger.info(f"Starting batch processing of {len(tasks)} embedding tasks")
        
        for i, task in enumerate(tasks):
            logger.debug(f"Processing {i+1}/{len(tasks)}: {task.text[:50]}...")
            
            # Get embedding using OpenAI
            embedding = None
            provider = ""
            
            if self.openai_available:
                embedding = self.get_embedding_openai(task.text)
                if embedding:
                    provider = "openai"
            
            # Create result
            if embedding:
                result = VectorizeResult(
                    doc_id=task.doc_id,
                    embedding=embedding,
                    success=True,
                    provider=provider
                )
            else:
                result = VectorizeResult(
                    doc_id=task.doc_id,
                    embedding=[],
                    success=False,
                    error="OpenAI embedding failed"
                )
            
            results.append(result)
            
            # Simple rate limiting
            time.sleep(0.2)
        
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


def main():
    """Test OpenAI vectorizer"""
    vectorizer = HybridVectorizer()
    
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


if __name__ == "__main__":
    main()