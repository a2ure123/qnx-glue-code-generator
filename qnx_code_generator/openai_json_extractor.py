#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Efficient JSON data extractor based on OpenAI
Specialized for extracting QNX function information from HTML documents and outputting standard JSON format
"""

import os
import sys
import json
import time
import logging
import re
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from pathlib import Path
from openai import OpenAI
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from qnx_gdb_type_enhancer import QNXGDBTypeEnhancer

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

@dataclass
class FunctionParameter:
    """Function parameter information"""
    name: str = ""
    type: str = ""
    description: str = ""
    is_pointer: bool = False
    is_const: bool = False
    is_optional: bool = False

@dataclass
class HeaderFile:
    """Header file information"""
    filename: str = ""
    path: str = ""
    is_system: bool = True

@dataclass
class QNXFunctionInfo:
    """QNX function complete information"""
    name: str = ""
    synopsis: str = ""
    description: str = ""
    parameters: List[FunctionParameter] = None
    return_type: str = ""
    return_description: str = ""
    headers: List[HeaderFile] = None
    libraries: List[str] = None
    examples: List[str] = None
    see_also: List[str] = None
    classification: str = ""
    safety: str = ""
    
    def __post_init__(self):
        if self.parameters is None:
            self.parameters = []
        if self.headers is None:
            self.headers = []
        if self.libraries is None:
            self.libraries = []
        if self.examples is None:
            self.examples = []
        if self.see_also is None:
            self.see_also = []


class OpenAIJSONExtractor:
    """OpenAI-based JSON extractor (Enhanced, supports QNX GDB type analysis)"""
    
    def __init__(self, config_path: str = "config.json"):
        """Initialize JSON extractor"""
        # Load configuration
        self.config = self._load_config(config_path)
        
        # AI configuration
        ai_config = self.config.get("ai_settings", {})
        openai_config = ai_config.get("openai", {})
        
        # OpenAI configuration
        self.api_key_env = openai_config.get("api_key_env", "OPENAI_API_KEY")
        self.model = openai_config.get("chat_model", "gpt-4o-mini")
        self.max_tokens = openai_config.get("max_tokens", 4000)
        self.temperature = openai_config.get("temperature", 0.1)
        
        # Initialize OpenAI client
        self.openai_client = None
        self._initialize_openai()
        
        # Initialize QNX GDB type enhancer
        try:
            self.gdb_enhancer = QNXGDBTypeEnhancer(config_path)
            self.gdb_enhancement_enabled = True
            logger.info("QNX GDB type enhancer initialized successfully")
        except Exception as e:
            logger.warning(f"QNX GDB type enhancer initialization failed: {e}")
            self.gdb_enhancer = None
            self.gdb_enhancement_enabled = False
        
        # JSON extraction prompt template
        self.extraction_prompt = self._create_extraction_prompt()
        
        logger.info(f"OpenAI JSON extractor initialization completed")
        logger.info(f"Model: {self.model}")
        logger.info(f"GDB enhancement: {'Enabled' if self.gdb_enhancement_enabled else 'Disabled'}")
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration file"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load config file: {e}")
            return {}
    
    def _initialize_openai(self):
        """Initialize OpenAI client"""
        api_key = os.getenv(self.api_key_env)
        if not api_key:
            raise ValueError(f"Please set environment variable {self.api_key_env}")
        
        # Check proxy configuration
        import httpx
        proxy_config = self.config.get("network_settings", {}).get("proxy", {})
        client_kwargs = {"api_key": api_key}
        
        if proxy_config.get("enabled", False):
            https_proxy = proxy_config.get("https_proxy")
            if https_proxy:
                logger.info(f"OpenAI JSON extractor using proxy: {https_proxy}")
                client_kwargs["http_client"] = httpx.Client(proxy=https_proxy)
        
        self.openai_client = OpenAI(**client_kwargs)
        logger.info("OpenAI client initialized successfully")
    
    def _create_extraction_prompt(self) -> str:
        """Create JSON extraction prompt template"""
        return """
You are a professional QNX function documentation JSON extractor. Please extract function information from the following HTML document and return it in standard JSON format.

Please output according to the following JSON schema:

{
  "name": "Function name",
  "synopsis": "Function declaration/prototype",
  "description": "Function description",
  "parameters": [
    {
      "name": "Parameter name",
      "type": "Parameter type",
      "description": "Parameter description",
      "is_pointer": false,
      "is_const": false,
      "is_optional": false
    }
  ],
  "return_type": "Return type",
  "return_description": "Return value description",
  "headers": [
    {
      "filename": "Header filename",
      "path": "Full path",
      "is_system": true
    }
  ],
  "libraries": ["Library list"],
  "examples": ["Code examples"],
  "see_also": ["Related functions"],
  "classification": "Function classification",
  "safety": "Thread safety"
}

