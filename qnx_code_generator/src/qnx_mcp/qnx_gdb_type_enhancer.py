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
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
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
            
            # Try to start QNX GDB with CLI interface for better output parsing
            try:
                self.gdb_process = subprocess.Popen(
                    [self.gdb_executable, "--quiet", "--batch-silent"],
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
                    [self.gdb_fallback, "--quiet", "--batch-silent"],
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
        """Send GDB command and get result using subprocess communication"""
        try:
            # Create a new GDB process for each command to avoid session issues
            env = self._setup_qnx_environment()
            
            # QNX libc library path for type information
            qnx_libc_path = f"{self.qnx_root}/target/qnx7/x86_64/lib/libc.so.4"
            
            # Use GDB in batch mode with QNX library loaded first, then the command
            gdb_cmd = [
                self.gdb_executable, "--quiet", "--batch", 
                "--ex", f"file {qnx_libc_path}",  # Load QNX libc for type information
                "--ex", command
            ]
            
            try:
                result = subprocess.run(
                    gdb_cmd,
                    capture_output=True,
                    text=True,
                    timeout=10,
                    env=env
                )
                
                if result.returncode == 0 and result.stdout:
                    response = result.stdout.strip()
                    logger.debug(f"GDB command '{command}' response: {response[:200]}...")
                    return response
                else:
                    # Fallback to system GDB if QNX GDB fails (also load QNX libc)
                    gdb_cmd_fallback = [
                        self.gdb_fallback, "--quiet", "--batch",
                        "--ex", f"file {qnx_libc_path}",  # Also load QNX libc in fallback
                        "--ex", command
                    ]
                    result_fallback = subprocess.run(
                        gdb_cmd_fallback,
                        capture_output=True,
                        text=True,
                        timeout=10,
                        env=env
                    )
                    
                    if result_fallback.returncode == 0 and result_fallback.stdout:
                        response = result_fallback.stdout.strip()
                        logger.debug(f"GDB fallback command '{command}' response: {response[:200]}...")
                        return response
                    
            except FileNotFoundError:
                logger.warning(f"GDB executable not found: {self.gdb_executable}")
                return ""
            except subprocess.TimeoutExpired:
                logger.warning(f"GDB command '{command}' timed out")
                return ""
                
            return ""
            
        except Exception as e:
            logger.error(f"Failed to send GDB command '{command}': {e}")
            return ""
    
    def get_type_info(self, type_name: str) -> Optional[TypeInfo]:
        """Get type information - simplified to just store raw ptype output"""
        try:
            # Just use ptype command and store the raw result
            command = f"ptype {type_name}"
            result = self._send_gdb_command(command)
            
            if result and result.strip():
                # Create simple TypeInfo with raw output
                type_info = TypeInfo(name=type_name)
                type_info.definition = result.strip()
                
                # Basic type classification based on keywords
                result_lower = result.lower()
                if 'struct' in result_lower:
                    type_info.is_struct = True
                elif 'union' in result_lower:
                    type_info.is_union = True
                elif 'enum' in result_lower:
                    type_info.is_enum = True
                    
                if '*' in result:
                    type_info.is_pointer = True
                if '[' in result and ']' in result:
                    type_info.is_array = True
                
                logger.debug(f"Got ptype result for {type_name}: {len(result)} chars")
                return type_info
            
            # If ptype fails, try whatis as simpler fallback
            result = self._send_gdb_command(f"whatis {type_name}")
            if result and result.strip():
                type_info = TypeInfo(name=type_name)
                type_info.definition = result.strip()
                logger.debug(f"Got whatis result for {type_name}: {len(result)} chars")
                return type_info
            
            return None
            
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
        """Extract struct fields with improved parsing"""
        fields = []
        lines = output.split('\n')
        
        in_struct = False
        brace_count = 0
        
        for line in lines:
            line = line.strip()
            
            # Start of struct/union definition
            if 'struct' in line or 'union' in line:
                if '{' in line:
                    in_struct = True
                    brace_count += line.count('{') - line.count('}')
                continue
            
            # Track braces
            if in_struct:
                brace_count += line.count('{') - line.count('}')
                
                # End of struct definition
                if brace_count <= 0:
                    break
                
                # Parse field definition
                if line and not line.startswith(('{', '}')) and ';' in line:
                    # Remove trailing semicolon and clean up
                    field_def = line.replace(';', '').strip()
                    
                    # Handle different field formats
                    # Example: "    time_t tv_sec;"
                    # Example: "    long int tv_nsec;"
                    # Example: "    unsigned int *ptr;"
                    
                    if field_def:
                        # Split and reconstruct type and name
                        parts = field_def.split()
                        if len(parts) >= 2:
                            # Last part is field name, rest is type
                            field_name = parts[-1].rstrip('*')  # Remove pointer symbols from name
                            field_type = ' '.join(parts[:-1])
                            
                            # Count pointer levels
                            pointer_count = parts[-1].count('*')
                            if pointer_count > 0:
                                field_type += ' ' + '*' * pointer_count
                            
                            fields.append({
                                "name": field_name,
                                "type": field_type,
                                "description": f"Struct field of type {field_type}"
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
            
            # Clean type name (remove struct/union prefix if present)
            clean_name = type_name.replace('struct ', '').replace('union ', '').replace('enum ', '')
            
            # More comprehensive type definition search patterns
            patterns = [
                # struct timespec { ... };
                rf'struct\s+{clean_name}\s*\{{([^{{}}]*(?:\{{[^{{}}]*\}}[^{{}}]*)*)\}}\s*;?',
                # union name { ... };
                rf'union\s+{clean_name}\s*\{{([^{{}}]*(?:\{{[^{{}}]*\}}[^{{}}]*)*)\}}\s*;?',
                # enum name { ... };
                rf'enum\s+{clean_name}\s*\{{([^{{}}]*)\}}\s*;?',
                # typedef struct { ... } name;
                rf'typedef\s+struct\s*\{{([^{{}}]*(?:\{{[^{{}}]*\}}[^{{}}]*)*)\}}\s*{clean_name}\s*;',
                # typedef ... name;
                rf'typedef\s+[^;]+\s+{clean_name}\s*;'
            ]
            
            for i, pattern in enumerate(patterns):
                match = re.search(pattern, content, re.DOTALL | re.MULTILINE)
                if match:
                    type_info = TypeInfo(name=type_name)
                    type_info.definition = match.group(0).strip()
                    
                    # Determine type classification
                    if i <= 1 or i == 3:  # struct patterns
                        type_info.is_struct = True
                        if len(match.groups()) > 0 and match.group(1):
                            # Extract fields from the content inside braces
                            fields_content = match.group(1).strip()
                            type_info.fields = self._parse_struct_fields_from_text(fields_content)
                    elif i == 1:  # union pattern
                        type_info.is_union = True
                        if len(match.groups()) > 0 and match.group(1):
                            fields_content = match.group(1).strip()
                            type_info.fields = self._parse_struct_fields_from_text(fields_content)
                    elif i == 2:  # enum pattern
                        type_info.is_enum = True
                        if len(match.groups()) > 0 and match.group(1):
                            enum_content = match.group(1).strip()
                            type_info.fields = self._parse_enum_values_from_text(enum_content)
                    
                    logger.debug(f"Found {type_name} definition in {file_path}")
                    return type_info
                    
        except Exception as e:
            logger.warning(f"Failed to read file {file_path}: {e}")
        
        return None
    
    def _parse_struct_fields_from_text(self, fields_text: str) -> List[Dict[str, str]]:
        """Parse struct fields from text content"""
        fields = []
        
        # Split by semicolons and process each field
        field_lines = [line.strip() for line in fields_text.split(';') if line.strip()]
        
        for line in field_lines:
            line = line.strip()
            if line and not line.startswith(('/', '*', '#')):  # Skip comments and preprocessor
                # Handle field like: "time_t tv_sec"
                parts = line.split()
                if len(parts) >= 2:
                    field_name = parts[-1].rstrip('*[]')  # Remove pointer/array symbols
                    field_type = ' '.join(parts[:-1])
                    
                    # Add back pointer/array symbols to type
                    if '*' in parts[-1]:
                        field_type += ' *'
                    if '[' in parts[-1]:
                        field_type += '[]'
                    
                    fields.append({
                        "name": field_name,
                        "type": field_type,
                        "description": f"Struct field of type {field_type}"
                    })
        
        return fields
    
    def _parse_enum_values_from_text(self, enum_text: str) -> List[Dict[str, str]]:
        """Parse enum values from text content"""
        values = []
        
        # Split by commas and process each value
        value_lines = [line.strip() for line in enum_text.split(',') if line.strip()]
        
        for line in value_lines:
            line = line.strip()
            if line and not line.startswith(('/', '*', '#')):
                # Handle enum value like: "VALUE_NAME = 123" or "VALUE_NAME"
                if '=' in line:
                    name, value = line.split('=', 1)
                    name = name.strip()
                    value = value.strip()
                else:
                    name = line.strip()
                    value = "auto"
                
                values.append({
                    "name": name,
                    "value": value,
                    "description": f"Enum value: {name} = {value}"
                })
        
        return values
    
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

    def enhance_header_file_paths(self, headers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Enhance header file information with complete paths"""
        enhanced_headers = []
        
        for header in headers:
            enhanced_header = header.copy()
            header_filename = header.get('filename', '')
            
            if header_filename:
                # Try to find complete path for the header file
                complete_path = self._find_complete_header_path(header_filename)
                if complete_path:
                    enhanced_header['path'] = complete_path
                    enhanced_header['is_system'] = self._is_system_header(complete_path)
                    logger.info(f"Enhanced header path: {header_filename} -> {complete_path}")
                else:
                    # Use default system path if not found
                    if not header.get('path'):
                        enhanced_header['path'] = f"/usr/include/{header_filename}"
                    logger.warning(f"Complete path not found for header: {header_filename}")
            
            enhanced_headers.append(enhanced_header)
        
        return enhanced_headers

    def _find_complete_header_path(self, header_filename: str) -> Optional[str]:
        """Find complete path for header file"""
        # Search in configured header paths
        for header_path in self.header_paths:
            if not os.path.exists(header_path):
                continue
            
            # Try direct path
            direct_path = os.path.join(header_path, header_filename)
            if os.path.exists(direct_path):
                return os.path.abspath(direct_path)
            
            # Try recursive search in subdirectories
            try:
                for root, dirs, files in os.walk(header_path):
                    if header_filename in files:
                        return os.path.abspath(os.path.join(root, header_filename))
            except Exception as e:
                logger.warning(f"Failed to search in {header_path}: {e}")
        
        return None

    def _is_system_header(self, header_path: str) -> bool:
        """Check if header is a system header"""
        system_paths = ['/usr/include', '/usr/local/include', self.qnx_root]
        return any(header_path.startswith(path) for path in system_paths)
    
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
        """Enhance function parameter information with GDB ptype results"""
        enhanced_params = []
        
        for param in parameters:
            enhanced_param = param.copy()
            param_type = param.get('type', '')
            
            if param_type:
                # Clean type name
                clean_type = self._clean_type_name(param_type)
                type_info = self.get_type_info(clean_type)
                
                if type_info:
                    # Add info field with GDB ptype results
                    enhanced_param['info'] = {
                        'ptype_result': type_info.definition,
                        'type_classification': {
                            'is_struct': type_info.is_struct,
                            'is_union': type_info.is_union,
                            'is_enum': type_info.is_enum,
                            'is_pointer': type_info.is_pointer,
                            'is_array': type_info.is_array
                        },
                        'fields': type_info.fields if type_info.fields else [],
                        'size': type_info.size if type_info.size > 0 else None
                    }
                    enhanced_param['enhanced'] = True
                    
                    logger.info(f"Enhanced parameter type info: {param_type} -> {clean_type}")
                else:
                    enhanced_param['info'] = {
                        'ptype_result': f"Type information not found for {param_type}",
                        'type_classification': {},
                        'fields': [],
                        'size': None
                    }
                    enhanced_param['enhanced'] = False
            else:
                enhanced_param['info'] = {
                    'ptype_result': "No type information available",
                    'type_classification': {},
                    'fields': [],
                    'size': None
                }
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


class MultiThreadGDBEnhancer:
    """Multi-threaded GDB enhancement processor"""
    
    def __init__(self, config_path: str = "config.json", max_workers: int = 4):
        """Initialize multi-threaded enhancer"""
        self.config_path = config_path
        self.max_workers = max_workers
        self.lock = Lock()
        self.processed_count = 0
        self.failed_count = 0
        self.start_time = None
        
        # Load configuration
        self.config = self._load_config(config_path)
        
        logger.info(f"Multi-threaded GDB enhancer initialized with {max_workers} workers")
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration file"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load config file: {e}")
            return {}
    
    def _create_worker_enhancer(self) -> QNXGDBTypeEnhancer:
        """Create a GDB enhancer instance for worker thread"""
        return QNXGDBTypeEnhancer(self.config_path)
    
    def _enhance_single_function(self, func_data: Dict[str, Any], func_name: str, 
                                enhancer: QNXGDBTypeEnhancer) -> Dict[str, Any]:
        """Enhance a single function with GDB type information"""
        try:
            enhanced_func = func_data.copy()
            
            # Enhance parameters if they exist
            if 'parameters' in enhanced_func and enhanced_func['parameters']:
                enhanced_params = enhancer.enhance_function_parameters(enhanced_func['parameters'])
                enhanced_func['parameters'] = enhanced_params
            
            with self.lock:
                self.processed_count += 1
                if self.processed_count % 10 == 0:
                    elapsed = time.time() - self.start_time if self.start_time else 0
                    rate = self.processed_count / elapsed if elapsed > 0 else 0
                    eta = (self.total_functions - self.processed_count) / rate if rate > 0 else 0
                    logger.info(f"Enhanced {self.processed_count}/{self.total_functions} functions "
                              f"({self.processed_count/self.total_functions*100:.1f}%) "
                              f"Rate: {rate:.1f} func/s ETA: {eta/60:.1f}m")
            
            return {func_name: enhanced_func}
            
        except Exception as e:
            with self.lock:
                self.failed_count += 1
                logger.error(f"Failed to enhance function {func_name}: {e}")
            
            return {func_name: func_data}  # Return original data if enhancement fails
    
    def enhance_functions_parallel(self, input_file: str, output_file: str, 
                                 max_functions: Optional[int] = None) -> Dict[str, Any]:
        """Enhance functions in parallel using multiple threads"""
        
        logger.info(f"Starting parallel GDB enhancement")
        logger.info(f"Input: {input_file}")
        logger.info(f"Output: {output_file}")
        logger.info(f"Max workers: {self.max_workers}")
        
        # Load input data
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                functions_data = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load input file {input_file}: {e}")
            return {}
        
        # Limit functions if specified
        if max_functions and max_functions > 0:
            function_items = list(functions_data.items())[:max_functions]
            functions_data = dict(function_items)
            logger.info(f"Limited to first {max_functions} functions")
        
        self.total_functions = len(functions_data)
        self.processed_count = 0
        self.failed_count = 0
        self.start_time = time.time()
        
        logger.info(f"Processing {self.total_functions} functions with {self.max_workers} threads")
        
        enhanced_functions = {}
        
        # Process functions in parallel
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_func = {}
            
            for func_name, func_data in functions_data.items():
                # Create a new enhancer for each task to avoid thread conflicts
                enhancer = self._create_worker_enhancer()
                future = executor.submit(self._enhance_single_function, func_data, func_name, enhancer)
                future_to_func[future] = func_name
            
            # Collect results
            for future in as_completed(future_to_func):
                func_name = future_to_func[future]
                try:
                    result = future.result()
                    enhanced_functions.update(result)
                    
                    # Periodically save progress
                    if len(enhanced_functions) % 50 == 0:
                        self._save_progress(enhanced_functions, output_file)
                        
                except Exception as e:
                    logger.error(f"Exception processing function {func_name}: {e}")
                    # Add original function data if processing failed
                    enhanced_functions[func_name] = functions_data[func_name]
        
        # Final save
        self._save_progress(enhanced_functions, output_file)
        
        # Summary
        elapsed_time = time.time() - self.start_time
        success_count = self.processed_count - self.failed_count
        
        logger.info("=" * 60)
        logger.info("GDB Enhancement Complete!")
        logger.info(f"Total functions: {self.total_functions}")
        logger.info(f"Successfully enhanced: {success_count}")
        logger.info(f"Failed: {self.failed_count}")
        logger.info(f"Success rate: {success_count/self.total_functions*100:.1f}%")
        logger.info(f"Processing time: {elapsed_time:.1f}s")
        logger.info(f"Average rate: {self.total_functions/elapsed_time:.1f} functions/second")
        logger.info(f"Output saved to: {output_file}")
        logger.info("=" * 60)
        
        return enhanced_functions
    
    def _save_progress(self, enhanced_functions: Dict[str, Any], output_file: str):
        """Save current progress to file"""
        try:
            # Define serialize function locally to avoid circular imports
            def serialize_function_info(obj):
                """Custom JSON serialization function"""
                from dataclasses import asdict
                # Handle dataclass objects
                if hasattr(obj, '__dataclass_fields__'):
                    return asdict(obj)
                # Handle objects with __dict__ attribute
                elif hasattr(obj, '__dict__'):
                    return {k: serialize_function_info(v) for k, v in obj.__dict__.items()}
                # Handle namedtuple
                elif hasattr(obj, '_asdict'):
                    return obj._asdict()
                # Handle lists and tuples
                elif isinstance(obj, (list, tuple)):
                    return [serialize_function_info(item) for item in obj]
                # Handle dictionaries
                elif isinstance(obj, dict):
                    return {key: serialize_function_info(value) for key, value in obj.items()}
                # Other basic types
                else:
                    return obj
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(enhanced_functions, f, indent=2, default=serialize_function_info, ensure_ascii=False)
            
            logger.debug(f"Progress saved: {len(enhanced_functions)} functions")
            
        except Exception as e:
            logger.error(f"Failed to save progress: {e}")


def main():
    """Main function for command line usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description='QNX GDB Type Enhancement - Single/Multi-threaded')
    parser.add_argument('--input', '-i', help='Input JSON file with extracted functions')
    parser.add_argument('--output', '-o', help='Output JSON file for enhanced functions')
    parser.add_argument('--workers', '-w', type=int, default=4, help='Number of worker threads (default: 4)')
    parser.add_argument('--max-functions', '-m', type=int, help='Maximum number of functions to process')
    parser.add_argument('--config', '-c', default='config.json', help='Configuration file path')
    parser.add_argument('--test', action='store_true', help='Run type information test')
    
    args = parser.parse_args()
    
    if args.test:
        # Test mode
        enhancer = QNXGDBTypeEnhancer(args.config)
        
        # Test type information retrieval
        test_types = ["size_t", "struct sockaddr", "FILE", "mqd_t", "acl_t"]
        
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
        return 0
    
    if not args.input or not args.output:
        logger.error("Input and output files are required for enhancement mode")
        return 1
    
    # Validate input file
    if not os.path.exists(args.input):
        logger.error(f"Input file not found: {args.input}")
        return 1
    
    # Multi-threaded enhancement
    enhancer = MultiThreadGDBEnhancer(
        config_path=args.config,
        max_workers=args.workers
    )
    
    # Process functions
    try:
        enhanced_functions = enhancer.enhance_functions_parallel(
            input_file=args.input,
            output_file=args.output,
            max_functions=args.max_functions
        )
        
        logger.info(f"Enhancement completed successfully!")
        return 0
        
    except Exception as e:
        logger.error(f"Enhancement failed: {e}")
        return 1


if __name__ == "__main__":
    exit(main())