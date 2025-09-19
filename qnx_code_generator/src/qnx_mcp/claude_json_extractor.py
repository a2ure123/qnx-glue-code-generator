#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Claude-based JSON Extractor for QNX Functions
Fast and efficient extraction using Claude Haiku model
"""

import os
import sys
import json
import logging
import time
import requests
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from bs4 import BeautifulSoup

# Add src directory to Python path  
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from qnx_batch_processor import serialize_function_info
from qnx_gdb_type_enhancer import QNXGDBTypeEnhancer

logger = logging.getLogger(__name__)

class ClaudeJSONExtractor:
    """Claude-based JSON extractor for QNX functions"""
    
    def __init__(self, config_path: str = "config.json", enable_gdb_in_extraction: bool = False):
        """Initialize Claude JSON extractor
        
        Args:
            config_path: Configuration file path
            enable_gdb_in_extraction: Whether to enable GDB enhancement during JSON extraction
        """
        # Load configuration
        self.config = self._load_config(config_path)
        
        # AI configuration
        ai_config = self.config.get("ai_settings", {})
        claude_config = ai_config.get("claude", {})
        
        # Claude configuration
        self.api_key_env = claude_config.get("api_key_env", "CLAUDE_API_KEY")
        self.base_url = claude_config.get("base_url", "http://10.12.190.50:3000/api")
        self.model = claude_config.get("model", "claude-3-haiku-20240307")
        self.max_tokens = claude_config.get("max_tokens", 4000)
        self.temperature = claude_config.get("temperature", 0.1)
        
        # Initialize API key
        self.api_key = os.getenv(self.api_key_env)
        if not self.api_key:
            raise ValueError(f"Please set environment variable {self.api_key_env}")
        
        # Request settings
        request_config = self.config.get("network_settings", {}).get("request_settings", {})
        self.timeout = request_config.get("timeout", 30)
        self.max_retries = request_config.get("max_retries", 3)
        self.retry_delay = request_config.get("retry_delay", 1.0)
        
        # Initialize QNX GDB type enhancer (only if enabled for extraction phase)
        if enable_gdb_in_extraction:
            try:
                self.gdb_enhancer = QNXGDBTypeEnhancer(config_path)
                self.gdb_enhancement_enabled = True
                logger.info("QNX GDB type enhancer initialized successfully")
            except Exception as e:
                logger.warning(f"QNX GDB type enhancer initialization failed: {e}")
                self.gdb_enhancer = None
                self.gdb_enhancement_enabled = False
        else:
            self.gdb_enhancer = None
            self.gdb_enhancement_enabled = False
            logger.info("GDB enhancement disabled for extraction phase")
        
        # JSON extraction prompt template
        self.extraction_prompt = self._create_extraction_prompt()
        
        logger.info(f"Claude JSON extractor initialization completed")
        logger.info(f"Model: {self.model}")
        logger.info(f"Base URL: {self.base_url}")
        logger.info(f"GDB enhancement: {'Enabled' if self.gdb_enhancement_enabled else 'Disabled'}")
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration file"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load config file: {e}")
            return {}
    
    def _create_extraction_prompt(self) -> str:
        """Create JSON extraction prompt template"""
        return """You are a professional QNX function documentation JSON extractor. Please extract information from the QNX function documentation and output in strict JSON format.

Required JSON structure:
{
  "name": "function_name",
  "synopsis": "function prototype/signature",
  "description": "brief description",
  "parameters": [
    {
      "name": "param_name",
      "type": "param_type",
      "description": "param description",
      "is_pointer": false,
      "is_const": false,
      "is_optional": false
    }
  ],
  "return_type": "return_type",
  "return_description": "return value description",
  "headers": [
    {
      "filename": "header.h",
      "path": "/usr/include/header.h",
      "is_system": true
    }
  ],
  "libraries": ["library_name"],
  "examples": ["code example"],
  "see_also": ["related_function"],
  "classification": "function category",
  "safety": "thread safety info"
}

