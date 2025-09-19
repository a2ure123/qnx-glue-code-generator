#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Intelligent QNX-Linux Glue Code Generation Agent

This module implements a LangGraph-based agent that coordinates the entire 
glue code generation process:
1. Analyzes QNX functions using QNX MCP
2. Analyzes Linux functions using Linux MCP  
3. Generates appropriate glue code
4. Modifies dynlink.c if needed
5. Compiles and tests the changes
6. Retries on failures with error feedback
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum

# LangGraph imports
try:
    from langgraph.graph import StateGraph, END
    from langgraph.prebuilt import ToolExecutor
    from langgraph.checkpoint.sqlite import SqliteSaver
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    logging.warning("LangGraph not available - using simplified agent")

# Local imports
try:
    from ..core.mcp_client import QNXMCPClient, LinuxMCPClient
except ImportError:
    # Fallback for testing
    try:
        from src.core.mcp_client import QNXMCPClient, LinuxMCPClient
    except ImportError:
        class QNXMCPClient:
            async def connect(self): pass
            async def disconnect(self): pass
            async def get_function_info(self, name): return {"error": "No QNX MCP"}
            async def call_tool(self, tool, params): return {"error": "No QNX MCP"}
        
        class LinuxMCPClient:
            async def connect(self): pass
            async def disconnect(self): pass
            async def get_function_info(self, name): return {"error": "No Linux MCP"}
            async def call_tool(self, tool, params): return {"error": "No Linux MCP"}

logger = logging.getLogger(__name__)

class AgentState(Enum):
    """Agent states for the glue code generation process"""
    INIT = "init"
    ANALYZE_QNX = "analyze_qnx"
    ANALYZE_LINUX = "analyze_linux" 
    GENERATE_CODE = "generate_code"
    MODIFY_DYNLINK = "modify_dynlink"
    COMPILE_TEST = "compile_test"
    HANDLE_ERROR = "handle_error"
    COMPLETE = "complete"
    FAILED = "failed"

@dataclass
class GlueGenerationState:
    """State for the glue code generation process"""
    # Input
    qnx_functions: List[str]
    
    # Process state
    current_function: Optional[str] = None
    current_state: AgentState = AgentState.INIT
    retry_count: int = 0
    max_retries: int = 3
    
    # Analysis results
    qnx_function_info: Dict[str, Any] = None
    linux_function_info: Dict[str, Any] = None
    glue_plan: Dict[str, Any] = None
    
    # Generation results
    generated_code: Optional[str] = None
    dynlink_modifications: Optional[str] = None
    compilation_result: Dict[str, Any] = None
    
    # Final results
    success: bool = False
    error_message: Optional[str] = None
    completed_functions: List[str] = None
    failed_functions: List[str] = None
    
    def __post_init__(self):
        if self.completed_functions is None:
            self.completed_functions = []
        if self.failed_functions is None:
            self.failed_functions = []

