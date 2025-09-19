#!/usr/bin/env python3
"""
Test the intelligent agent system
"""

import asyncio
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

try:
    from glue_generator.intelligent_agent import IntelligentGlueAgent
    LANGGRAPH_AVAILABLE = True
except ImportError as e:
    print(f"Warning: LangGraph not available - {e}")
    LANGGRAPH_AVAILABLE = False

async def test_intelligent_agent():
    """Test the intelligent agent system"""
    print("=== Testing Intelligent Glue Agent ===")
    
    if not LANGGRAPH_AVAILABLE:
        print("✗ Cannot test intelligent agent - LangGraph dependencies not available")
        print("  To install: pip install langgraph")
        return
    
    # Test 1: Initialize agent
    print("\n1. Testing agent initialization...")
    try:
        agent = IntelligentGlueAgent()
        print("✓ Intelligent agent initialized successfully")
        
        # Test 2: Test simple function processing without MCP servers
        print("\n2. Testing simple function processing...")
        try:
            # This will test the simplified processing path
            result = await agent._process_function_simple("test_function")
            
            if result.get("success") is False:
                # Expected for test function that doesn't exist
                print("○ Simple processing correctly reported failure for non-existent function")
            else:
                print(f"? Unexpected success: {result}")
                
        except Exception as e:
            print(f"○ Expected error in simple processing (no MCP servers): {e}")
        
        print("\n3. Testing agent configuration...")
        print(f"  - Config loaded: {bool(agent.config)}")
        print(f"  - LangGraph available: {agent.graph is not None}")
        print(f"  - Checkpointer available: {agent.checkpointer is not None}")
        
    except Exception as e:
        print(f"✗ Error initializing agent: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n=== Intelligent Agent Test Complete ===")

async def test_langgraph_workflow():
    """Test LangGraph workflow structure"""
    print("\n=== Testing LangGraph Workflow ===")
    
    if not LANGGRAPH_AVAILABLE:
        print("✗ LangGraph not available for workflow testing")
        return
    
    try:
        from glue_generator.intelligent_agent import GlueGenerationState, AgentState
        
        # Test state creation
        print("\n1. Testing state management...")
        test_state = GlueGenerationState(
            qnx_functions=["test_func"],
            current_function="test_func"
        )
        
        print(f"✓ State created with:")
        print(f"  - Current function: {test_state.current_function}")
        print(f"  - Current state: {test_state.current_state}")
        print(f"  - Max retries: {test_state.max_retries}")
        print(f"  - Completed functions: {len(test_state.completed_functions)}")
        
    except Exception as e:
        print(f"✗ Error testing workflow: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_intelligent_agent())
    asyncio.run(test_langgraph_workflow())