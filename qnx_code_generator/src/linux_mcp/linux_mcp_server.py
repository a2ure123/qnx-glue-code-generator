#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Linux Function Information MCP Server with musl source code analysis

This MCP server provides Linux function information by:
1. Parsing musl source code from configured directory
2. Using GDB to analyze compiled libc.so functions
3. Generating QNX glue code and dynlink.c modifications
4. Supporting compilation verification and error feedback
"""

import asyncio
import logging
import json
import os
import re
import subprocess
import tempfile
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path

# MCP server imports
from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.types import Resource, Tool, TextContent, ImageContent, EmbeddedResource
import mcp.types as types

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class LinuxFunctionInfo:
    """Linux function information structure"""
    name: str
    signature: str
    description: str
    parameters: List[Dict[str, Any]]
    return_type: str
    return_description: str
    headers: List[str]
    source_file: str
    source_location: str  # file:line_start-line_end
    source_code: str
    library: str
    availability: str
    gdb_analysis: Optional[Dict[str, Any]] = None
    examples: List[str] = None
    notes: Optional[str] = None

@dataclass
class QNXGlueCodePlan:
    """QNX glue code generation plan"""
    qnx_function: str
    linux_function: Optional[str]
    strategy: str  # "direct", "wrap_with_prefix", "create_stub", "complex"
    needs_dynlink_modification: bool
    qnx_support_file: Optional[str]  # Path to generate QNX support file
    glue_code: str
    dynlink_addition: Optional[str]  # Code to add to dynlink.c
    confidence: float

class LinuxMuslAnalyzer:
    """Analyzes musl source code and libc.so using GDB"""
    
    def __init__(self, config_path: str = "config.json"):
        """Initialize musl analyzer"""
        self.config = self._load_config(config_path)
        
        # musl source configuration
        self.musl_path = self.config.get("linux_system", {}).get("musl_source_path", 
                                                                 "/home/a2ure/Desktop/afl-qnx/qol/musl")
        self.libc_path = self.config.get("linux_system", {}).get("libc_path", 
                                                                 "/home/a2ure/Desktop/afl-qnx/qol/musl/lib/libc.so")
        self.qnx_support_dir = self.config.get("linux_system", {}).get("qnx_support_dir", 
                                                                       "/home/a2ure/Desktop/afl-qnx/qol/qnxsupport")
        self.dynlink_path = self.config.get("linux_system", {}).get("dynlink_path",
                                                                   "/home/a2ure/Desktop/afl-qnx/qol/musl/ldso/dynlink.c")
        
        # Function database
        self.function_db: Dict[str, LinuxFunctionInfo] = {}
        self.source_index: Dict[str, List[str]] = {}  # file -> function_names
        
        # GDB process
        self.gdb_process = None
        
        logger.info(f"Linux musl analyzer initialized with musl path: {self.musl_path}")
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration file"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load config: {e}")
            return {}
    
    async def scan_musl_source(self) -> Dict[str, int]:
        """Scan musl source code and build function index"""
        stats = {"files_scanned": 0, "functions_found": 0, "errors": 0}
        
        if not os.path.exists(self.musl_path):
            logger.error(f"musl source path not found: {self.musl_path}")
            return stats
        
        src_path = os.path.join(self.musl_path, "src")
        if not os.path.exists(src_path):
            logger.error(f"musl src directory not found: {src_path}")
            return stats
        
        # Scan all C files in src directory
        for root, dirs, files in os.walk(src_path):
            for file in files:
                if file.endswith('.c'):
                    file_path = os.path.join(root, file)
                    try:
                        functions = await self._parse_c_file(file_path)
                        self.source_index[file_path] = functions
                        stats["functions_found"] += len(functions)
                        stats["files_scanned"] += 1
                        
                        logger.debug(f"Parsed {file_path}: found {len(functions)} functions")
                        
                    except Exception as e:
                        logger.error(f"Error parsing {file_path}: {e}")
                        stats["errors"] += 1
        
        logger.info(f"musl source scan complete: {stats}")
        return stats
    
    async def _parse_c_file(self, file_path: str) -> List[str]:
        """Parse C file and extract function definitions"""
        functions = []
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Find function definitions using regex
            # Look for pattern: type function_name(parameters) {
            func_pattern = r'^([a-zA-Z_][a-zA-Z0-9_\s\*]*)\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\([^)]*\)\s*\{'
            
            lines = content.split('\n')
            for i, line in enumerate(lines):
                match = re.match(func_pattern, line.strip())
                if match and not line.strip().startswith('//'):
                    func_name = match.group(2)
                    # Skip static functions and macros
                    if not line.strip().startswith('static') and not line.strip().startswith('#'):
                        
                        # Extract full function info
                        func_info = await self._extract_function_info(content, func_name, file_path, i)
                        if func_info:
                            functions.append(func_name)
                            self.function_db[func_name] = func_info
        
        except Exception as e:
            logger.error(f"Error reading {file_path}: {e}")
        
        return functions
    
    async def _extract_function_info(self, content: str, func_name: str, file_path: str, line_no: int) -> Optional[LinuxFunctionInfo]:
        """Extract detailed function information"""
        try:
            lines = content.split('\n')
            
            # Find function start and end
            start_line = line_no
            brace_count = 0
            end_line = start_line
            
            for i in range(start_line, len(lines)):
                line = lines[i]
                brace_count += line.count('{') - line.count('}')
                if brace_count == 0 and '{' in lines[start_line:i+1]:
                    end_line = i
                    break
            
            # Extract function source code
            func_source = '\n'.join(lines[start_line:end_line+1])
            
            # Parse function signature
            signature_lines = []
            for i in range(max(0, start_line-5), start_line+3):
                if i < len(lines):
                    signature_lines.append(lines[i])
            
            signature = self._parse_function_signature('\n'.join(signature_lines), func_name)
            
            return LinuxFunctionInfo(
                name=func_name,
                signature=signature,
                description=f"Function from {os.path.basename(file_path)}",
                parameters=[],  # TODO: Parse parameters
                return_type="unknown",  # TODO: Parse return type
                return_description="",
                headers=[],  # TODO: Determine headers
                source_file=file_path,
                source_location=f"{file_path}:{start_line+1}-{end_line+1}",
                source_code=func_source,
                library="musl",
                availability="musl"
            )
            
        except Exception as e:
            logger.error(f"Error extracting function info for {func_name}: {e}")
            return None
    
    def _parse_function_signature(self, text: str, func_name: str) -> str:
        """Parse function signature from text"""
        lines = text.split('\n')
        for line in lines:
            if func_name in line and '(' in line:
                return line.strip()
        return f"unknown {func_name}()"
    
    async def analyze_function_with_gdb(self, func_name: str) -> Optional[Dict[str, Any]]:
        """Analyze function using GDB"""
        try:
            if not os.path.exists(self.libc_path):
                logger.warning(f"libc.so not found: {self.libc_path}")
                return None
            
            # Start GDB process if not already running
            if not self.gdb_process:
                await self._start_gdb()
            
            if not self.gdb_process:
                return None
            
            # GDB commands to analyze function
            commands = [
                f"info address {func_name}",
                f"disassemble {func_name}",
                f"info variables {func_name}",
                f"ptype {func_name}"
            ]
            
            results = {}
            for cmd in commands:
                result = await self._send_gdb_command(cmd)
                results[cmd] = result
            
            return results
            
        except Exception as e:
            logger.error(f"GDB analysis failed for {func_name}: {e}")
            return None
    
    async def _start_gdb(self) -> bool:
        """Start GDB process"""
        try:
            self.gdb_process = await asyncio.create_subprocess_exec(
                'gdb', self.libc_path, '-q',
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Initialize GDB
            await self._send_gdb_command("set confirm off")
            await self._send_gdb_command("set pagination off")
            
            logger.info("GDB process started")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start GDB: {e}")
            return False
    
    async def _send_gdb_command(self, command: str) -> str:
        """Send command to GDB and get response"""
        try:
            if not self.gdb_process:
                return ""
            
            self.gdb_process.stdin.write(f"{command}\n".encode())
            await self.gdb_process.stdin.drain()
            
            # Read response with timeout
            try:
                response = await asyncio.wait_for(
                    self.gdb_process.stdout.readline(), timeout=5.0
                )
                return response.decode().strip()
            except asyncio.TimeoutError:
                return ""
            
        except Exception as e:
            logger.error(f"GDB command failed: {command} - {e}")
            return ""
    
    def get_existing_qnx_escape_functions(self) -> List[str]:
        """Get list of functions already in ESCAPE_QNX_FUNC"""
        escaped_funcs = []
        
        try:
            with open(self.dynlink_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Find ESCAPE_QNX_FUNC calls
            pattern = r'ESCAPE_QNX_FUNC\(([^)]+)\);'
            matches = re.findall(pattern, content)
            
            escaped_funcs = [match.strip() for match in matches]
            logger.info(f"Found {len(escaped_funcs)} functions in ESCAPE_QNX_FUNC")
            
        except Exception as e:
            logger.error(f"Error reading dynlink.c: {e}")
        
        return escaped_funcs
    
    async def generate_qnx_glue_plan(self, qnx_func: str, qnx_info: Dict[str, Any]) -> QNXGlueCodePlan:
        """Generate QNX glue code plan"""
        
        # Check if function exists in Linux
        linux_func_info = self.function_db.get(qnx_func)
        escaped_funcs = self.get_existing_qnx_escape_functions()
        
        if not linux_func_info:
            # Strategy 1: Create stub in qnxsupport
            return QNXGlueCodePlan(
                qnx_function=qnx_func,
                linux_function=None,
                strategy="create_stub",
                needs_dynlink_modification=False,
                qnx_support_file=f"{self.qnx_support_dir}/{qnx_func}.c",
                glue_code=self._generate_stub_code(qnx_func, qnx_info),
                dynlink_addition=None,
                confidence=0.7
            )
        
        elif qnx_func in escaped_funcs:
            # Strategy 2: Function already escaped, create _qnx_ version
            return QNXGlueCodePlan(
                qnx_function=qnx_func,
                linux_function=qnx_func,
                strategy="wrap_with_prefix",
                needs_dynlink_modification=False,
                qnx_support_file=f"{self.qnx_support_dir}/_qnx_{qnx_func}.c",
                glue_code=self._generate_qnx_wrapper_code(qnx_func, linux_func_info, qnx_info),
                dynlink_addition=None,
                confidence=0.9
            )
        
        else:
            # Strategy 3: Need to add to ESCAPE_QNX_FUNC and create wrapper
            return QNXGlueCodePlan(
                qnx_function=qnx_func,
                linux_function=qnx_func,
                strategy="wrap_with_prefix",
                needs_dynlink_modification=True,
                qnx_support_file=f"{self.qnx_support_dir}/_qnx_{qnx_func}.c",
                glue_code=self._generate_qnx_wrapper_code(qnx_func, linux_func_info, qnx_info),
                dynlink_addition=f"\tESCAPE_QNX_FUNC({qnx_func});",
                confidence=0.8
            )
    
    def _generate_stub_code(self, func_name: str, qnx_info: Dict[str, Any]) -> str:
        """Generate stub code for QNX-only functions"""
        signature = qnx_info.get('signature', f'int {func_name}(void)')
        description = qnx_info.get('description', f'QNX function {func_name}')
        
        return f'''/*
 * QNX function {func_name} - stub implementation
 * {description}
 * Generated automatically
 */

#include <errno.h>
#include <stdio.h>

{signature} {{
    // TODO: Implement QNX-specific behavior for {func_name}
    printf("Warning: QNX function {func_name}() called - stub implementation\\n");
    errno = ENOSYS;  // Function not implemented
    return -1;
}}
'''
    
    def _generate_qnx_wrapper_code(self, func_name: str, linux_info: LinuxFunctionInfo, qnx_info: Dict[str, Any]) -> str:
        """Generate QNX wrapper code that calls Linux implementation"""
        qnx_signature = qnx_info.get('signature', linux_info.signature)
        
        return f'''/*
 * QNX wrapper for {func_name}
 * Maps QNX behavior to Linux implementation
 * Generated automatically
 */

#include <stdio.h>
#include <errno.h>

// Forward declaration of Linux implementation
extern {linux_info.signature.replace(func_name, f"__linux_{func_name}")};

{qnx_signature.replace(func_name, f"_qnx_{func_name}")} {{
    // TODO: Add QNX-specific parameter conversion if needed
    
    // Call Linux implementation
    return __linux_{func_name}(/* TODO: map parameters */);
}}
'''

class LinuxFunctionMCPServer:
    """Linux Function Information MCP Server with musl analysis"""
    
    def __init__(self, config_path: str = "config.json"):
        """Initialize Linux MCP server"""
        self.config = self._load_config(config_path)
        self.server = Server("linux-function-musl")
        self.analyzer = LinuxMuslAnalyzer(config_path)
        
        # Initialize server tools
        self._register_tools()
        
        logger.info("Linux Function MCP Server (musl) initialized")
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration file"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load config: {e}")
            return {}
    
    def _register_tools(self):
        """Register MCP tools"""
        
        @self.server.call_tool()
        async def scan_musl_source() -> List[types.TextContent]:
            """Scan musl source code and build function index"""
            try:
                stats = await self.analyzer.scan_musl_source()
                
                return [types.TextContent(
                    type="text",
                    text=json.dumps({
                        "message": "musl source scan completed",
                        "statistics": stats,
                        "total_functions": len(self.analyzer.function_db),
                        "sample_functions": list(self.analyzer.function_db.keys())[:10]
                    }, indent=2)
                )]
                
            except Exception as e:
                logger.error(f"Error scanning musl source: {e}")
                return [types.TextContent(
                    type="text",
                    text=json.dumps({"error": str(e)}, indent=2)
                )]
        
        @self.server.call_tool()
        async def get_linux_function_info(name: str) -> List[types.TextContent]:
            """Get Linux function information from musl source"""
            try:
                func_info = self.analyzer.function_db.get(name)
                if not func_info:
                    return [types.TextContent(
                        type="text",
                        text=json.dumps({
                            "error": f"Function '{name}' not found in musl source",
                            "available_functions": len(self.analyzer.function_db),
                            "suggestions": [f for f in self.analyzer.function_db.keys() if name in f][:5]
                        }, indent=2)
                    )]
                
                # Get GDB analysis if available
                gdb_info = await self.analyzer.analyze_function_with_gdb(name)
                if gdb_info:
                    func_info.gdb_analysis = gdb_info
                
                return [types.TextContent(
                    type="text",
                    text=json.dumps(asdict(func_info), indent=2)
                )]
                
            except Exception as e:
                logger.error(f"Error getting Linux function info: {e}")
                return [types.TextContent(
                    type="text",
                    text=json.dumps({"error": str(e)}, indent=2)
                )]
        
        @self.server.call_tool()
        async def generate_qnx_glue_code(qnx_func: str, qnx_info: str) -> List[types.TextContent]:
            """Generate QNX glue code plan and implementation"""
            try:
                # Parse QNX info (JSON string)
                qnx_data = json.loads(qnx_info) if isinstance(qnx_info, str) else qnx_info
                
                # Generate glue code plan
                plan = await self.analyzer.generate_qnx_glue_plan(qnx_func, qnx_data)
                
                return [types.TextContent(
                    type="text",
                    text=json.dumps({
                        "qnx_function": plan.qnx_function,
                        "strategy": plan.strategy,
                        "needs_dynlink_modification": plan.needs_dynlink_modification,
                        "qnx_support_file": plan.qnx_support_file,
                        "confidence": plan.confidence,
                        "glue_code": plan.glue_code,
                        "dynlink_addition": plan.dynlink_addition
                    }, indent=2)
                )]
                
            except Exception as e:
                logger.error(f"Error generating QNX glue code: {e}")
                return [types.TextContent(
                    type="text",
                    text=json.dumps({"error": str(e)}, indent=2)
                )]
        
        @self.server.call_tool()
        async def modify_dynlink(additions: str) -> List[types.TextContent]:
            """Add ESCAPE_QNX_FUNC entries to dynlink.c"""
            try:
                # Read current dynlink.c
                with open(self.analyzer.dynlink_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Find insertion point (after last ESCAPE_QNX_FUNC)
                lines = content.split('\n')
                insert_line = -1
                
                for i, line in enumerate(lines):
                    if 'ESCAPE_QNX_FUNC(' in line:
                        insert_line = i + 1
                
                if insert_line == -1:
                    return [types.TextContent(
                        type="text",
                        text=json.dumps({"error": "Could not find ESCAPE_QNX_FUNC section in dynlink.c"}, indent=2)
                    )]
                
                # Insert new entries
                new_lines = additions.strip().split('\n')
                lines[insert_line:insert_line] = new_lines
                
                # Write back to file
                with open(self.analyzer.dynlink_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(lines))
                
                return [types.TextContent(
                    type="text",
                    text=json.dumps({
                        "message": "dynlink.c modified successfully",
                        "inserted_lines": len(new_lines),
                        "dynlink_path": self.analyzer.dynlink_path
                    }, indent=2)
                )]
                
            except Exception as e:
                logger.error(f"Error modifying dynlink.c: {e}")
                return [types.TextContent(
                    type="text",
                    text=json.dumps({"error": str(e)}, indent=2)
                )]
        
        @self.server.call_tool()
        async def compile_musl() -> List[types.TextContent]:
            """Compile musl library to test changes"""
            try:
                # Change to musl directory and compile
                result = subprocess.run(
                    ['make', 'clean', '&&', 'make'],
                    cwd=self.analyzer.musl_path,
                    capture_output=True,
                    text=True,
                    shell=True,
                    timeout=300
                )
                
                return [types.TextContent(
                    type="text",
                    text=json.dumps({
                        "success": result.returncode == 0,
                        "return_code": result.returncode,
                        "stdout": result.stdout,
                        "stderr": result.stderr
                    }, indent=2)
                )]
                
            except subprocess.TimeoutExpired:
                return [types.TextContent(
                    type="text",
                    text=json.dumps({"error": "Compilation timed out"}, indent=2)
                )]
            except Exception as e:
                logger.error(f"Error compiling musl: {e}")
                return [types.TextContent(
                    type="text",
                    text=json.dumps({"error": str(e)}, indent=2)
                )]

async def main():
    """Main function to run the Linux MCP server"""
    server = LinuxFunctionMCPServer()
    
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="linux-function-musl",
                server_version="1.0.0",
                capabilities=server.server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())