Important requirements:
1. ONLY output valid JSON, no explanations or additional text
2. If information is missing, use empty string "" or empty array []
3. Ensure all quotes are properly escaped
4. Focus on accuracy and completeness
5. Extract function prototype exactly as shown"""
    
    def clean_html_content(self, html_content: str) -> str:
        """Clean HTML content and extract text"""
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
        """Extract function information from HTML content using Claude API"""
        
        for attempt in range(self.max_retries):
            try:
                # Clean HTML content
                cleaned_content = self.clean_html_content(html_content)
                
                # Build full prompt
                full_prompt = self.extraction_prompt + "\n\n" + cleaned_content
                
                if function_name:
                    full_prompt += f"\n\nPlease focus on function: {function_name}"
                
                # Call Claude API for extraction
                logger.info(f"Start extracting function info: {function_name or 'Not specified'} (Attempt {attempt + 1}/{self.max_retries})")
                
                response = self._call_claude_api(full_prompt)
                
                if response:
                    # Parse JSON response
                    try:
                        json_data = json.loads(response)
                        function_info = self._json_to_function_info(json_data)
                        
                        # GDB type enhancement
                        if self.gdb_enhancement_enabled and function_info:
                            function_info = self._enhance_with_gdb_info(function_info)
                        
                        logger.info(f"Function info extracted successfully: {function_info.name}")
                        return function_info
                    except json.JSONDecodeError as e:
                        logger.error(f"JSON parsing failed: {e}")
                        logger.error(f"Raw response: {response[:500]}...")
                        if attempt < self.max_retries - 1:
                            time.sleep(self.retry_delay)
                            continue
                        return None
                else:
                    logger.warning(f"Claude response is empty (Attempt {attempt + 1}/{self.max_retries})")
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay)
                        continue
                    else:
                        logger.error("Failed to get valid response after multiple attempts")
                        return None
                        
            except Exception as e:
                logger.error(f"Function info extraction failed: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    continue
                return None
        
        return None
    
    def _call_claude_api(self, prompt: str) -> Optional[str]:
        """Call Claude API with the given prompt"""
        # Try different endpoint formats since this might be a relay service
        endpoints_to_try = [
            f"{self.base_url}/v1/chat/completions",  # OpenAI compatible format
            f"{self.base_url}/chat/completions",     # Alternative format
            f"{self.base_url}/v1/messages",          # Anthropic format
            f"{self.base_url}/messages",             # Anthropic format without version
            self.base_url                            # Direct base URL
        ]
        
        for endpoint in endpoints_to_try:
            try:
                # Try OpenAI compatible format first
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                }
                
                # OpenAI compatible payload
                payload = {
                    "model": self.model,
                    "max_tokens": self.max_tokens,
                    "temperature": self.temperature,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                }
                
                logger.info(f"Trying endpoint: {endpoint}")
                response = requests.post(
                    endpoint,
                    headers=headers,
                    json=payload,
                    timeout=self.timeout
                )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # Try different response formats
                    if "choices" in result and len(result["choices"]) > 0:
                        # OpenAI format
                        return result["choices"][0]["message"]["content"]
                    elif "content" in result and len(result["content"]) > 0:
                        # Anthropic format
                        return result["content"][0]["text"]
                    elif "response" in result:
                        # Alternative format
                        return result["response"]
                    else:
                        logger.warning(f"Unknown response format: {result}")
                        continue
                        
                elif response.status_code == 404:
                    # Try next endpoint
                    continue
                else:
                    logger.error(f"Claude API error at {endpoint}: {response.status_code} - {response.text}")
                    continue
                    
            except requests.RequestException as e:
                logger.warning(f"Request to {endpoint} failed: {e}")
                continue
        
        logger.error("All Claude API endpoints failed")
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
            
            # Enhance parameter type information with new info field structure
            if function_info.parameters:
                # Convert to dict format for enhancement
                param_dicts = []
                for param in function_info.parameters:
                    param_dict = {
                        'name': param.name,
                        'type': param.type,
                        'description': param.description,
                        'is_pointer': param.is_pointer,
                        'is_const': param.is_const,
                        'is_optional': param.is_optional
                    }
                    param_dicts.append(param_dict)
                
                # Enhance parameters
                enhanced_param_dicts = self.gdb_enhancer.enhance_function_parameters(param_dicts)
                
                # Convert back to FunctionParameter objects
                enhanced_params = []
                for param_dict in enhanced_param_dicts:
                    param = FunctionParameter(
                        name=param_dict.get('name', ''),
                        type=param_dict.get('type', ''),
                        description=param_dict.get('description', ''),
                        is_pointer=param_dict.get('is_pointer', False),
                        is_const=param_dict.get('is_const', False),
                        is_optional=param_dict.get('is_optional', False)
                    )
                    # Add the info field as a custom attribute
                    if 'info' in param_dict:
                        param.info = param_dict['info']
                    enhanced_params.append(param)
                
                function_info.parameters = enhanced_params
                logger.info(f"Enhanced {len(enhanced_params)} parameters with GDB info")
            
            # Enhance header file information with complete paths
            if function_info.headers:
                # Convert to dict format for enhancement
                header_dicts = []
                for header in function_info.headers:
                    header_dict = {
                        'filename': header.filename,
                        'path': header.path,
                        'is_system': header.is_system
                    }
                    header_dicts.append(header_dict)
                
                # Enhance headers
                enhanced_header_dicts = self.gdb_enhancer.enhance_header_file_paths(header_dicts)
                
                # Convert back to HeaderFile objects
                enhanced_headers = []
                for header_dict in enhanced_header_dicts:
                    header = HeaderFile(
                        filename=header_dict.get('filename', ''),
                        path=header_dict.get('path', ''),
                        is_system=header_dict.get('is_system', True)
                    )
                    enhanced_headers.append(header)
                
                function_info.headers = enhanced_headers
                logger.info(f"Enhanced {len(enhanced_headers)} headers with complete paths")
            
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


def main():
    """Test function"""
    logging.basicConfig(level=logging.INFO)
    
    # Test with a simple HTML content
    test_html = """
    <html>
    <body>
    <h1>abort</h1>
    <p>Synopsis: void abort(void);</p>
    <p>Description: Terminates the program abnormally.</p>
    <p>Header: stdlib.h</p>
    </body>
    </html>
    """
    
    try:
        extractor = ClaudeJSONExtractor()
        result = extractor.extract_function_info(test_html, "abort")
        if result:
            print(f"Extracted function: {result.name}")
            print(f"Synopsis: {result.synopsis}")
        else:
            print("Extraction failed")
    except Exception as e:
        print(f"Test failed: {e}")


if __name__ == "__main__":
    main()