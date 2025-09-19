#!/usr/bin/env python3
"""
Test Linux MCP System
Comprehensive tests for Linux MCP server functionality
"""

import asyncio
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src'))

from linux_mcp.linux_mcp_server import LinuxMuslAnalyzer

async def test_musl_analyzer():
    """Test Linux musl analyzer functionality"""
    print("=== Testing Linux Musl Analyzer ===")
    
    analyzer = LinuxMuslAnalyzer()
    
    # Test 1: Scan musl source
    print("\n1. Testing musl source scanning...")
    try:
        result = await analyzer.scan_musl_source()
        print(f"✓ Scanned musl source: {len(result)} functions found")
        assert len(result) > 0, "Should find functions in musl source"
        return True
    except Exception as e:
        print(f"✗ Error scanning musl source: {e}")
        return False

async def test_qnx_escape_functions():
    """Test QNX escape function detection"""
    print("\n2. Testing QNX escape function detection...")
    
    analyzer = LinuxMuslAnalyzer()
    
    try:
        escaped_funcs = analyzer.get_existing_qnx_escape_functions()
        print(f"✓ Found {len(escaped_funcs)} escaped functions")
        assert len(escaped_funcs) > 0, "Should find ESCAPE_QNX_FUNC entries"
        
        # Check that known functions are detected
        expected_funcs = ['stat', 'malloc', 'socket']
        for func in expected_funcs:
            if func in escaped_funcs:
                print(f"  ✓ Found expected function: {func}")
            else:
                print(f"  ○ Function {func} not in escape list (may be expected)")
        
        return True
    except Exception as e:
        print(f"✗ Error getting escape functions: {e}")
        return False

async def test_glue_code_generation():
    """Test QNX glue code generation"""
    print("\n3. Testing QNX glue code generation...")
    
    analyzer = LinuxMuslAnalyzer()
    
    try:
        qnx_info = {
            "name": "test_function",
            "synopsis": "int test_function(char *str);",
            "description": "A test function for testing",
            "parameters": [{"name": "str", "type": "char*"}],
            "return_type": "int"
        }
        
        plan = await analyzer.generate_qnx_glue_plan("test_function", qnx_info)
        print(f"✓ Generated glue plan: {plan.strategy}")
        
        assert plan.glue_code, "Should generate glue code"
        assert len(plan.glue_code) > 0, "Glue code should not be empty"
        
        print(f"  Generated {len(plan.glue_code)} characters of code")
        return True
    except Exception as e:
        print(f"✗ Error generating glue code: {e}")
        return False

async def run_linux_mcp_tests():
    """Run all Linux MCP tests"""
    print("🐧 Linux MCP System Tests")
    print("=" * 40)
    
    tests = [
        ("Musl Analyzer", test_musl_analyzer),
        ("QNX Escape Functions", test_qnx_escape_functions),
        ("Glue Code Generation", test_glue_code_generation),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            results[test_name] = await test_func()
        except Exception as e:
            print(f"\n✗ {test_name} test exception: {e}")
            results[test_name] = False
    
    # Summary
    print("\n" + "=" * 40)
    print("Linux MCP Test Summary:")
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✓ Passed" if result else "✗ Failed"
        print(f"  {test_name}: {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    return passed == total

if __name__ == "__main__":
    success = asyncio.run(run_linux_mcp_tests())
    sys.exit(0 if success else 1)