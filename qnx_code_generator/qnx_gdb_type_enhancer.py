#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QNX GDB Type Information Enhancer
Obtain accurate type information through QNX's ntox86_64-gdb to enhance JSON extraction accuracy
"""

import os
import sys
import json
import subprocess
import tempfile
import logging
import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class TypeInfo:
    """Type information"""
    name: str = ""
    definition: str = ""
    size: int = 0
    is_struct: bool = False
    is_union: bool = False
    is_enum: bool = False
    is_pointer: bool = False
    is_array: bool = False
    fields: List[Dict[str, str]] = None
    
    def __post_init__(self):
        if self.fields is None:
            self.fields = []

@dataclass
class HeaderFileInfo:
    """Header file information"""
    path: str = ""
    content_preview: str = ""
    relevant_definitions: List[str] = None
    
    def __post_init__(self):
        if self.relevant_definitions is None:
            self.relevant_definitions = []

class QNXGDBTypeEnhancer:
    """QNX GDB Type Information Enhancer"""
    
    def __init__(self, config_path: str = "config.json"):
        """Initialize enhancer"""
        self.config = self._load_config(config_path)
        
        # QNX system configuration
        qnx_config = self.config.get("qnx_system", {})
        self.qnx_root = qnx_config.get("root_path", "/home/a2ure/Desktop/qnx700")
        self.env_script = qnx_config.get("env_setup_script", f"{self.qnx_root}/qnxsdp-env.sh")
        self.gdb_executable = qnx_config.get("gdb_executable", "ntox86_64-gdb")
        self.gdb_fallback = qnx_config.get("gdb_fallback", "gdb")
        self.header_paths = qnx_config.get("header_search_paths", [])
        self.symbol_paths = qnx_config.get("symbol_library_paths", [])
        self.preferred_arch = qnx_config.get("preferred_architecture", "x86_64")
        
        # Debug settings
        debug_config = self.config.get("debug_settings", {})
        self.enable_gdb_analysis = debug_config.get("enable_gdb_analysis", True)
        self.max_function_declarations = debug_config.get("max_function_declarations", 20)
        self.header_preview_size = debug_config.get("header_content_preview_size", 2000)
        
        # GDB session
        self.gdb_process = None
        self.gdb_initialized = False
        
        logger.info(f"QNX GDB enhancer initialized")
        logger.info(f"QNX root path: {self.qnx_root}")
        logger.info(f"GDB executable: {self.gdb_executable}")
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration file"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load configuration file: {e}")
            return {}
    
    def _setup_qnx_environment(self) -> Dict[str, str]:
        """Set QNX environment variables"""
        env = os.environ.copy()
        
        if os.path.exists(self.env_script):
            try:
                # Execute QNX environment setup script and get environment variables
                cmd = f"source {self.env_script} && env"
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, executable='/bin/bash')
                
                if result.returncode == 0:
                    for line in result.stdout.split('\n'):
                        if '=' in line:
                            key, value = line.split('=', 1)
                            env[key] = value
                    logger.info("QNX environment setup succeeded")
                else:
                    logger.warning(f"QNX environment setup failed: {result.stderr}")
            except Exception as e:
                logger.warning(f"Failed to execute QNX environment script: {e}")
        else:
            logger.warning(f"QNX environment script does not exist: {self.env_script}")
        
        return env
    
    def _start_gdb_session(self) -> bool:
        """Start GDB session"""
        if not self.enable_gdb_analysis:
            logger.info("GDB analysis is disabled")
            return False
        
        try:
            env = self._setup_qnx_environment()
            
            # Try to start QNX GDB
            try:
                self.gdb_process = subprocess.Popen(
                    [self.gdb_executable, "--interpreter=mi", "--quiet"],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    env=env
                )
                logger.info(f"Successfully started {self.gdb_executable}")
            except FileNotFoundError:
                logger.warning(f"{self.gdb_executable} not found, trying {self.gdb_fallback}")
                self.gdb_process = subprocess.Popen(
                    [self.gdb_fallback, "--interpreter=mi", "--quiet"],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    env=env
                )
                logger.info(f"Successfully started {self.gdb_fallback}")
            
            # Initialize GDB settings
            self._send_gdb_command("set confirm off")
            self._send_gdb_command("set pagination off")
            
            # Set symbol file paths
            for path in self.symbol_paths:
                if os.path.exists(path):
                    self._send_gdb_command(f"set solib-search-path {path}")
            
            self.gdb_initialized = True
            logger.info("GDB session initialized")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start GDB session: {e}")
            return False
    
    def _send_gdb_command(self, command: str) -> str:
        """Send GDB command and get result"""
        if not self.gdb_process or not self.gdb_initialized:
            return ""
        
        try:
            self.gdb_process.stdin.write(command + "\n")
            self.gdb_process.stdin.flush()
            
            # Read response (simplified version, should actually parse MI format)
            response = ""
            # More complex MI parsing needed here, simplified for now
            return response
        except Exception as e:
            logger.error(f"Failed to send GDB command: {e}")
            return ""
    
    def get_type_info(self, type_name: str) -> Optional[TypeInfo]:
        """Get type information"""
        if not self.gdb_initialized:
            if not self._start_gdb_session():
                return None
        
        try:
            # Use ptype command to get type information
            command = f"ptype {type_name}"
            result = self._send_gdb_command(command)
            
            if result:
                return self._parse_ptype_output(result, type_name)
            else:
                # If GDB fails, try to search in header files
                return self._search_type_in_headers(type_name)
        except Exception as e:
            logger.error(f"Failed to get type information {type_name}: {e}")
            return None
    
    def _parse_ptype_output(self, output: str, type_name: str) -> TypeInfo:
        """Parse ptype output"""
        type_info = TypeInfo(name=type_name)
        
        # Parse struct/union/enum
        if "struct" in output:
            type_info.is_struct = True
            type_info.fields = self._extract_struct_fields(output)
        elif "union" in output:
            type_info.is_union = True
            type_info.fields = self._extract_struct_fields(output)
        elif "enum" in output:
            type_info.is_enum = True
            type_info.fields = self._extract_enum_values(output)
        
        # Detect pointer and array
        if "*" in output:
            type_info.is_pointer = True
        if "[" in output and "]" in output:
            type_info.is_array = True
        
        type_info.definition = output.strip()
        return type_info
    
    def _extract_struct_fields(self, output: str) -> List[Dict[str, str]]:
        """Extract struct fields"""
        fields = []
        # Simplified field extraction logic
        lines = output.split('\n')
        for line in lines:
            line = line.strip()
            if line and not line.startswith(('struct', 'union', '}', '{')):
                # Parse field definition
                if ';' in line:
                    field_def = line.replace(';', '').strip()
                    parts = field_def.split()
                    if len(parts) >= 2:
                        field_type = ' '.join(parts[:-1])
                        field_name = parts[-1]
                        fields.append({
                            "name": field_name,
                            "type": field_type,
                            "description": f"Field of type {field_type}"
                        })
        return fields
    
    def _extract_enum_values(self, output: str) -> List[Dict[str, str]]:
        """Extract enum values"""
        values = []
        # Simplified enum value extraction logic
        lines = output.split('\n')
        for line in lines:
            line = line.strip()
            if line and '=' in line:
                parts = line.split('=')
                if len(parts) == 2:
                    name = parts[0].strip().rstrip(',')
                    value = parts[1].strip().rstrip(',')
                    values.append({
                        "name": name,
                        "value": value,
                        "description": f"Enum value: {name} = {value}"
                    })
        return values
    
    def _search_type_in_headers(self, type_name: str) -> Optional[TypeInfo]:
        """Search for type definition in header files"""
        for header_path in self.header_paths:
            if not os.path.exists(header_path):
                continue
            
            try:
                # Search for type definition
                for root, dirs, files in os.walk(header_path):
                    for file in files:
                        if file.endswith(('.h', '.hpp')):
                            file_path = os.path.join(root, file)
                            type_info = self._search_type_in_file(file_path, type_name)
                            if type_info:
                                return type_info
            except Exception as e:
                logger.warning(f"Failed to search header files {header_path}: {e}")
        
        return None
    
    def _search_type_in_file(self, file_path: str, type_name: str) -> Optional[TypeInfo]:
        """Search for type definition in a single file"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Simple type definition search
            patterns = [
                rf'typedef\s+.*\s+{type_name}\s*;',
                rf'struct\s+{type_name}\s*\{{.*?\}}',
                rf'union\s+{type_name}\s*\{{.*?\}}',
                rf'enum\s+{type_name}\s*\{{.*?\}}'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, content, re.DOTALL)
                if match:
                    type_info = TypeInfo(name=type_name)
                    type_info.definition = match.group(0)
                    
                    if 'struct' in pattern:
                        type_info.is_struct = True
                    elif 'union' in pattern:
                        type_info.is_union = True
                    elif 'enum' in pattern:
                        type_info.is_enum = True
                    
                    return type_info
        except Exception as e:
            logger.warning(f"Failed to read file {file_path}: {e}")
        
        return None
    
    def get_header_file_info(self, header_name: str) -> Optional[HeaderFileInfo]:
        """Get header file information"""
        for header_path in self.header_paths:
            file_path = os.path.join(header_path, header_name)
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    
                    header_info = HeaderFileInfo(path=file_path)
                    header_info.content_preview = content[:self.header_preview_size]
                    
                    # Extract relevant definitions
                    header_info.relevant_definitions = self._extract_definitions(content)
                    
                    return header_info
                except Exception as e:
                    logger.warning(f"Failed to read header file {file_path}: {e}")
        
        return None
    
    def _extract_definitions(self, content: str) -> List[str]:
        """Extract definitions from header file content"""
        definitions = []
        
        # Extract function declarations
        func_pattern = r'^\s*(?:extern\s+)?[\w\s\*]+\s+\w+\s*\([^)]*\)\s*;'
        for match in re.finditer(func_pattern, content, re.MULTILINE):
            definitions.append(match.group(0).strip())
        
        # Extract typedefs
        typedef_pattern = r'typedef\s+[^;]+;'
        for match in re.finditer(typedef_pattern, content):
            definitions.append(match.group(0).strip())
        
        # Extract macro definitions
        define_pattern = r'#define\s+\w+.*'
        for match in re.finditer(define_pattern, content):
            definitions.append(match.group(0).strip())
        
        return definitions[:self.max_function_declarations]
    
    def enhance_function_parameters(self, parameters: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Enhance function parameter information"""
        enhanced_params = []
        
        for param in parameters:
            enhanced_param = param.copy()
            param_type = param.get('type', '')
            
            if param_type:
                # Clean type name
                clean_type = self._clean_type_name(param_type)
                type_info = self.get_type_info(clean_type)
                
                if type_info:
                    enhanced_param['type_definition'] = type_info.definition
                    enhanced_param['type_fields'] = type_info.fields
                    enhanced_param['is_struct'] = type_info.is_struct
                    enhanced_param['is_union'] = type_info.is_union
                    enhanced_param['is_enum'] = type_info.is_enum
                    enhanced_param['enhanced'] = True
                    
                    logger.info(f"Enhanced parameter type info: {param_type} -> {clean_type}")
                else:
                    enhanced_param['enhanced'] = False
            
            enhanced_params.append(enhanced_param)
        
        return enhanced_params
    
    def _clean_type_name(self, type_name: str) -> str:
        """Clean type name, remove modifiers"""
        # Remove const, volatile, static, etc.
        type_name = re.sub(r'\b(const|volatile|static|extern|inline)\b', '', type_name)
        # Remove pointer and reference symbols
        type_name = re.sub(r'[\*&]+', '', type_name)
        # Remove extra spaces
        type_name = ' '.join(type_name.split())
        return type_name.strip()
    
    def close(self):
        """Close GDB session"""
        if self.gdb_process:
            try:
                self.gdb_process.terminate()
                self.gdb_process.wait(timeout=5)
            except:
                self.gdb_process.kill()
            finally:
                self.gdb_process = None
                self.gdb_initialized = False
                logger.info("GDB session closed")
    
    def __del__(self):
        """Destructor"""
        self.close()


if __name__ == "__main__":
    # Test code
    enhancer = QNXGDBTypeEnhancer()
    
    # Test type information retrieval
    test_types = ["size_t", "struct sockaddr", "FILE"]
    
    for type_name in test_types:
        print(f"\n=== Test type: {type_name} ===")
        type_info = enhancer.get_type_info(type_name)
        if type_info:
            print(f"Type definition: {type_info.definition}")
            if type_info.fields:
                print(f"Number of fields: {len(type_info.fields)}")
        else:
            print("Type information not found")
    
    enhancer.close()