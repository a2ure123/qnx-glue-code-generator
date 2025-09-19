#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Linux Function Information MCP Server with Enhanced GDB-based Analysis

This MCP server provides comprehensive Linux function information through:

PRIMARY WORKFLOW (Recommended):
1. GDB-based precise function location in compiled libc.so
2. Intelligent brace matching to extract complete function source code
3. AI-powered function analysis for semantic understanding
4. Smart caching for performance optimization

TOOLS PROVIDED:
- smart_function_lookup: Primary tool for individual function analysis
- batch_smart_analysis: Efficient batch processing of multiple functions
- scan_musl_source: Fallback regex-based source scanning
- get_linux_function_info: Legacy function info retrieval
- generate_qnx_glue_code: QNX adaptation code generation
- modify_dynlink: Automated dynlink.c modifications
- compile_musl: Build verification and testing

FEATURES:
- Precise GDB-based function location
- Context-aware source code extraction
- AI-enhanced function analysis
- Concurrent batch processing
- Intelligent caching system
- Comprehensive error handling
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
import time

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
    function_address: Optional[str] = None
    ai_analysis: Optional[Dict[str, Any]] = None

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
        self.gdb_initialized = False
        self.function_cache: Dict[str, LinuxFunctionInfo] = {}
        
        logger.info(f"Linux musl analyzer initialized with musl path: {self.musl_path}")
        
        # AI analysis settings
        self.ai_provider = self.config.get("ai_settings", {}).get("provider", "claude")
        self.ai_config = self.config.get("ai_settings", {}).get(self.ai_provider, {})
        
        # 代码生成专用AI配置
        code_gen_settings = self.config.get("ai_settings", {}).get("code_generation", {})
        if code_gen_settings:
            self.code_gen_ai_provider = code_gen_settings.get("provider", "claude")
            self.code_gen_ai_config = code_gen_settings.get(self.code_gen_ai_provider, {})
        else:
            # 如果没有单独配置，使用默认AI配置
            self.code_gen_ai_provider = self.ai_provider
            self.code_gen_ai_config = self.ai_config
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration file"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load config: {e}")
            return {}
    
    async def scan_musl_source(self) -> Dict[str, int]:
        """扫描 musl 源码并构建函数索引 (备用方案)"""
        stats = {"files_scanned": 0, "functions_found": 0, "errors": 0, "method": "regex_fallback"}
        
        if not os.path.exists(self.musl_path):
            logger.error(f"musl source path not found: {self.musl_path}")
            return stats
        
        src_path = os.path.join(self.musl_path, "src")
        if not os.path.exists(src_path):
            logger.error(f"musl src directory not found: {src_path}")
            return stats
        
        logger.info("Starting musl source scan (regex-based fallback method)")
        
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
    
    async def batch_smart_analysis(self, func_names: List[str], max_concurrent: int = 5) -> Dict[str, Any]:
        """批量智能分析函数"""
        try:
            results = {
                "analyzed_functions": {},
                "failed_functions": [],
                "statistics": {
                    "total_requested": len(func_names),
                    "successful": 0,
                    "failed": 0,
                    "cached": 0
                }
            }
            
            # 使用信号量限制并发数
            semaphore = asyncio.Semaphore(max_concurrent)
            
            async def analyze_single_function(func_name: str):
                async with semaphore:
                    try:
                        # 检查缓存
                        if func_name in self.function_cache:
                            results["statistics"]["cached"] += 1
                            results["analyzed_functions"][func_name] = asdict(self.function_cache[func_name])
                            return
                        
                        # 智能分析
                        func_info = await self.smart_function_extract(func_name)
                        if func_info:
                            results["statistics"]["successful"] += 1
                            results["analyzed_functions"][func_name] = asdict(func_info)
                        else:
                            results["statistics"]["failed"] += 1
                            results["failed_functions"].append(func_name)
                            
                    except Exception as e:
                        logger.error(f"Batch analysis failed for {func_name}: {e}")
                        results["statistics"]["failed"] += 1
                        results["failed_functions"].append(func_name)
            
            # 并发执行分析
            tasks = [analyze_single_function(func_name) for func_name in func_names]
            await asyncio.gather(*tasks, return_exceptions=True)
            
            logger.info(f"Batch analysis complete: {results['statistics']}")
            return results
            
        except Exception as e:
            logger.error(f"Batch smart analysis failed: {e}")
            return {"error": str(e)}
    
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
    
    def extract_function_by_braces(self, content: str, start_line: int, func_name: str = None) -> Optional[str]:
        """基于智能大括号匹配提取完整函数代码"""
        try:
            lines = content.split('\n')
            
            if start_line >= len(lines):
                return None
            
            # 从函数声明开始向上找到完整声明（处理多行声明）
            func_start = start_line
            while func_start > 0:
                prev_line = lines[func_start-1].strip()
                # 如果上一行以分号结尾，说明是前一个函数或声明的结束
                if prev_line.endswith(';') or prev_line.endswith('}'):
                    break
                # 如果上一行包含左大括号，说明函数开始了
                if '{' in prev_line:
                    func_start -= 1
                    break
                # 继续向上查找函数声明的开始
                if prev_line and not prev_line.startswith('//') and not prev_line.startswith('/*'):
                    func_start -= 1
                else:
                    break
            
            # 向下匹配大括号找到函数结束
            brace_count = 0
            in_string = False
            in_char = False
            in_single_comment = False
            in_multi_comment = False
            func_end = start_line
            
            for i in range(func_start, len(lines)):
                line = lines[i]
                j = 0
                
                while j < len(line):
                    char = line[j]
                    
                    # 处理单行注释
                    if not in_string and not in_char and not in_multi_comment:
                        if j < len(line) - 1 and line[j:j+2] == '//':
                            in_single_comment = True
                            j += 2
                            continue
                    
                    # 处理多行注释开始
                    if not in_string and not in_char and not in_single_comment:
                        if j < len(line) - 1 and line[j:j+2] == '/*':
                            in_multi_comment = True
                            j += 2
                            continue
                    
                    # 处理多行注释结束
                    if in_multi_comment:
                        if j < len(line) - 1 and line[j:j+2] == '*/':
                            in_multi_comment = False
                            j += 2
                            continue
                    
                    # 跳过注释中的内容
                    if in_single_comment or in_multi_comment:
                        j += 1
                        continue
                    
                    # 处理字符串
                    if char == '"' and not in_char:
                        if j == 0 or line[j-1] != '\\':
                            in_string = not in_string
                    
                    # 处理字符常量
                    elif char == "'" and not in_string:
                        if j == 0 or line[j-1] != '\\':
                            in_char = not in_char
                    
                    # 处理大括号（只在非字符串、非字符常量、非注释中）
                    elif not in_string and not in_char:
                        if char == '{':
                            brace_count += 1
                        elif char == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                func_end = i
                                function_code = '\\n'.join(lines[func_start:func_end+1])
                                logger.debug(f"Extracted function {func_name or 'unknown'}: {len(function_code)} chars")
                                return function_code
                    
                    j += 1
                
                # 单行注释在行末结束
                if in_single_comment:
                    in_single_comment = False
            
            # 如果没有找到匹配的右大括号，返回从开始到文件末尾
            if brace_count > 0:
                function_code = '\\n'.join(lines[func_start:])
                logger.warning(f"Unmatched braces for function {func_name or 'unknown'}, returning partial code")
                return function_code
                
            return None
            
        except Exception as e:
            logger.error(f"Error extracting function by braces: {e}")
            return None
    
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
    
    async def _send_gdb_command_with_timeout(self, command: str, timeout: float = 10.0) -> str:
        """Send command to GDB with enhanced timeout and error handling"""
        try:
            if not self.gdb_process:
                await self._start_gdb()
                if not self.gdb_process:
                    return ""
            
            logger.debug(f"Sending GDB command: {command}")
            self.gdb_process.stdin.write(f"{command}\n".encode())
            await self.gdb_process.stdin.drain()
            
            # Read multiple lines of response until prompt
            response_lines = []
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                try:
                    line = await asyncio.wait_for(
                        self.gdb_process.stdout.readline(), timeout=1.0
                    )
                    line_str = line.decode().strip()
                    
                    # Stop reading when we see the GDB prompt
                    if line_str.startswith("(gdb)") or line_str == "":
                        break
                        
                    response_lines.append(line_str)
                    
                except asyncio.TimeoutError:
                    # Continue reading until timeout
                    continue
            
            return "\n".join(response_lines)
            
        except Exception as e:
            logger.error(f"Enhanced GDB command failed: {command} - {e}")
            return f"ERROR: {str(e)}"
    
    async def locate_function_with_gdb(self, func_name: str) -> Optional[Dict[str, Any]]:
        """使用 GDB 精确定位函数"""
        try:
            if not os.path.exists(self.libc_path):
                logger.warning(f"libc.so not found: {self.libc_path}")
                return None
            
            # Start GDB process if not already running
            if not self.gdb_process:
                if not await self._start_gdb():
                    return None
            
            # GDB commands to locate function precisely
            commands = [
                f"info address {func_name}",      # Get function address
                f"info line {func_name}",         # Get source location
                f"info symbol {func_name}",       # Get symbol info
                f"x/1i {func_name}",             # Show first instruction
                f"disassemble {func_name}",      # Get disassembly for boundaries
            ]
            
            results = {}
            for cmd in commands:
                result = await self._send_gdb_command_with_timeout(cmd, timeout=15.0)
                results[cmd] = result
                logger.debug(f"GDB {cmd}: {result[:100]}...")
            
            return self._parse_gdb_location_info(results, func_name)
            
        except Exception as e:
            logger.error(f"GDB location failed for {func_name}: {e}")
            return None
    
    def _parse_gdb_location_info(self, gdb_results: Dict[str, str], func_name: str) -> Optional[Dict[str, Any]]:
        """Parse GDB command results to extract function location info"""
        try:
            location_info = {
                "function_name": func_name,
                "address": None,
                "source_file": None,
                "line_number": None,
                "symbol_info": None,
                "disassembly": None
            }
            
            # Parse address info
            address_result = gdb_results.get(f"info address {func_name}", "")
            if "Symbol" in address_result and "is at" in address_result:
                # Extract address from "Symbol malloc is at 0x7ffff7e5b010 in section .text"
                parts = address_result.split()
                for i, part in enumerate(parts):
                    if part.startswith("0x"):
                        location_info["address"] = part
                        break
            
            # Parse line info
            line_result = gdb_results.get(f"info line {func_name}", "")
            if "Line" in line_result and "of" in line_result:
                # Extract from "Line 123 of \"/path/to/file.c\" starts at address 0x..."
                import re
                line_match = re.search(r'Line (\d+) of "([^"]+)"', line_result)
                if line_match:
                    location_info["line_number"] = int(line_match.group(1))
                    location_info["source_file"] = line_match.group(2)
            
            # Parse symbol info
            symbol_result = gdb_results.get(f"info symbol {func_name}", "")
            location_info["symbol_info"] = symbol_result
            
            # Parse disassembly for function boundaries
            disasm_result = gdb_results.get(f"disassemble {func_name}", "")
            location_info["disassembly"] = disasm_result
            
            # Only return if we have essential information
            if location_info["address"] or location_info["source_file"]:
                return location_info
            else:
                logger.warning(f"Insufficient location info for {func_name}")
                return None
                
        except Exception as e:
            logger.error(f"Error parsing GDB location info: {e}")
            return None
    
    async def _analyze_function_with_ai(self, func_name: str, func_code: str) -> Optional[Dict[str, Any]]:
        """使用 Claude 4 Sonnet 分析函数代码"""
        try:
            # 检查是否有 API 配置
            if not self.ai_config:
                logger.warning("No AI configuration found, using mock analysis")
                return self._get_mock_analysis(func_name, func_code)
            
            # 构建分析提示
            analysis_prompt = f"""请分析以下 C 函数代码，并以 JSON 格式返回结果：

函数名: {func_name}

代码:
```c
{func_code}
```

请提供详细分析，返回格式如下 JSON：
{{
    "function_signature": "完整的函数签名",
    "parameters": [
        {{"name": "参数名", "type": "类型", "description": "说明"}}, 
        ...
    ],
    "return_type": "返回值类型",
    "return_description": "返回值说明",
    "description": "函数主要功能描述",
    "error_handling": "错误处理方式说明", 
    "required_headers": ["需要的头文件列表"],
    "porting_notes": "QNX移植注意事项",
    "complexity": "复杂度评估(low/medium/high)",
    "thread_safety": "线程安全性说明"
}}

请务必返回有效的 JSON 格式。"""
            
            # 调用 Claude API
            ai_response = await self._call_claude_api(analysis_prompt)
            
            if ai_response:
                try:
                    # 尝试解析 JSON 响应
                    import re
                    # 提取 JSON 部分
                    json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
                    if json_match:
                        ai_analysis = json.loads(json_match.group())
                        ai_analysis["analysis_timestamp"] = time.time()
                        ai_analysis["code_length"] = len(func_code)
                        ai_analysis["ai_model"] = self.ai_config.get("model", "claude-sonnet-4")
                        
                        logger.info(f"Claude 4 analysis completed for {func_name}: {len(func_code)} chars analyzed")
                        return ai_analysis
                    else:
                        logger.warning(f"No JSON found in AI response for {func_name}")
                        return self._get_mock_analysis(func_name, func_code)
                        
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse AI JSON response for {func_name}: {e}")
                    return self._get_mock_analysis(func_name, func_code)
            else:
                logger.warning(f"No AI response for {func_name}, using mock analysis")
                return self._get_mock_analysis(func_name, func_code)
            
        except Exception as e:
            logger.error(f"AI analysis failed for {func_name}: {e}")
            return self._get_mock_analysis(func_name, func_code)
    
    def _get_mock_analysis(self, func_name: str, func_code: str) -> Dict[str, Any]:
        """获取模拟分析结果"""
        return {
            "function_signature": f"分析中的函数: {func_name}",
            "parameters": [],
            "return_type": "unknown", 
            "return_description": "需要分析",
            "description": f"函数 {func_name} 的功能描述（模拟）",
            "error_handling": "需要分析错误处理方式",
            "required_headers": ["stdio.h"],
            "porting_notes": "需要分析移植注意事项",
            "complexity": "medium",
            "thread_safety": "需要分析",
            "analysis_timestamp": time.time(),
            "code_length": len(func_code),
            "ai_model": "mock"
        }
    
    async def _call_claude_api(self, prompt: str) -> Optional[str]:
        """调用 Claude API"""
        try:
            import aiohttp
            import os
            
            # 获取 API 配置
            api_key = os.getenv(self.ai_config.get("api_key_env", "CLAUDE_API_KEY"))
            if not api_key:
                logger.warning("Claude API key not found")
                return None
            
            base_url = self.ai_config.get("base_url", "https://api.anthropic.com")
            model = self.ai_config.get("model", "claude-sonnet-4-20250514")
            max_tokens = self.ai_config.get("max_tokens", 8000)
            temperature = self.ai_config.get("temperature", 0.1)
            
            # 构建请求
            url = f"{base_url}/v1/messages"
            headers = {
                "Content-Type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01"
            }
            
            payload = {
                "model": model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }
            
            # 发送请求
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, json=payload, headers=headers) as response:
                    if response.status == 200:
                        result = await response.json()
                        content = result.get("content", [])
                        if content and len(content) > 0:
                            return content[0].get("text", "")
                    else:
                        logger.error(f"Claude API error: {response.status} - {await response.text()}")
                        return None
            
        except Exception as e:
            logger.error(f"Claude API call failed: {e}")
            return None
    
    async def _call_claude_api_for_code_generation(self, prompt: str) -> Optional[str]:
        """调用 Claude API 进行代码生成（使用专门的代码生成配置）"""
        try:
            import aiohttp
            import os
            
            # 获取代码生成专用 API 配置
            api_key = os.getenv(self.code_gen_ai_config.get("api_key_env", "CLAUDE_API_KEY"))
            if not api_key:
                logger.warning("Claude API key not found for code generation")
                return None
            
            base_url = self.code_gen_ai_config.get("base_url", "https://api.anthropic.com")
            model = self.code_gen_ai_config.get("model", "claude-sonnet-4-20250514")
            max_tokens = self.code_gen_ai_config.get("max_tokens", 8000)
            temperature = self.code_gen_ai_config.get("temperature", 0.1)
            
            # 构建请求
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01"
            }
            
            data = {
                "model": model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [{"role": "user", "content": prompt}]
            }
            
            timeout = aiohttp.ClientTimeout(total=30)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(f"{base_url}/v1/messages", 
                                       headers=headers, 
                                       json=data) as response:
                    
                    if response.status == 200:
                        result = await response.json()
                        if result.get("content") and len(result["content"]) > 0:
                            response_text = result["content"][0].get("text", "")
                            logger.info(f"Claude code generation API success - model: {model}")
                            return response_text
                        else:
                            logger.error("Empty response from Claude code generation API")
                            return None
                    else:
                        error_text = await response.text()
                        logger.error(f"Claude code generation API error {response.status}: {error_text}")
                        return None
            
        except Exception as e:
            logger.error(f"Claude code generation API call failed: {e}")
            return None
    
    async def smart_function_extract(self, func_name: str) -> Optional[LinuxFunctionInfo]:
        """智能函数提取 - 结合 GDB 定位和智能大括号匹配"""
        try:
            # Check cache first
            if func_name in self.function_cache:
                logger.debug(f"Function {func_name} found in cache")
                return self.function_cache[func_name]
            
            # 1. GDB 精确定位函数
            gdb_info = await self.locate_function_with_gdb(func_name)
            if not gdb_info:
                logger.warning(f"Function {func_name} not found via GDB")
                return None
            
            source_file = gdb_info.get('source_file')
            line_number = gdb_info.get('line_number')
            
            if not source_file or not line_number:
                logger.warning(f"Incomplete location info for {func_name}")
                return None
            
            # 2. 读取源文件并提取完整函数代码
            if not os.path.exists(source_file):
                logger.error(f"Source file not found: {source_file}")
                return None
            
            with open(source_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # 使用智能大括号匹配提取函数
            func_code = self.extract_function_by_braces(content, line_number - 1, func_name)
            if not func_code:
                logger.warning(f"Could not extract function code for {func_name}")
                return None
            
            # 3. 提取函数签名
            signature = self._extract_function_signature_from_code(func_code, func_name)
            
            # 4. AI 分析函数
            ai_analysis = await self._analyze_function_with_ai(func_name, func_code)
            
            # 5. 构建 LinuxFunctionInfo
            func_info = LinuxFunctionInfo(
                name=func_name,
                signature=signature,
                description=ai_analysis.get('description', f'Function {func_name} from {os.path.basename(source_file)}') if ai_analysis else f'Function {func_name}',
                parameters=[],  # TODO: Parse from AI analysis
                return_type=ai_analysis.get('return_type', 'unknown') if ai_analysis else 'unknown',
                return_description="",
                headers=ai_analysis.get('required_headers', []) if ai_analysis else [],
                source_file=source_file,
                source_location=f"{source_file}:{line_number}",
                source_code=func_code,
                library="musl",
                availability="musl",
                function_address=gdb_info.get('address'),
                gdb_analysis=gdb_info,
                ai_analysis=ai_analysis
            )
            
            # Cache the result
            self.function_cache[func_name] = func_info
            logger.info(f"Successfully extracted and analyzed function: {func_name}")
            
            return func_info
            
        except Exception as e:
            logger.error(f"Smart function extract failed for {func_name}: {e}")
            return None
    
    def _extract_function_signature_from_code(self, func_code: str, func_name: str) -> str:
        """从函数代码中提取函数签名"""
        try:
            lines = func_code.split('\n')
            
            # 找到包含函数名和左括号的行
            signature_lines = []
            found_func_name = False
            
            for line in lines:
                clean_line = line.strip()
                if not clean_line or clean_line.startswith('//') or clean_line.startswith('/*'):
                    continue
                
                if func_name in clean_line and '(' in clean_line:
                    found_func_name = True
                    signature_lines.append(clean_line)
                    
                    # 如果这行包含完整的函数声明（到 { 为止），直接返回
                    if '{' in clean_line:
                        signature = ' '.join(signature_lines)
                        return signature.split('{')[0].strip()
                        
                elif found_func_name:
                    signature_lines.append(clean_line)
                    if '{' in clean_line:
                        signature = ' '.join(signature_lines)
                        return signature.split('{')[0].strip()
            
            # 如果没找到完整签名，返回基本格式
            return f"unknown {func_name}(...)"
            
        except Exception as e:
            logger.error(f"Error extracting signature for {func_name}: {e}")
            return f"unknown {func_name}(...)"
    
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
        """Generate QNX glue code plan with AI enhancement"""
        
        # Check if function exists in Linux
        linux_func_info = self.function_db.get(qnx_func)
        escaped_funcs = self.get_existing_qnx_escape_functions()
        
        if not linux_func_info:
            # Strategy 1: Create stub in qnxsupport with AI enhancement
            glue_code = await self._generate_ai_enhanced_stub_code(qnx_func, qnx_info)
            if not glue_code:
                glue_code = self._generate_stub_code(qnx_func, qnx_info)
            
            return QNXGlueCodePlan(
                qnx_function=qnx_func,
                linux_function=None,
                strategy="create_stub",
                needs_dynlink_modification=False,
                qnx_support_file=f"{self.qnx_support_dir}/{qnx_func}.c",
                glue_code=glue_code,
                dynlink_addition=None,
                confidence=0.8 if glue_code != self._generate_stub_code(qnx_func, qnx_info) else 0.7
            )
        
        elif qnx_func in escaped_funcs:
            # Strategy 2: Function already escaped, create _qnx_ version with AI enhancement
            glue_code = await self._generate_ai_enhanced_wrapper_code(qnx_func, linux_func_info, qnx_info)
            if not glue_code:
                glue_code = self._generate_qnx_wrapper_code(qnx_func, linux_func_info, qnx_info)
            
            return QNXGlueCodePlan(
                qnx_function=qnx_func,
                linux_function=qnx_func,
                strategy="wrap_with_prefix",
                needs_dynlink_modification=False,
                qnx_support_file=f"{self.qnx_support_dir}/_qnx_{qnx_func}.c",
                glue_code=glue_code,
                dynlink_addition=None,
                confidence=0.95 if glue_code != self._generate_qnx_wrapper_code(qnx_func, linux_func_info, qnx_info) else 0.9
            )
        
        else:
            # Strategy 3: Need to add to ESCAPE_QNX_FUNC and create wrapper with AI enhancement
            glue_code = await self._generate_ai_enhanced_wrapper_code(qnx_func, linux_func_info, qnx_info)
            if not glue_code:
                glue_code = self._generate_qnx_wrapper_code(qnx_func, linux_func_info, qnx_info)
            
            return QNXGlueCodePlan(
                qnx_function=qnx_func,
                linux_function=qnx_func,
                strategy="wrap_with_prefix",
                needs_dynlink_modification=True,
                qnx_support_file=f"{self.qnx_support_dir}/_qnx_{qnx_func}.c",
                glue_code=glue_code,
                dynlink_addition=f"\tESCAPE_QNX_FUNC({qnx_func});",
                confidence=0.9 if glue_code != self._generate_qnx_wrapper_code(qnx_func, linux_func_info, qnx_info) else 0.8
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
    
    async def _generate_ai_enhanced_stub_code(self, func_name: str, qnx_info: Dict[str, Any]) -> Optional[str]:
        """使用 Claude 4 生成智能化的 QNX 存根代码"""
        try:
            signature = qnx_info.get('signature', f'int {func_name}(void)')
            description = qnx_info.get('description', f'QNX function {func_name}')
            
            prompt = f"""你是一个 QNX 到 Linux 移植专家。请为 QNX 函数 {func_name} 生成一个智能的存根实现。

函数信息：
- 函数名: {func_name}
- 函数签名: {signature}
- 描述: {description}

要求：
1. 分析函数的可能用途和预期行为
2. 提供一个合理的存根实现，而不是简单返回错误
3. 如果可能，尝试提供一些基本功能或合理的默认行为
4. 添加详细的注释说明
5. 处理可能的参数验证
6. 设置合适的错误码和返回值

请只返回 C 代码，不要包含任何解释文字。"""

            response = await self._call_claude_api_for_code_generation(prompt)
            if response:
                logger.info(f"AI enhanced stub code generated for {func_name}")
                return response.strip()
            
        except Exception as e:
            logger.error(f"AI enhanced stub code generation failed for {func_name}: {e}")
        
        return None
    
    async def _generate_ai_enhanced_wrapper_code(self, func_name: str, linux_info: LinuxFunctionInfo, qnx_info: Dict[str, Any]) -> Optional[str]:
        """使用 Claude 4 生成智能化的 QNX 包装器代码"""
        try:
            qnx_signature = qnx_info.get('signature', linux_info.signature)
            linux_signature = linux_info.signature
            linux_description = linux_info.description or "Linux implementation"
            qnx_description = qnx_info.get('description', f'QNX function {func_name}')
            
            prompt = f"""你是一个 QNX 到 Linux 移植专家。请为 QNX 函数 {func_name} 生成一个智能的包装器，将其映射到 Linux 实现。

函数信息：
- QNX 函数名: {func_name}
- QNX 函数签名: {qnx_signature}
- QNX 描述: {qnx_description}
- Linux 函数签名: {linux_signature}
- Linux 描述: {linux_description}

要求：
1. 分析 QNX 和 Linux 函数的差异
2. 实现参数转换和映射
3. 处理返回值转换
4. 实现错误码映射（QNX 到 Linux errno）
5. 添加参数验证
6. 添加详细注释说明差异和转换逻辑
7. 确保线程安全性（如果需要）
8. 包装器函数名应为 _qnx_{func_name}

请只返回 C 代码，不要包含任何解释文字。"""

            response = await self._call_claude_api_for_code_generation(prompt)
            if response:
                logger.info(f"AI enhanced wrapper code generated for {func_name}")
                return response.strip()
            
        except Exception as e:
            logger.error(f"AI enhanced wrapper code generation failed for {func_name}: {e}")
        
        return None

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
        async def batch_smart_analysis(func_names: str, max_concurrent: int = 3) -> List[types.TextContent]:
            """批量智能分析函数列表"""
            try:
                # 解析函数名列表 (逗号分隔或换行分隔)
                if isinstance(func_names, str):
                    func_list = [name.strip() for name in func_names.replace(',', '\n').split('\n') if name.strip()]
                else:
                    func_list = func_names
                
                if not func_list:
                    return [types.TextContent(
                        type="text",
                        text=json.dumps({"error": "没有提供函数名列表"}, indent=2)
                    )]
                
                # 执行批量分析
                results = await self.analyzer.batch_smart_analysis(func_list, max_concurrent)
                
                return [types.TextContent(
                    type="text",
                    text=json.dumps(results, indent=2)
                )]
                
            except Exception as e:
                logger.error(f"Batch smart analysis tool failed: {e}")
                return [types.TextContent(
                    type="text",
                    text=json.dumps({"error": str(e)}, indent=2)
                )]
        
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
        async def smart_function_lookup(func_name: str) -> List[types.TextContent]:
            """智能函数查询 - 结合GDB定位和AI分析"""
            try:
                # 使用智能提取方法
                func_info = await self.analyzer.smart_function_extract(func_name)
                if not func_info:
                    return [types.TextContent(
                        type="text",
                        text=json.dumps({
                            "error": f"函数 '{func_name}' 未找到或无法提取",
                            "suggestion": "请检查函数名是否正确，或函数是否存在于 libc.so 中"
                        }, indent=2)
                    )]
                
                # 返回完整的函数信息
                result = {
                    "function_name": func_info.name,
                    "signature": func_info.signature,
                    "source_location": func_info.source_location,
                    "function_address": func_info.function_address,
                    "source_code": func_info.source_code,
                    "description": func_info.description,
                    "return_type": func_info.return_type,
                    "headers": func_info.headers,
                    "library": func_info.library,
                    "gdb_analysis": func_info.gdb_analysis,
                    "ai_analysis": func_info.ai_analysis,
                    "extraction_method": "smart_gdb_braces"
                }
                
                return [types.TextContent(
                    type="text",
                    text=json.dumps(result, indent=2)
                )]
                
            except Exception as e:
                logger.error(f"Smart function lookup failed: {e}")
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
    import mcp.server.stdio
    
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