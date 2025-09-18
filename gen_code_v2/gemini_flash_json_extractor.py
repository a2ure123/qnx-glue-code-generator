#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于Gemini 2.5 Flash的高效JSON数据提取器
专门用于从HTML文档中提取QNX函数信息并输出标准JSON格式
"""

import os
import sys
import json
import logging
import re
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from pathlib import Path
import google.generativeai as genai
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 禁用第三方库的详细日志
logging.getLogger("chromadb.telemetry").setLevel(logging.ERROR)
logging.getLogger("backoff").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.ERROR)


@dataclass
class FunctionParameter:
    """函数参数信息"""
    name: str
    type: str
    description: str = ""
    is_pointer: bool = False
    is_const: bool = False
    is_optional: bool = False


@dataclass
class HeaderFile:
    """头文件信息"""
    filename: str
    path: str = ""
    is_system: bool = True  # 是否为系统头文件 (<> 包围)


@dataclass
class QNXFunctionInfo:
    """QNX函数完整信息"""
    name: str
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


class GeminiFlashJSONExtractor:
    """基于Gemini 2.5 Flash的JSON提取器"""
    
    def __init__(self, config_path: str = "config.json"):
        """初始化JSON提取器"""
        # 加载配置
        self.config = self._load_config(config_path)
        
        # AI配置
        ai_config = self.config.get("ai_settings", {})
        gemini_config = ai_config.get("gemini", {})
        
        self.api_key_env = gemini_config.get("api_key_env", "GEMINI_API_KEY")
        self.model_name = gemini_config.get("model", "gemini-2.5-flash")
        self.max_tokens = gemini_config.get("max_tokens", 4000)
        self.temperature = gemini_config.get("temperature", 0.1)
        
        # 初始化Gemini
        self._initialize_gemini()
        
        # JSON提取提示模板
        self.extraction_prompt = self._create_extraction_prompt()
        
        logger.info(f"Gemini 2.5 Flash JSON提取器初始化完成")
        logger.info(f"模型: {self.model_name}")
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"配置文件加载失败: {e}")
            return {}
    
    def _initialize_gemini(self):
        """初始化Gemini客户端"""
        api_key = os.getenv(self.api_key_env)
        if not api_key:
            raise ValueError(f"请设置环境变量 {self.api_key_env}")
        
        genai.configure(api_key=api_key)
        
        # 配置生成参数
        generation_config = genai.types.GenerationConfig(
            max_output_tokens=self.max_tokens,
            temperature=self.temperature,
            response_mime_type="application/json"  # 强制JSON输出
        )
        
        self.model = genai.GenerativeModel(
            model_name=self.model_name,
            generation_config=generation_config
        )
        
        logger.info("Gemini 2.5 Flash客户端初始化成功")
    
    def _create_extraction_prompt(self) -> str:
        """创建JSON提取提示模板"""
        return """
你是一个专业的QNX函数文档JSON提取器。请从以下HTML文档中提取函数信息，并返回标准JSON格式。

请按照以下JSON schema格式输出：

{
  "name": "函数名称",
  "synopsis": "函数声明/原型",
  "description": "函数描述",
  "parameters": [
    {
      "name": "参数名",
      "type": "参数类型",
      "description": "参数描述",
      "is_pointer": false,
      "is_const": false,
      "is_optional": false
    }
  ],
  "return_type": "返回值类型",
  "return_description": "返回值描述",
  "headers": [
    {
      "filename": "头文件名",
      "path": "完整路径",
      "is_system": true
    }
  ],
  "libraries": ["链接库列表"],
  "examples": ["代码示例"],
  "see_also": ["相关函数"],
  "classification": "函数分类",
  "safety": "线程安全性"
}

提取规则：
1. 准确提取函数名、参数列表、返回类型
2. 识别参数是否为指针、常量、可选
3. 提取完整的函数描述和参数说明
4. 识别所需头文件和链接库
5. 提取代码示例和相关函数
6. 如果某个字段在文档中不存在，设为空字符串或空数组
7. 确保输出是有效的JSON格式