class IntelligentGlueAgent:
    """Intelligent agent for QNX-Linux glue code generation"""
    
    def __init__(self, config_path: str = "config.json"):
        """Initialize the intelligent agent"""
        self.config = self._load_config(config_path)
        
        # MCP clients
        self.qnx_client = QNXMCPClient()
        self.linux_client = LinuxMCPClient()
        
        # LangGraph setup
        self.graph = None
        self.checkpointer = None
        
        if LANGGRAPH_AVAILABLE:
            self._setup_langgraph()
        
        logger.info("Intelligent Glue Agent initialized")
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load config: {e}")
            return {}
    
    def _setup_langgraph(self):
        """Setup LangGraph workflow"""
        if not LANGGRAPH_AVAILABLE:
            return
        
        # Create workflow graph
        workflow = StateGraph(GlueGenerationState)
        
        # Add nodes
        workflow.add_node("analyze_qnx", self._analyze_qnx_function)
        workflow.add_node("analyze_linux", self._analyze_linux_function)
        workflow.add_node("generate_code", self._generate_glue_code)
        workflow.add_node("modify_dynlink", self._modify_dynlink)
        workflow.add_node("compile_test", self._compile_and_test)
        workflow.add_node("handle_error", self._handle_compilation_error)
        
        # Add edges
        workflow.set_entry_point("analyze_qnx")
        
        workflow.add_edge("analyze_qnx", "analyze_linux")
        workflow.add_edge("analyze_linux", "generate_code")
        
        # Conditional edge for dynlink modification
        workflow.add_conditional_edges(
            "generate_code",
            self._should_modify_dynlink,
            {
                "modify": "modify_dynlink",
                "skip": "compile_test"
            }
        )
        
        workflow.add_edge("modify_dynlink", "compile_test")
        
        # Conditional edge for compilation result
        workflow.add_conditional_edges(
            "compile_test",
            self._check_compilation_result,
            {
                "success": END,
                "retry": "handle_error",
                "fail": END
            }
        )
        
        workflow.add_edge("handle_error", "generate_code")
        
        # Create checkpointer for persistence
        self.checkpointer = SqliteSaver.from_conn_string(":memory:")
        
        # Compile graph
        self.graph = workflow.compile(checkpointer=self.checkpointer)
    
    async def generate_glue_code_for_functions(self, functions: List[str]) -> Dict[str, Any]:
        """Generate glue code for multiple functions"""
        results = {
            "total_functions": len(functions),
            "completed": [],
            "failed": [],
            "summary": {}
        }
        
        # Connect to MCP servers
        await self.qnx_client.connect()
        await self.linux_client.connect()
        
        try:
            for func_name in functions:
                logger.info(f"Processing function: {func_name}")
                
                if LANGGRAPH_AVAILABLE:
                    result = await self._process_function_with_langgraph(func_name)
                else:
                    result = await self._process_function_simple(func_name)
                
                if result.get("success"):
                    results["completed"].append(func_name)
                    logger.info(f"Successfully processed: {func_name}")
                else:
                    results["failed"].append(func_name)
                    logger.error(f"Failed to process: {func_name} - {result.get('error')}")
            
            results["summary"] = {
                "success_rate": len(results["completed"]) / len(functions),
                "total_completed": len(results["completed"]),
                "total_failed": len(results["failed"])
            }
            
        finally:
            await self.qnx_client.disconnect()
            await self.linux_client.disconnect()
        
        return results
    
    async def _process_function_with_langgraph(self, func_name: str) -> Dict[str, Any]:
        """Process single function using LangGraph"""
        if not self.graph:
            return await self._process_function_simple(func_name)
        
        try:
            # Create initial state
            initial_state = GlueGenerationState(
                qnx_functions=[func_name],
                current_function=func_name
            )
            
            # Run the graph
            config = {"configurable": {"thread_id": f"func_{func_name}"}}
            final_state = await self.graph.ainvoke(asdict(initial_state), config)
            
            return {
                "success": final_state.get("success", False),
                "error": final_state.get("error_message"),
                "generated_code": final_state.get("generated_code"),
                "compilation_result": final_state.get("compilation_result")
            }
            
        except Exception as e:
            logger.error(f"LangGraph processing failed for {func_name}: {e}")
            return await self._process_function_simple(func_name)
    
    async def _process_function_simple(self, func_name: str) -> Dict[str, Any]:
        """Simple processing without LangGraph"""
        try:
            # Step 1: Analyze QNX function
            logger.info(f"Analyzing QNX function: {func_name}")
            qnx_info = await self.qnx_client.get_function_info(func_name)
            
            if not qnx_info or "error" in qnx_info:
                return {"success": False, "error": f"QNX function {func_name} not found"}
            
            # Step 2: Analyze Linux function
            logger.info(f"Analyzing Linux function: {func_name}")
            linux_info = await self.linux_client.get_function_info(func_name)
            
            # Step 3: Generate glue code
            logger.info(f"Generating glue code for: {func_name}")
            glue_plan = await self.linux_client.call_tool("generate_qnx_glue_code", {
                "qnx_func": func_name,
                "qnx_info": json.dumps(qnx_info)
            })
            
            if not glue_plan or "error" in glue_plan:
                return {"success": False, "error": f"Failed to generate glue code for {func_name}"}
            
            # Step 4: Modify dynlink if needed
            if glue_plan.get("needs_dynlink_modification"):
                logger.info(f"Modifying dynlink.c for: {func_name}")
                dynlink_result = await self.linux_client.call_tool("modify_dynlink", {
                    "additions": glue_plan.get("dynlink_addition", "")
                })
                
                if "error" in dynlink_result:
                    logger.warning(f"Failed to modify dynlink.c: {dynlink_result['error']}")
            
            # Step 5: Compile and test
            logger.info(f"Compiling musl library...")
            compile_result = await self.linux_client.call_tool("compile_musl", {})
            
            success = compile_result.get("success", False)
            if not success:
                logger.error(f"Compilation failed: {compile_result.get('stderr', '')}")
            
            return {
                "success": success,
                "error": None if success else compile_result.get("stderr"),
                "generated_code": glue_plan.get("glue_code"),
                "compilation_result": compile_result
            }
            
        except Exception as e:
            logger.error(f"Error processing function {func_name}: {e}")
            return {"success": False, "error": str(e)}
    
    # LangGraph node functions
    async def _analyze_qnx_function(self, state: GlueGenerationState) -> GlueGenerationState:
        """Analyze QNX function"""
        try:
            func_name = state.current_function
            logger.info(f"LangGraph: Analyzing QNX function {func_name}")
            
            qnx_info = await self.qnx_client.get_function_info(func_name)
            state.qnx_function_info = qnx_info
            state.current_state = AgentState.ANALYZE_LINUX
            
            return state
            
        except Exception as e:
            logger.error(f"QNX analysis failed: {e}")
            state.error_message = str(e)
            state.current_state = AgentState.FAILED
            return state
    
    async def _analyze_linux_function(self, state: GlueGenerationState) -> GlueGenerationState:
        """Analyze Linux function"""
        try:
            func_name = state.current_function
            logger.info(f"LangGraph: Analyzing Linux function {func_name}")
            
            linux_info = await self.linux_client.get_function_info(func_name)
            state.linux_function_info = linux_info
            state.current_state = AgentState.GENERATE_CODE
            
            return state
            
        except Exception as e:
            logger.error(f"Linux analysis failed: {e}")
            state.error_message = str(e)
            state.current_state = AgentState.FAILED
            return state
    
    async def _generate_glue_code(self, state: GlueGenerationState) -> GlueGenerationState:
        """Generate glue code"""
        try:
            func_name = state.current_function
            logger.info(f"LangGraph: Generating glue code for {func_name}")
            
            # Include previous error in generation if retrying
            qnx_info = state.qnx_function_info.copy()
            if state.retry_count > 0 and state.compilation_result:
                qnx_info["previous_compilation_error"] = state.compilation_result.get("stderr", "")
                qnx_info["retry_count"] = state.retry_count
            
            glue_plan = await self.linux_client.call_tool("generate_qnx_glue_code", {
                "qnx_func": func_name,
                "qnx_info": json.dumps(qnx_info)
            })
            
            state.glue_plan = glue_plan
            state.generated_code = glue_plan.get("glue_code")
            state.dynlink_modifications = glue_plan.get("dynlink_addition")
            state.current_state = AgentState.MODIFY_DYNLINK
            
            return state
            
        except Exception as e:
            logger.error(f"Code generation failed: {e}")
            state.error_message = str(e)
            state.current_state = AgentState.FAILED
            return state
    
    async def _modify_dynlink(self, state: GlueGenerationState) -> GlueGenerationState:
        """Modify dynlink.c if needed"""
        try:
            if state.dynlink_modifications:
                logger.info(f"LangGraph: Modifying dynlink.c")
                
                result = await self.linux_client.call_tool("modify_dynlink", {
                    "additions": state.dynlink_modifications
                })
                
                if "error" in result:
                    logger.warning(f"dynlink modification failed: {result['error']}")
            
            state.current_state = AgentState.COMPILE_TEST
            return state
            
        except Exception as e:
            logger.error(f"dynlink modification failed: {e}")
            state.error_message = str(e)
            state.current_state = AgentState.FAILED
            return state
    
    async def _compile_and_test(self, state: GlueGenerationState) -> GlueGenerationState:
        """Compile and test the changes"""
        try:
            logger.info(f"LangGraph: Compiling musl library")
            
            compile_result = await self.linux_client.call_tool("compile_musl", {})
            state.compilation_result = compile_result
            
            if compile_result.get("success"):
                state.success = True
                state.current_state = AgentState.COMPLETE
                state.completed_functions.append(state.current_function)
                logger.info(f"Successfully completed: {state.current_function}")
            else:
                state.current_state = AgentState.HANDLE_ERROR
                logger.error(f"Compilation failed for {state.current_function}")
            
            return state
            
        except Exception as e:
            logger.error(f"Compilation test failed: {e}")
            state.error_message = str(e)
            state.current_state = AgentState.FAILED
            return state
    
    async def _handle_compilation_error(self, state: GlueGenerationState) -> GlueGenerationState:
        """Handle compilation errors with retry logic"""
        try:
            state.retry_count += 1
            
            if state.retry_count <= state.max_retries:
                logger.info(f"Retrying code generation (attempt {state.retry_count}/{state.max_retries})")
                state.current_state = AgentState.GENERATE_CODE
            else:
                logger.error(f"Max retries exceeded for {state.current_function}")
                state.current_state = AgentState.FAILED
                state.failed_functions.append(state.current_function)
                state.error_message = f"Max retries exceeded: {state.compilation_result.get('stderr', 'Unknown error')}"
            
            return state
            
        except Exception as e:
            logger.error(f"Error handling failed: {e}")
            state.error_message = str(e)
            state.current_state = AgentState.FAILED
            return state
    
    # LangGraph conditional functions
    def _should_modify_dynlink(self, state: GlueGenerationState) -> str:
        """Determine if dynlink should be modified"""
        if state.glue_plan and state.glue_plan.get("needs_dynlink_modification"):
            return "modify"
        return "skip"
    
    def _check_compilation_result(self, state: GlueGenerationState) -> str:
        """Check compilation result and determine next action"""
        if state.compilation_result and state.compilation_result.get("success"):
            return "success"
        elif state.retry_count < state.max_retries:
            return "retry"
        else:
            return "fail"

async def main():
    """Test the intelligent agent"""
    agent = IntelligentGlueAgent()
    
    # Test with a few functions
    test_functions = ["malloc", "printf", "some_qnx_specific_func"]
    
    results = await agent.generate_glue_code_for_functions(test_functions)
    
    print("=== Intelligent Agent Results ===")
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    asyncio.run(main())