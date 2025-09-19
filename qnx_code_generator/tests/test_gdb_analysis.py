#!/usr/bin/env python3
"""
Test GDB analysis functionality
"""

import asyncio
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src'))

from linux_mcp.linux_mcp_server import LinuxMuslAnalyzer

async def test_gdb_analysis():
    """Test GDB analysis functionality"""
    print("=== Testing GDB Analysis ===")
    
    # Initialize analyzer
    analyzer = LinuxMuslAnalyzer()
    
    # Test 1: Check if GDB is available
    print("\n1. Testing GDB availability...")
    try:
        # Try to start GDB
        gdb_started = await analyzer._start_gdb()
        if gdb_started:
            print("✓ GDB started successfully")
            
            # Test 2: Send a simple command
            print("\n2. Testing GDB command...")
            try:
                response = await analyzer._send_gdb_command("help")
                if response and "help" in response.lower():
                    print("✓ GDB responds to commands")
                else:
                    print("✗ GDB response unclear")
            except Exception as e:
                print(f"✗ Error sending GDB command: {e}")
            
            # Test 3: Try function analysis (this will likely fail without libc.so)
            print("\n3. Testing function analysis...")
            try:
                result = await analyzer.analyze_function_with_gdb("malloc")
                if result:
                    print(f"✓ Function analysis worked: {result}")
                else:
                    print("○ Function analysis returned no result (expected without libc.so)")
            except Exception as e:
                print(f"○ Expected error analyzing function (no libc.so): {e}")
                
        else:
            print("✗ Failed to start GDB")
            
    except Exception as e:
        print(f"✗ Error testing GDB: {e}")
    
    print("\n=== GDB Test Complete ===")

if __name__ == "__main__":
    asyncio.run(test_gdb_analysis())