#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QNX函数文档MCP服务器
提供标准MCP接口，让大模型获取QNX函数的HTML文档并解析成结构化JSON
"""

import os
import sys
import json
import logging
import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

# MCP server imports
try:
    from mcp.server import Server
    from mcp.server.models import InitializationOptions
    from mcp.server.stdio import stdio_server
    from mcp.types import (
        Resource, 
        Tool, 
        TextContent, 
        ImageContent, 
        EmbeddedResource
    )
except ImportError:
    print("请安装 mcp 包: pip install mcp")
    sys.exit(1)

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from qnx_html_mcp import QNXHTMLMCPService
from qnx_html_parser_agent import QNXHTMLParserAgent, FunctionParameter, ParsedFunctionInfo
from enhanced_qnx_rag import EnhancedQNXRAG
from qnx_json_extractor import QNXJSONExtractor

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class QNXFunctionInfo:
    """标准的QNX函数信息结构"""
    name: str
    signature: str
    description: str
    parameters: List[Dict[str, str]]
    headers: List[str]
    return_type: str = ""
    return_description: str = ""
    url: str = ""
    html_content: str = ""


class QNXFunctionMCPServer:
    """QNX函数文档MCP服务器"""
    
    def __init__(self):
        self.server = Server("qnx-function-docs")
        self.html_service = QNXHTMLMCPService()
        self.parser_agent = QNXHTMLParserAgent()
        self.enhanced_rag = EnhancedQNXRAG()
        self.json_extractor = QNXJSONExtractor()
        
        # 注册工具
        self._register_tools()
        
        # 注册资源
        self._register_resources()
    
    def _register_tools(self):
        """注册MCP工具"""
        
        @self.server.call_tool()
        async def get_qnx_function_info(function_name: str) -> List[TextContent]:
            """获取QNX函数的结构化信息（JSON格式）- 使用新的JSON提取器"""
            try:
                logger.info(f"获取函数信息: {function_name}")
                
                # 使用新的JSON提取器直接获取结构化信息
                function_info = self.json_extractor.extract_function_json(function_name)
                
                if not function_info:
                    return [TextContent(
                        type="text",
                        text=json.dumps({
                            "error": f"未找到或解析失败: {function_name}",
                            "function_name": function_name
                        }, indent=2, ensure_ascii=False)
                    )]
                
                # 返回JSON格式
                return [TextContent(
                    type="text",
                    text=json.dumps(function_info, indent=2, ensure_ascii=False)
                )]
                
            except Exception as e:
                logger.error(f"获取函数信息失败 {function_name}: {e}")
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "error": f"服务器错误: {str(e)}",
                        "function_name": function_name
                    }, indent=2, ensure_ascii=False)
                )]
        
        @self.server.call_tool()
        async def list_qnx_functions(limit: int = 50) -> List[TextContent]:
            """列出可用的QNX函数名"""
            try:
                # 优先使用增强RAG系统的函数列表
                functions = self.enhanced_rag.list_all_functions(limit=limit)
                if not functions:
                    # 回退到HTML服务
                    functions = self.html_service.list_available_functions(limit=limit)
                
                # 获取集合统计信息
                stats = self.enhanced_rag.get_collection_stats()
                
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "available_functions": functions,
                        "total_count": len(functions),
                        "limit": limit,
                        "rag_status": stats.get("status", "unknown"),
                        "total_in_rag": stats.get("total_functions", 0)
                    }, indent=2, ensure_ascii=False)
                )]
            except Exception as e:
                logger.error(f"列出函数失败: {e}")
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "error": f"列出函数失败: {str(e)}"
                    }, indent=2, ensure_ascii=False)
                )]
        
        @self.server.call_tool()
        async def batch_get_qnx_functions(function_names: List[str]) -> List[TextContent]:
            """批量获取多个QNX函数的信息"""
            try:
                logger.info(f"批量处理 {len(function_names)} 个函数")
                
                # 使用JSON提取器批量处理
                results = self.json_extractor.batch_extract_functions(function_names)
                
                failed = set(function_names) - set(results.keys())
                
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "batch_results": results,
                        "summary": {
                            "requested": len(function_names),
                            "successful": len(results),
                            "failed": len(failed),
                            "failed_functions": list(failed)
                        }
                    }, indent=2, ensure_ascii=False)
                )]
                
            except Exception as e:
                logger.error(f"批量获取失败: {e}")
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "error": f"批量处理失败: {str(e)}"
                    }, indent=2, ensure_ascii=False)
                )]
        
        @self.server.call_tool() 
        async def get_qnx_function_html(function_name: str) -> List[TextContent]:
            """获取QNX函数的原始HTML文档"""
            try:
                html_data = self.html_service.get_function_html(function_name)
                if not html_data:
                    return [TextContent(
                        type="text",
                        text=json.dumps({
                            "error": f"未找到函数 {function_name}",
                            "function_name": function_name
                        }, indent=2, ensure_ascii=False)
                    )]
                
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "function_name": function_name,
                        "html_content": html_data['html_content'],
                        "metadata": html_data['metadata'],
                        "source": html_data['source']
                    }, indent=2, ensure_ascii=False)
                )]
                
            except Exception as e:
                logger.error(f"获取HTML失败 {function_name}: {e}")
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "error": f"获取HTML失败: {str(e)}",
                        "function_name": function_name
                    }, indent=2, ensure_ascii=False)
                )]
    
    def _register_resources(self):
        """注册MCP资源"""
        
        @self.server.list_resources()
        async def list_resources() -> List[Resource]:
            """列出可用资源"""
            return [
                Resource(
                    uri="qnx://functions/list",
                    name="QNX函数列表",
                    description="可用的QNX函数名列表",
                    mimeType="application/json"
                ),
                Resource(
                    uri="qnx://functions/common",
                    name="常用QNX函数",
                    description="常用的QNX函数信息",
                    mimeType="application/json"
                )
            ]
        
        @self.server.read_resource()
        async def read_resource(uri: str) -> str:
            """读取资源内容"""
            if uri == "qnx://functions/list":
                functions = self.html_service.list_available_functions(limit=100)
                return json.dumps({
                    "available_functions": functions,
                    "total_count": len(functions)
                }, indent=2, ensure_ascii=False)
            
            elif uri == "qnx://functions/common":
                # 返回一些常用函数的信息
                common_functions = ["malloc", "free", "printf", "sprintf", "open", "close", "read", "write"]
                results = {}
                
                for func_name in common_functions:
                    html_data = self.html_service.get_function_html(func_name)
                    if html_data:
                        parsed_info = self.parser_agent.parse_html_to_json(func_name)
                        if parsed_info:
                            results[func_name] = {
                                "signature": parsed_info.signature,
                                "description": parsed_info.description,
                                "parameter_count": len(parsed_info.parameters)
                            }
                
                return json.dumps({
                    "common_functions": results
                }, indent=2, ensure_ascii=False)
            
            else:
                raise ValueError(f"未知资源: {uri}")
    
    async def run(self):
        """运行MCP服务器"""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="qnx-function-docs",
                    server_version="1.0.0",
                    capabilities={
                        "tools": {},
                        "resources": {}
                    }
                )
            )


def main():
    """启动MCP服务器"""
    import argparse
    
    parser = argparse.ArgumentParser(description="QNX函数文档MCP服务器")
    parser.add_argument("--test", action="store_true", help="运行测试模式")
    
    args = parser.parse_args()
    
    if args.test:
        # 测试模式 - 直接调用功能测试
        server_instance = QNXFunctionMCPServer()
        
        print("🧪 测试QNX函数MCP服务器")
        
        # 测试获取函数信息
        test_functions = ["sprintf", "malloc", "printf"]
        
        for func_name in test_functions:
            print(f"\n📋 测试函数: {func_name}")
            
            # 测试HTML服务
            html_data = server_instance.html_service.get_function_html(func_name)
            if html_data:
                print(f"✅ HTML获取成功: {len(html_data['html_content'])} 字符")
                
                # 测试解析
                parsed_info = server_instance.parser_agent.parse_html_to_json(func_name)
                if parsed_info:
                    print(f"✅ 解析成功: {len(parsed_info.parameters)} 个参数")
                    print(f"   签名: {parsed_info.signature}")
                    print(f"   描述: {parsed_info.description[:100]}...")
                else:
                    print("❌ 解析失败")
            else:
                print("❌ HTML获取失败")
    
    else:
        # 正常MCP服务器模式
        server = QNXFunctionMCPServer()
        
        logger.info("🚀 启动QNX函数文档MCP服务器")
        logger.info("提供的工具:")
        logger.info("  - get_qnx_function_info: 获取函数结构化信息")
        logger.info("  - list_qnx_functions: 列出可用函数")
        logger.info("  - batch_get_qnx_functions: 批量获取函数信息")
        logger.info("  - get_qnx_function_html: 获取原始HTML")
        
        asyncio.run(server.run())


if __name__ == "__main__":
    main()