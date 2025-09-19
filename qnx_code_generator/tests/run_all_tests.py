#!/usr/bin/env python3
"""
Run All Tests for QNX-Linux Glue Code Generator

This script runs all test suites for the system:
1. System integration tests
2. Linux MCP system tests  
3. Intelligent agent tests
4. GDB analysis tests
"""

import asyncio
import subprocess
import sys
import os

def run_test_file(test_file):
    """Run a test file and return success status"""
    print(f"\n🚀 Running {test_file}...")
    print("=" * 50)
    
    try:
        result = subprocess.run([sys.executable, test_file], 
                              cwd=os.path.dirname(__file__),
                              capture_output=True, 
                              text=True)
        
        # Print output
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        success = result.returncode == 0
        print(f"\n{'✓ PASSED' if success else '✗ FAILED'}: {test_file}")
        return success
        
    except Exception as e:
        print(f"✗ Exception running {test_file}: {e}")
        return False

async def main():
    """Main test runner"""
    print("🧪 QNX-Linux Glue Code Generator - Full Test Suite")
    print("=" * 60)
    
    # Test files to run (in order of importance)
    test_files = [
        "system_test_summary.py",
        "test_linux_mcp_system.py", 
        "test_intelligent_agent_system.py",
        "test_gdb_analysis.py",
    ]
    
    results = {}
    
    for test_file in test_files:
        test_path = os.path.join(os.path.dirname(__file__), test_file)
        if os.path.exists(test_path):
            results[test_file] = run_test_file(test_file)
        else:
            print(f"⚠️  Test file not found: {test_file}")
            results[test_file] = False
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_file, result in results.items():
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"  {test_file:30} {status}")
    
    print(f"\nOverall Result: {passed}/{total} test suites passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED!")
        return True
    else:
        print("⚠️  SOME TESTS FAILED")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)