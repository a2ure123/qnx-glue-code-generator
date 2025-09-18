#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QNX System Comprehensive Test
Test crawler, JSON extraction, hybrid vectorization, and batch processing functions
"""

import sys
import os
import json
import tempfile
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from qnx_web_crawler import QNXWebCrawler
from openai_json_extractor import OpenAIJSONExtractor  
from hybrid_vectorizer import HybridVectorizer
from qnx_batch_processor import QNXBatchProcessor

def test_web_crawler():
    """Test web crawler"""
    print("=== Test QNX Web Crawler ===")
    
    try:
        crawler = QNXWebCrawler()
        
        # Test single function crawling
        test_functions = ["abort", "malloc"]
        functions = crawler.crawl_functions(test_functions, max_functions=2)
        
        print(f"✓ Crawler test passed")
        print(f"  Successfully crawled {len(functions)} functions")
        
        for func in functions:
            is_valid = crawler.validate_function_content(func)
            print(f"  {func.name}: {'✓' if is_valid else '✗'}")
        
        return True
        
    except Exception as e:
        print(f"✗ Crawler test failed: {e}")
        return False

def test_json_extractor():
    """Test JSON extractor"""
    print("\n=== Test JSON Extractor ===")
    
    try:
        extractor = OpenAIJSONExtractor()
        
        # Use simple HTML for testing
        test_html = """
        <html>
        <body>
        <h1>abort()</h1>
        <p>The abort() function causes abnormal process termination.</p>
        <code>void abort(void);</code>
        </body>
        </html>
        """
        
        result = extractor.extract_function_info(test_html, "abort")
        
        if result and hasattr(result, 'name'):
            print(f"✓ JSON extraction test passed")
            print(f"  Extracted function: {result.name}")
            return True
        else:
            print(f"✗ JSON extraction failed: No valid result")
            return False
            
    except Exception as e:
        print(f"✗ JSON extraction test failed: {e}")
        return False

def test_hybrid_vectorizer():
    """Test hybrid vectorizer"""
    print("\n=== Test Hybrid Vectorizer ===")
    
    try:
        vectorizer = HybridVectorizer()
        
        # Test single embedding
        result = vectorizer.get_single_embedding("test function")
        
        if result.success:
            print(f"✓ Hybrid vectorization test passed")
            print(f"  Provider used: {result.provider}")
            print(f"  Vector length: {len(result.embedding)}")
            return True
        else:
            print(f"✗ Hybrid vectorization failed: {result.error}")
            return False
            
    except Exception as e:
        print(f"✗ Hybrid vectorization test failed: {e}")
        return False

def test_batch_processor():
    """Test batch processor"""
    print("\n=== Test Batch Processor ===")
    
    try:
        processor = QNXBatchProcessor()
        
        # Use small sample for testing
        test_functions = ["abort"]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_output = f.name
        
        try:
            result = processor.process_functions(test_functions, 
                                               output_file=os.path.basename(temp_output))
            
            if result.get("success"):
                print(f"✓ Batch processing test passed")
                print(f"  Processed functions: {result['stats']['stored']}/{result['stats']['total_functions']}")
                print(f"  API usage: {result['stats']['api_usage']}")
                return True
            else:
                print(f"✗ Batch processing failed: {result.get('error')}")
                return False
                
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_output)
            except:
                pass
            
    except Exception as e:
        print(f"✗ Batch processing test failed: {e}")
        return False

def test_api_status():
    """Test API status"""
    print("\n=== Test API Status ===")
    
    try:
        # Test OpenAI API
        import os
        
        openai_key = os.getenv("OPENAI_API_KEY")
        openai_ok = bool(openai_key)
        
        print(f"✓ API status check completed")
        print(f"  OpenAI: {'✓' if openai_ok else '✗'}")
        
        return openai_ok
        
    except Exception as e:
        print(f"✗ API status check failed: {e}")
        return False

def run_all_tests():
    """Run all tests"""
    print("QNX System Comprehensive Test Start")
    print("=" * 50)
    
    tests = [
        ("API Status", test_api_status),
        ("Web Crawler", test_web_crawler),
        ("JSON Extractor", test_json_extractor),
        ("Hybrid Vectorizer", test_hybrid_vectorizer),
        ("Batch Processor", test_batch_processor),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"\n✗ {test_name} test exception: {e}")
            results[test_name] = False
    
    # Summary
    print("\n" + "=" * 50)
    print("Test Summary:")
    
    passed = 0
    total = len(results)
    
    for test_name, result in results.items():
        status = "✓ Passed" if result else "✗ Failed"
        print(f"  {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed!")
        return True
    else:
        print("⚠️  Some tests failed")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)