#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QNX MCP Server Test Script
Test basic functionality of the MCP server
"""

import asyncio
import sys
import os

# Add parent directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from qnx_mcp_server import QNXFunctionsMCPServer

async def test_mcp_server():
    """Test MCP server functionality"""
    print("=== QNX MCP Server Test ===")
    
    # Initialize server
    server = QNXFunctionsMCPServer()
    await server.initialize_vector_db()
    
    # Test 1: Get available function list
    print("\n1. Test getting available function list...")
    functions = await server.get_available_functions(limit=10)
    print(f"Found {len(functions)} functions:")
    for func in functions[:5]:
        print(f"  - {func}")
    if len(functions) > 5:
        print(f"  ... {len(functions) - 5} more functions")
    
    # Test 2: Search functions
    print("\n2. Test function search...")
    test_queries = ["memory allocation", "string", "file operations"]
    
    for query in test_queries:
        print(f"\nSearch: '{query}'")
        results = await server.search_functions(query, n_results=3)
        if results:
            for i, result in enumerate(results, 1):
                print(f"  {i}. {result['function_name']} (similarity: {result['similarity']:.3f})")
        else:
            print("  No related functions found")
    
    # Test 3: Get function details
    print("\n3. Test getting function details...")
    if functions:
        test_function = functions[0]
        print(f"\nGet function details: {test_function}")
        details = await server.get_function_details(test_function)
        if details:
            func_data = details.get("function_data", {})
            print(f"  Function name: {func_data.get('name', 'N/A')}")
            print(f"  Description: {func_data.get('description', 'N/A')[:100]}...")
            print(f"  Number of parameters: {len(func_data.get('parameters', []))}")
            print(f"  Return type: {func_data.get('return_type', 'N/A')}")
        else:
            print("  No function details found")
    
    print("\n=== Test complete ===")

if __name__ == "__main__":
    asyncio.run(test_mcp_server())