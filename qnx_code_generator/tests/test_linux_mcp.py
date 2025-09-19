#!/usr/bin/env python3
"""
Test script for Linux MCP server functionality
"""

import asyncio
import json
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from linux_mcp.linux_mcp_server import LinuxMuslAnalyzer

async def test_musl_source_scanning():
    """Test musl source code scanning functionality"""
    print("=== Testing Linux Musl Analyzer ===")
    
    # Initialize analyzer directly
    analyzer = LinuxMuslAnalyzer()
    
    # Test 1: Scan musl source index
    print("\n1. Testing musl source scanning...")
    try:
        result = await analyzer.scan_musl_source()
        print(f"✓ Scanned musl source: {len(result)} functions found")
        
        # Show some examples
        func_names = list(result.keys())[:5]
        for func in func_names:
            print(f"  - {func}: {result[func]} lines")
    except Exception as e:
        print(f"✗ Error scanning musl source: {e}")
    
    # Test 2: Test QNX escape function detection
    print("\n2. Testing QNX escape function detection...")
    try:
        escaped_funcs = analyzer.get_existing_qnx_escape_functions()
        print(f"✓ Found {len(escaped_funcs)} escaped functions:")
        for func in escaped_funcs[:5]:  # Show first 5
            print(f"  - {func}")
    except Exception as e:
        print(f"✗ Error getting escape functions: {e}")
    
    # Test 3: Test QNX glue code generation
    print("\n3. Testing QNX glue code plan generation...")
    try:
        qnx_info = {
            "name": "test_func",
            "synopsis": "int test_func(char *str);",
            "description": "A test function for testing",
            "parameters": [{"name": "str", "type": "char*", "description": "input string"}],
            "return_type": "int"
        }
        
        plan = await analyzer.generate_qnx_glue_plan("test_func", qnx_info)
        print(f"✓ Generated QNX glue plan:")
        print(f"  Strategy: {plan.strategy}")
        print(f"  Needs dynlink: {plan.needs_dynlink_modification}")
        print(f"  Generated code length: {len(plan.glue_code)} characters")
        if plan.dynlink_addition:
            print(f"  Dynlink addition: {plan.dynlink_addition}")
            
    except Exception as e:
        print(f"✗ Error generating glue plan: {e}")
    
    # Test 4: Test with a function that exists in Linux (malloc)
    print("\n4. Testing with existing Linux function 'malloc'...")
    try:
        qnx_info = {
            "name": "malloc",
            "synopsis": "void *malloc(size_t size);",
            "description": "Allocate memory",
            "parameters": [{"name": "size", "type": "size_t", "description": "size to allocate"}],
            "return_type": "void*"
        }
        
        plan = await analyzer.generate_qnx_glue_plan("malloc", qnx_info)
        print(f"✓ Generated malloc glue plan:")
        print(f"  Strategy: {plan.strategy}")
        print(f"  Needs dynlink: {plan.needs_dynlink_modification}")
            
    except Exception as e:
        print(f"✗ Error generating malloc glue plan: {e}")
    
    print("\n=== Test Complete ===")

if __name__ == "__main__":
    asyncio.run(test_musl_source_scanning())