Extraction rules:
1. Identify key information such as function name, prototype, description from HTML
2. Parameter list should include type, name, description
3. Extract header files from #include directives
4. Extract return value info from Returns section
5. Extract code examples from Example section
6. Extract related functions from See also section
7. If some fields are not found, set them to empty value or empty list

Please only return JSON, do not add any other explanation.
"""
    
    def clean_html_content(self, html_content: str) -> str:
        """Clean HTML content and extract main text"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove script and style tags
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Get main content area
            main_content = soup.find('div', class_='content') or soup.find('main') or soup.body or soup
            
            if main_content:
                # Keep structured information
                text_content = main_content.get_text(separator='\n', strip=True)
                
                # Clean extra blank lines
                lines = [line.strip() for line in text_content.split('\n') if line.strip()]
                cleaned_text = '\n'.join(lines)
                
                # Limit length to avoid token overflow
                if len(cleaned_text) > 6000:
                    cleaned_text = cleaned_text[:6000] + "\n... (content truncated)"
                
                return cleaned_text
            else:
                return html_content[:6000]
                
        except Exception as e:
            logger.warning(f"HTML cleaning failed: {e}")
            return html_content[:6000]
    
    def extract_function_info(self, html_content: str, function_name: str = "") -> Optional[QNXFunctionInfo]:
        """Extract function information from HTML content"""
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                # Clean HTML content
                cleaned_content = self.clean_html_content(html_content)
                
                # Build full prompt
                full_prompt = self.extraction_prompt + "\n\n" + cleaned_content
                
                if function_name:
                    full_prompt += f"\n\nPlease focus on function: {function_name}"
                
                # Call OpenAI for extraction
                logger.info(f"Start extracting function info: {function_name or 'Not specified'} (Attempt {attempt + 1}/{max_retries})")
                
                response = self.openai_client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are a professional QNX function documentation JSON extractor."},
                        {"role": "user", "content": full_prompt}
                    ],
                    max_tokens=self.max_tokens,
                    temperature=self.temperature
                )
                
                if response.choices and response.choices[0].message:
                    content = response.choices[0].message.content.strip()
                    
                    # Clean possible markdown format
                    if content.startswith("```json"):
                        content = content[7:]
                    if content.endswith("```"):
                        content = content[:-3]
                    content = content.strip()
                    
                    # Parse JSON response
                    json_data = json.loads(content)
                    
                    # Convert to QNXFunctionInfo object
                    function_info = self._json_to_function_info(json_data)
                    
                    # GDB type enhancement
                    if self.gdb_enhancement_enabled and function_info:
                        function_info = self._enhance_with_gdb_info(function_info)
                    
                    logger.info(f"Function info extracted successfully: {function_info.name}")
                    return function_info
                else:
                    logger.warning(f"OpenAI response is empty (Attempt {attempt + 1}/{max_retries})")
                    if attempt < max_retries - 1:
                        time.sleep(1)
                        continue
                    else:
                        logger.error("Failed to get valid response after multiple attempts")
                        return None
                    
            except json.JSONDecodeError as e:
                logger.error(f"JSON parsing failed: {e}")
                if 'content' in locals():
                    logger.error(f"Raw response: {content[:500]}...")
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
                return None
            except Exception as e:
                logger.error(f"Function info extraction failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
                return None
        
        return None
    
    def _json_to_function_info(self, json_data: Dict[str, Any]) -> QNXFunctionInfo:
        """Convert JSON data to QNXFunctionInfo object"""
        # Convert parameter list
        parameters = []
        for param_data in json_data.get("parameters", []):
            param = FunctionParameter(
                name=param_data.get("name", ""),
                type=param_data.get("type", ""),
                description=param_data.get("description", ""),
                is_pointer=param_data.get("is_pointer", False),
                is_const=param_data.get("is_const", False),
                is_optional=param_data.get("is_optional", False)
            )
            parameters.append(param)
        
        # Convert header file list
        headers = []
        for header_data in json_data.get("headers", []):
            header = HeaderFile(
                filename=header_data.get("filename", ""),
                path=header_data.get("path", ""),
                is_system=header_data.get("is_system", True)
            )
            headers.append(header)
        
        # Create QNXFunctionInfo object
        function_info = QNXFunctionInfo(
            name=json_data.get("name", ""),
            synopsis=json_data.get("synopsis", ""),
            description=json_data.get("description", ""),
            parameters=parameters,
            return_type=json_data.get("return_type", ""),
            return_description=json_data.get("return_description", ""),
            headers=headers,
            libraries=json_data.get("libraries", []),
            examples=json_data.get("examples", []),
            see_also=json_data.get("see_also", []),
            classification=json_data.get("classification", ""),
            safety=json_data.get("safety", "")
        )
        
        return function_info
    
    def _enhance_with_gdb_info(self, function_info: QNXFunctionInfo) -> QNXFunctionInfo:
        """Enhance function info with GDB type information"""
        if not self.gdb_enhancer:
            return function_info
        
        try:
            logger.info(f"Start GDB enhancement: {function_info.name}")
            
            # Enhance parameter type information
            if function_info.parameters:
                enhanced_params = []
                for param in function_info.parameters:
                    enhanced_param = param
                    param_type = param.type
                    
                    if param_type:
                        # Get detailed type information
                        type_info = self.gdb_enhancer.get_type_info(param_type)
                        if type_info:
                            # Add enhancement info to parameter description
                            if type_info.definition:
                                enhanced_description = param.description + f"\nType definition: {type_info.definition}"
                                enhanced_param = FunctionParameter(
                                    name=param.name,
                                    type=param.type,
                                    description=enhanced_description,
                                    is_pointer=type_info.is_pointer or param.is_pointer,
                                    is_const=param.is_const,
                                    is_optional=param.is_optional
                                )
                                logger.info(f"Enhanced parameter type: {param.name} ({param_type})")
                    
                    enhanced_params.append(enhanced_param)
                
                function_info.parameters = enhanced_params
            
            # Enhance header file information
            if function_info.headers:
                enhanced_headers = []
                for header in function_info.headers:
                    enhanced_header = header
                    
                    # Get detailed header file information
                    header_info = self.gdb_enhancer.get_header_file_info(header.filename)
                    if header_info and header_info.relevant_definitions:
                        # Add relevant definitions to function's see_also or examples
                        if not function_info.examples:
                            function_info.examples = []
                        
                        # Add relevant definitions from header file
                        for definition in header_info.relevant_definitions[:3]:  # Limit number
                            if function_info.name.lower() in definition.lower():
                                function_info.examples.append(f"// From {header.filename}:\n{definition}")
                        
                        logger.info(f"Enhanced header file info: {header.filename}")
                    
                    enhanced_headers.append(enhanced_header)
                
                function_info.headers = enhanced_headers
            
            # Enhance return type information
            if function_info.return_type:
                return_type_info = self.gdb_enhancer.get_type_info(function_info.return_type)
                if return_type_info and return_type_info.definition:
                    enhanced_return_desc = function_info.return_description
                    if enhanced_return_desc:
                        enhanced_return_desc += f"\nReturn type definition: {return_type_info.definition}"
                    else:
                        enhanced_return_desc = f"Return type definition: {return_type_info.definition}"
                    function_info.return_description = enhanced_return_desc
                    logger.info(f"Enhanced return type: {function_info.return_type}")
            
            logger.info(f"GDB enhancement completed: {function_info.name}")
            
        except Exception as e:
            logger.warning(f"GDB enhancement failed {function_info.name}: {e}")
        
        return function_info
    
    def close(self):
        """Close resources"""
        if hasattr(self, 'gdb_enhancer') and self.gdb_enhancer:
            self.gdb_enhancer.close()
    
    def __del__(self):
        """Destructor"""
        try:
            self.close()
        except:
            pass  # Ignore errors in destructor


def serialize_function_info(obj):
    """Serialize function info object"""
    if hasattr(obj, '__dataclass_fields__'):
        return asdict(obj)
    elif hasattr(obj, '__dict__'):
        return {k: serialize_function_info(v) for k, v in obj.__dict__.items()}
    elif isinstance(obj, list):
        return [serialize_function_info(item) for item in obj]
    elif isinstance(obj, dict):
        return {k: serialize_function_info(v) for k, v in obj.items()}
    else:
        return obj


if __name__ == "__main__":
    # Test code
    extractor = OpenAIJSONExtractor()
    
    test_html = """
    <html>
    <body>
    <h1>malloc()</h1>
    <p>The malloc() function allocates memory.</p>
    <code>void* malloc(size_t size);</code>
    </body>
    </html>
    """
    
    result = extractor.extract_function_info(test_html, "malloc")
    if result:
        print("Extraction succeeded:")
        print(json.dumps(serialize_function_info(result), indent=2, ensure_ascii=False))
    else:
        print("Extraction failed")