HTML文档内容：
"""
    
    def clean_html_content(self, html_content: str) -> str:
        """清理HTML内容，保留有用的文本信息"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 移除script和style标签
            for script in soup(["script", "style"]):
                script.decompose()
            
            # 获取主要内容区域
            main_content = soup.find('div', class_='content') or soup.find('main') or soup.body or soup
            
            if main_content:
                # 保留结构化信息
                text_content = main_content.get_text(separator='\n', strip=True)
                
                # 清理多余的空行
                lines = [line.strip() for line in text_content.split('\n') if line.strip()]
                cleaned_text = '\n'.join(lines)
                
                # 限制长度，避免超出token限制
                if len(cleaned_text) > 8000:
                    cleaned_text = cleaned_text[:8000] + "\n... (内容被截断)"
                
                return cleaned_text
            else:
                return html_content[:8000]
                
        except Exception as e:
            logger.warning(f"HTML清理失败: {e}")
            return html_content[:8000]
    
    def extract_function_info(self, html_content: str, function_name: str = "") -> Optional[QNXFunctionInfo]:
        """从HTML内容中提取函数信息"""
        try:
            # 清理HTML内容
            cleaned_content = self.clean_html_content(html_content)
            
            # 构建完整提示
            full_prompt = self.extraction_prompt + "\n\n" + cleaned_content
            
            if function_name:
                full_prompt += f"\n\n请重点关注函数: {function_name}"
            
            # 调用Gemini 2.5 Flash进行提取
            logger.info(f"开始提取函数信息: {function_name or '未指定'}")
            
            response = self.model.generate_content(full_prompt)
            
            if response.text:
                # 解析JSON响应
                json_data = json.loads(response.text)
                
                # 转换为QNXFunctionInfo对象
                function_info = self._json_to_function_info(json_data)
                
                logger.info(f"函数信息提取成功: {function_info.name}")
                return function_info
            else:
                logger.error("Gemini响应为空")
                return None
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {e}")
            logger.error(f"原始响应: {response.text if 'response' in locals() else 'N/A'}")
            return None
        except Exception as e:
            logger.error(f"函数信息提取失败: {e}")
            return None
    
    def _json_to_function_info(self, json_data: Dict[str, Any]) -> QNXFunctionInfo:
        """将JSON数据转换为QNXFunctionInfo对象"""
        # 转换参数列表
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
        
        # 转换头文件列表
        headers = []
        for header_data in json_data.get("headers", []):
            header = HeaderFile(
                filename=header_data.get("filename", ""),
                path=header_data.get("path", ""),
                is_system=header_data.get("is_system", True)
            )
            headers.append(header)
        
        # 创建函数信息对象
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
    
    def extract_batch_functions(self, html_files: List[Dict[str, str]]) -> List[QNXFunctionInfo]:
        """批量提取函数信息"""
        results = []
        
        logger.info(f"开始批量提取 {len(html_files)} 个文件的函数信息")
        
        for i, file_info in enumerate(html_files):
            file_path = file_info.get("path", "")
            function_name = file_info.get("function_name", "")
            html_content = file_info.get("content", "")
            
            logger.info(f"处理文件 {i+1}/{len(html_files)}: {function_name}")
            
            try:
                if html_content:
                    function_info = self.extract_function_info(html_content, function_name)
                    if function_info:
                        results.append(function_info)
                elif file_path and os.path.exists(file_path):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        html_content = f.read()
                    function_info = self.extract_function_info(html_content, function_name)
                    if function_info:
                        results.append(function_info)
                else:
                    logger.warning(f"无效的文件信息: {file_info}")
                    
            except Exception as e:
                logger.error(f"处理文件失败 {file_path}: {e}")
                continue
        
        logger.info(f"批量提取完成: {len(results)}/{len(html_files)} 成功")
        return results
    
    def save_function_info_json(self, function_info: QNXFunctionInfo, output_path: str):
        """保存函数信息为JSON文件"""
        try:
            # 转换为字典
            data = asdict(function_info)
            
            # 确保输出目录存在
            output_dir = os.path.dirname(output_path)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
            
            # 保存JSON文件
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"函数信息已保存到: {output_path}")
            
        except Exception as e:
            logger.error(f"保存JSON文件失败: {e}")
    
    def validate_json_output(self, json_data: Dict[str, Any]) -> bool:
        """验证JSON输出格式"""
        required_fields = ["name", "synopsis", "description", "parameters", "return_type"]
        
        for field in required_fields:
            if field not in json_data:
                logger.warning(f"缺少必需字段: {field}")
                return False
        
        # 验证参数格式
        if isinstance(json_data.get("parameters"), list):
            for param in json_data["parameters"]:
                if not isinstance(param, dict) or "name" not in param or "type" not in param:
                    logger.warning(f"参数格式错误: {param}")
                    return False
        
        return True


def main():
    """主函数 - 测试JSON提取器"""
    try:
        # 初始化提取器
        extractor = GeminiFlashJSONExtractor()
        
        # 测试HTML内容
        test_html = """
        <html>
        <body>
        <div class="content">
        <h1>sprintf</h1>
        <h2>Synopsis</h2>
        <p>int sprintf(char *s, const char *format, ...);</p>
        <h2>Description</h2>
        <p>The sprintf() function formats and stores a series of characters in the buffer s.</p>
        <h2>Parameters</h2>
        <p>s - Pointer to the buffer where the formatted string is stored</p>
        <p>format - Format string containing format specifiers</p>
        <h2>Returns</h2>
        <p>Number of characters written, excluding the null terminator</p>
        <h2>Header</h2>
        <p>#include &lt;stdio.h&gt;</p>
        </div>
        </body>
        </html>
        """
        
        # 提取函数信息
        function_info = extractor.extract_function_info(test_html, "sprintf")
        
        if function_info:
            print("提取成功!")
            print(f"函数名: {function_info.name}")
            print(f"声明: {function_info.synopsis}")
            print(f"描述: {function_info.description}")
            print(f"参数数量: {len(function_info.parameters)}")
            
            # 保存JSON文件
            extractor.save_function_info_json(function_info, "./test_sprintf.json")
        else:
            print("提取失败!")
        
    except Exception as e:
        logger.error(f"测试失败: {e}")


if __name__ == "__main__":
    main()