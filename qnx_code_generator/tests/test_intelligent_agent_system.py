#!/usr/bin/env python3
"""
Test Intelligent Agent System
Tests for the LangGraph-based intelligent agent
"""

import asyncio
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src'))

def test_langgraph_availability():
    """Test if LangGraph is available"""
    print("=== Testing LangGraph Availability ===")
    
    try:
        from langgraph.graph import StateGraph, END
        from langgraph.checkpoint.sqlite import SqliteSaver
        print("✓ LangGraph is available")
        return True
    except ImportError as e:
        print(f"✗ LangGraph not available: {e}")
        print("  Install with: pip install langgraph")
        return False

def test_agent_state_management():
    """Test agent state management"""
    print("\n=== Testing Agent State Management ===")
    
    try:
        from glue_generator.intelligent_agent import GlueGenerationState, AgentState
        
        # Test state creation
        test_state = GlueGenerationState(
            qnx_functions=["test_func"],
            current_function="test_func"
        )
        
        print(f"✓ State created successfully")
        print(f"  Current function: {test_state.current_function}")
        print(f"  Current state: {test_state.current_state}")
        print(f"  Max retries: {test_state.max_retries}")
        
        assert test_state.current_function == "test_func"
        assert test_state.current_state == AgentState.INIT
        assert test_state.max_retries == 3
        
        return True
    except Exception as e:
        print(f"✗ Error testing state management: {e}")
        return False

async def test_agent_initialization():
    """Test agent initialization"""
    print("\n=== Testing Agent Initialization ===")
    
    try:
        from glue_generator.intelligent_agent import IntelligentGlueAgent
        
        agent = IntelligentGlueAgent()
        print("✓ Agent initialized successfully")
        print(f"  Config loaded: {bool(agent.config)}")
        print(f"  Has QNX client: {hasattr(agent, 'qnx_client')}")
        print(f"  Has Linux client: {hasattr(agent, 'linux_client')}")
        
        return True
    except Exception as e:
        print(f"✗ Error initializing agent: {e}")
        return False

async def test_simple_processing():
    """Test simple processing (without MCP servers)"""
    print("\n=== Testing Simple Processing ===")
    
    try:
        from glue_generator.intelligent_agent import IntelligentGlueAgent
        
        agent = IntelligentGlueAgent()
        
        # Test simple processing for non-existent function
        result = await agent._process_function_simple("test_function")
        
        print("✓ Simple processing completed")
        print(f"  Success: {result.get('success')}")
        print(f"  Has error: {'error' in result}")
        
        # Should fail for non-existent function
        assert result.get('success') is False
        
        return True
    except Exception as e:
        print(f"✗ Error in simple processing: {e}")
        return False

async def run_agent_tests():
    """Run all intelligent agent tests"""
    print("🤖 Intelligent Agent System Tests")
    print("=" * 45)
    
    tests = [
        ("LangGraph Availability", test_langgraph_availability),
        ("Agent State Management", test_agent_state_management),
        ("Agent Initialization", test_agent_initialization),
        ("Simple Processing", test_simple_processing),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            if asyncio.iscoroutinefunction(test_func):
                results[test_name] = await test_func()
            else:
                results[test_name] = test_func()
        except Exception as e:
            print(f"\n✗ {test_name} test exception: {e}")
            results[test_name] = False
    
    # Summary
    print("\n" + "=" * 45)
    print("Intelligent Agent Test Summary:")
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✓ Passed" if result else "✗ Failed"
        print(f"  {test_name}: {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    return passed == total

if __name__ == "__main__":
    success = asyncio.run(run_agent_tests())
    sys.exit(0 if success else 1)