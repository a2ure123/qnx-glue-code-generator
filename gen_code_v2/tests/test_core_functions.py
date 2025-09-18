#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试核心功能 - 不依赖MCP包
直接测试RAG系统和JSON提取器的核心功能
"""

import os
import sys
import json
import logging

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from enhanced_qnx_rag import EnhancedQNXRAG
from qnx_json_extractor import QNXJSONExtractor

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_rag_system():
    """测试RAG系统"""
    print("🔍 测试RAG系统...")
    
    rag = EnhancedQNXRAG()
    stats = rag.get_collection_stats()
    
    print(f"RAG状态: {stats['status']}")
    print(f"总函数数: {stats.get('total_functions', 0)}")
    
    if stats['status'] != 'ready' or stats.get('total_functions', 0) == 0:
        print("⚠️  RAG系统未就绪")
        return False
    
    # 测试函数查找
    sample_functions = stats.get('sample_functions', [])[:3]
    print(f"测试函数: {sample_functions}")
    
    success_count = 0
    for func_name in sample_functions:
        result = rag.get_function_by_name(func_name)
        if result:
            print(f"✅ {func_name}: {len(result['html_content'])} 字符")
            success_count += 1
        else:
            print(f"❌ {func_name}: 未找到")
    
    print(f"RAG测试结果: {success_count}/{len(sample_functions)}")
    return success_count > 0


def test_json_extractor():
    """测试JSON提取器"""
    print("\n📋 测试JSON提取器...")
    
    extractor = QNXJSONExtractor()
    
    # 获取可用函数
    rag = EnhancedQNXRAG()
    stats = rag.get_collection_stats()
    sample_functions = stats.get('sample_functions', [])[:3]
    
    if not sample_functions:
        print("❌ 没有可测试的函数")
        return False
    
    success_count = 0
    for func_name in sample_functions:
        print(f"测试提取: {func_name}")
        result = extractor.extract_function_json(func_name)
        
        if result:
            print(f"✅ {func_name}: {len(result.get('parameters', []))}参数, {len(result.get('headers', []))}头文件")
            success_count += 1
        else:
            print(f"❌ {func_name}: 提取失败")
    
    print(f"JSON提取测试结果: {success_count}/{len(sample_functions)}")
    return success_count > 0


def test_mcp_like_interface():
    """测试类MCP接口功能"""
    print("\n🖥️  测试MCP类接口...")
    
    # 模拟MCP工具调用
    def get_qnx_function_info(function_name: str):
        """模拟MCP的get_qnx_function_info工具"""
        extractor = QNXJSONExtractor()
        function_info = extractor.extract_function_json(function_name)
        
        if not function_info:
            return {
                "error": f"未找到或解析失败: {function_name}",
                "function_name": function_name
            }
        
        return function_info
    
    def list_qnx_functions(limit: int = 10):
        """模拟MCP的list_qnx_functions工具"""
        rag = EnhancedQNXRAG()
        functions = rag.list_all_functions(limit=limit)
        stats = rag.get_collection_stats()
        
        return {
            "available_functions": functions,
            "total_count": len(functions),
            "limit": limit,
            "rag_status": stats.get("status", "unknown"),
            "total_in_rag": stats.get("total_functions", 0)
        }
    
    def batch_get_qnx_functions(function_names: list):
        """模拟MCP的batch_get_qnx_functions工具"""
        extractor = QNXJSONExtractor()
        results = extractor.batch_extract_functions(function_names)
        
        failed = set(function_names) - set(results.keys())
        
        return {
            "batch_results": results,
            "summary": {
                "requested": len(function_names),
                "successful": len(results),
                "failed": len(failed),
                "failed_functions": list(failed)
            }
        }
    
    # 测试这些模拟的MCP工具
    print("测试 list_qnx_functions...")
    list_result = list_qnx_functions(5)
    print(f"  可用函数: {len(list_result['available_functions'])}")
    print(f"  RAG状态: {list_result['rag_status']}")
    
    available_functions = list_result['available_functions']
    if available_functions:
        test_function = available_functions[0]
        
        print(f"\n测试 get_qnx_function_info({test_function})...")
        func_result = get_qnx_function_info(test_function)
        
        if 'error' not in func_result:
            print(f"  ✅ 函数信息获取成功")
            print(f"  签名: {func_result.get('signature', 'N/A')}")
            print(f"  参数数量: {len(func_result.get('parameters', []))}")
            print(f"  头文件数量: {len(func_result.get('headers', []))}")
        else:
            print(f"  ❌ {func_result.get('error', '未知错误')}")
        
        print(f"\n测试 batch_get_qnx_functions([{test_function}])...")
        batch_result = batch_get_qnx_functions([test_function])
        print(f"  批量结果: {batch_result['summary']['successful']}/{batch_result['summary']['requested']}")
        
        return True
    else:
        print("❌ 没有可测试的函数")
        return False


def main():
    """主测试函数"""
    print("🚀 核心功能测试")
    print("="*50)
    
    # 测试RAG系统
    rag_ok = test_rag_system()
    
    # 测试JSON提取器
    json_ok = test_json_extractor()
    
    # 测试MCP类接口
    mcp_ok = test_mcp_like_interface()
    
    print("\n" + "="*50)
    print("📊 测试总结:")
    print(f"  RAG系统: {'✅ 通过' if rag_ok else '❌ 失败'}")
    print(f"  JSON提取: {'✅ 通过' if json_ok else '❌ 失败'}")
    print(f"  MCP接口: {'✅ 通过' if mcp_ok else '❌ 失败'}")
    
    all_passed = rag_ok and json_ok and mcp_ok
    if all_passed:
        print("\n🎉 所有核心功能测试通过！")
        print("💡 系统已准备好供大模型调用")
        
        # 输出示例使用方法
        print("\n📝 使用示例:")
        print("1. 获取函数信息:")
        print('   get_qnx_function_info("abort")')
        print("2. 列出可用函数:")
        print('   list_qnx_functions(50)')
        print("3. 批量获取函数:")
        print('   batch_get_qnx_functions(["abort", "access", "alarm"])')
        
    else:
        print("\n⚠️  部分功能测试失败，请检查问题")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit(main())