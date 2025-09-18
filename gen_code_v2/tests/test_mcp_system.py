#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QNX MCP系统综合测试脚本
测试完整的工作流程：函数名作为key的RAG -> HTML内容 -> JSON提取
"""

import os
import sys
import json
import asyncio
import logging
from typing import List, Dict, Any

# 添加上级目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from enhanced_qnx_rag import EnhancedQNXRAG
from qnx_json_extractor import QNXJSONExtractor
# from qnx_function_mcp_server import QNXFunctionMCPServer

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class QNXMCPSystemTester:
    """QNX MCP系统测试器"""
    
    def __init__(self):
        self.enhanced_rag = EnhancedQNXRAG()
        self.json_extractor = QNXJSONExtractor()
        # self.mcp_server = QNXFunctionMCPServer()
    
    def test_rag_system(self, test_functions: List[str] = None) -> Dict[str, Any]:
        """测试RAG系统"""
        if not test_functions:
            test_functions = ["sprintf", "malloc", "printf"]
        
        logger.info("🔍 测试RAG系统...")
        
        results = {
            "rag_stats": self.enhanced_rag.get_collection_stats(),
            "function_tests": {},
            "summary": {
                "total_tested": 0,
                "successful": 0,
                "failed": 0
            }
        }
        
        for func_name in test_functions:
            logger.info(f"测试函数: {func_name}")
            
            # 测试精确查找
            rag_result = self.enhanced_rag.get_function_by_name(func_name)
            
            test_result = {
                "found_in_rag": bool(rag_result),
                "html_length": 0,
                "metadata": {}
            }
            
            if rag_result:
                test_result["html_length"] = len(rag_result['html_content'])
                test_result["metadata"] = rag_result['metadata']
                results["summary"]["successful"] += 1
            else:
                results["summary"]["failed"] += 1
            
            results["function_tests"][func_name] = test_result
            results["summary"]["total_tested"] += 1
        
        return results
    
    def test_json_extraction(self, test_functions: List[str] = None) -> Dict[str, Any]:
        """测试JSON提取"""
        if not test_functions:
            test_functions = ["sprintf", "malloc", "printf"]
        
        logger.info("📋 测试JSON提取...")
        
        results = {
            "extraction_tests": {},
            "summary": {
                "total_tested": 0,
                "successful": 0,
                "failed": 0
            }
        }
        
        for func_name in test_functions:
            logger.info(f"提取函数JSON: {func_name}")
            
            json_result = self.json_extractor.extract_function_json(func_name)
            
            test_result = {
                "extraction_successful": bool(json_result),
                "parameter_count": 0,
                "header_count": 0,
                "has_signature": False,
                "has_description": False
            }
            
            if json_result:
                test_result["parameter_count"] = len(json_result.get('parameters', []))
                test_result["header_count"] = len(json_result.get('headers', []))
                test_result["has_signature"] = bool(json_result.get('signature', ''))
                test_result["has_description"] = bool(json_result.get('description', ''))
                test_result["function_spec"] = json_result
                results["summary"]["successful"] += 1
            else:
                results["summary"]["failed"] += 1
            
            results["extraction_tests"][func_name] = test_result
            results["summary"]["total_tested"] += 1
        
        return results
    
    def test_batch_operations(self, test_functions: List[str] = None) -> Dict[str, Any]:
        """测试批量操作"""
        if not test_functions:
            test_functions = ["sprintf", "malloc", "printf", "open", "close"]
        
        logger.info("📦 测试批量操作...")
        
        results = {}
        
        # 测试RAG批量获取
        logger.info("测试RAG批量获取...")
        rag_batch_result = self.enhanced_rag.batch_get_functions(test_functions)
        results["rag_batch"] = {
            "requested": len(test_functions),
            "successful": len(rag_batch_result),
            "failed": len(test_functions) - len(rag_batch_result),
            "results": {k: {"html_length": len(v['html_content'])} for k, v in rag_batch_result.items()}
        }
        
        # 测试JSON批量提取
        logger.info("测试JSON批量提取...")
        json_batch_result = self.json_extractor.batch_extract_functions(test_functions)
        results["json_batch"] = {
            "requested": len(test_functions),
            "successful": len(json_batch_result),
            "failed": len(test_functions) - len(json_batch_result),
            "results": {k: {
                "parameter_count": len(v.get('parameters', [])),
                "header_count": len(v.get('headers', []))
            } for k, v in json_batch_result.items()}
        }
        
        return results
    
    def test_mcp_server_components(self) -> Dict[str, Any]:
        """测试MCP服务器组件（非异步部分）"""
        logger.info("🖥️  测试系统组件...")
        
        results = {
            "components_initialized": {
                "enhanced_rag": bool(self.enhanced_rag),
                "json_extractor": bool(self.json_extractor)
            },
            "rag_status": self.enhanced_rag.get_collection_stats()
        }
        
        return results
    
    def run_comprehensive_test(self, test_functions: List[str] = None) -> Dict[str, Any]:
        """运行综合测试"""
        if not test_functions:
            test_functions = ["sprintf", "malloc", "printf"]
        
        logger.info(f"🚀 开始综合测试，测试函数: {test_functions}")
        
        comprehensive_results = {
            "test_configuration": {
                "test_functions": test_functions,
                "total_functions": len(test_functions)
            },
            "rag_system_test": {},
            "json_extraction_test": {},
            "batch_operations_test": {},
            "mcp_components_test": {},
            "overall_summary": {}
        }
        
        try:
            # 1. 测试RAG系统
            comprehensive_results["rag_system_test"] = self.test_rag_system(test_functions)
            
            # 2. 测试JSON提取
            comprehensive_results["json_extraction_test"] = self.test_json_extraction(test_functions)
            
            # 3. 测试批量操作
            comprehensive_results["batch_operations_test"] = self.test_batch_operations(test_functions)
            
            # 4. 测试MCP组件
            comprehensive_results["mcp_components_test"] = self.test_mcp_server_components()
            
            # 5. 计算总体摘要
            rag_success = comprehensive_results["rag_system_test"]["summary"]["successful"]
            json_success = comprehensive_results["json_extraction_test"]["summary"]["successful"]
            
            comprehensive_results["overall_summary"] = {
                "rag_success_rate": rag_success / len(test_functions) if test_functions else 0,
                "json_success_rate": json_success / len(test_functions) if test_functions else 0,
                "system_ready": rag_success > 0 and json_success > 0,
                "total_tested": len(test_functions)
            }
            
            logger.info(f"✅ 综合测试完成！RAG成功率: {comprehensive_results['overall_summary']['rag_success_rate']:.2%}, JSON成功率: {comprehensive_results['overall_summary']['json_success_rate']:.2%}")
            
        except Exception as e:
            logger.error(f"综合测试失败: {e}")
            comprehensive_results["error"] = str(e)
        
        return comprehensive_results


def print_test_results(results: Dict[str, Any]):
    """打印测试结果"""
    print(f"\n{'='*60}")
    print("🧪 QNX MCP系统测试结果")
    print(f"{'='*60}")
    
    # 测试配置
    config = results.get("test_configuration", {})
    print(f"\n📋 测试配置:")
    print(f"   测试函数: {config.get('test_functions', [])}")
    print(f"   函数总数: {config.get('total_functions', 0)}")
    
    # RAG系统测试
    rag_test = results.get("rag_system_test", {})
    if rag_test:
        rag_summary = rag_test.get("summary", {})
        rag_stats = rag_test.get("rag_stats", {})
        
        print(f"\n🔍 RAG系统测试:")
        print(f"   集合状态: {rag_stats.get('status', 'unknown')}")
        print(f"   总函数数: {rag_stats.get('total_functions', 0)}")
        print(f"   测试成功: {rag_summary.get('successful', 0)}/{rag_summary.get('total_tested', 0)}")
    
    # JSON提取测试
    json_test = results.get("json_extraction_test", {})
    if json_test:
        json_summary = json_test.get("summary", {})
        
        print(f"\n📋 JSON提取测试:")
        print(f"   提取成功: {json_summary.get('successful', 0)}/{json_summary.get('total_tested', 0)}")
        
        # 显示函数详情
        for func_name, test_result in json_test.get("extraction_tests", {}).items():
            if test_result.get("extraction_successful"):
                print(f"   ✅ {func_name}: {test_result.get('parameter_count', 0)}参数, {test_result.get('header_count', 0)}头文件")
            else:
                print(f"   ❌ {func_name}: 提取失败")
    
    # 批量操作测试
    batch_test = results.get("batch_operations_test", {})
    if batch_test:
        print(f"\n📦 批量操作测试:")
        
        rag_batch = batch_test.get("rag_batch", {})
        print(f"   RAG批量: {rag_batch.get('successful', 0)}/{rag_batch.get('requested', 0)}")
        
        json_batch = batch_test.get("json_batch", {})
        print(f"   JSON批量: {json_batch.get('successful', 0)}/{json_batch.get('requested', 0)}")
    
    # MCP组件测试
    mcp_test = results.get("mcp_components_test", {})
    if mcp_test:
        components = mcp_test.get("components_initialized", {})
        print(f"\n🖥️  MCP组件测试:")
        for comp_name, initialized in components.items():
            status = "✅" if initialized else "❌"
            print(f"   {status} {comp_name}: {'已初始化' if initialized else '未初始化'}")
    
    # 总体摘要
    overall = results.get("overall_summary", {})
    if overall:
        print(f"\n🎯 总体摘要:")
        print(f"   RAG成功率: {overall.get('rag_success_rate', 0):.2%}")
        print(f"   JSON成功率: {overall.get('json_success_rate', 0):.2%}")
        print(f"   系统就绪: {'是' if overall.get('system_ready', False) else '否'}")
    
    if results.get("error"):
        print(f"\n❌ 错误: {results['error']}")
    
    print(f"\n{'='*60}")


def main():
    """主测试函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="QNX MCP系统综合测试")
    parser.add_argument("--functions", nargs='+', default=["sprintf", "malloc", "printf"],
                       help="要测试的函数列表")
    parser.add_argument("--build-rag", action="store_true", help="构建RAG索引（如果不存在）")
    parser.add_argument("--rebuild-rag", action="store_true", help="重建RAG索引")
    parser.add_argument("--max-functions", type=int, default=50, help="构建RAG时的最大函数数")
    parser.add_argument("--output", type=str, help="输出测试结果到JSON文件")
    
    args = parser.parse_args()
    
    logger.info("🚀 QNX MCP系统综合测试")
    
    # 创建测试器
    tester = QNXMCPSystemTester()
    
    # 检查RAG状态
    rag_stats = tester.enhanced_rag.get_collection_stats()
    print(f"📊 RAG状态: {rag_stats.get('status', 'unknown')}")
    
    # 构建RAG（如果需要）
    if args.build_rag or args.rebuild_rag or rag_stats.get('status') != 'ready':
        logger.info("🔨 构建RAG索引...")
        count = tester.enhanced_rag.build_enhanced_index(
            force_rebuild=args.rebuild_rag,
            max_functions=args.max_functions
        )
        print(f"✅ RAG索引构建完成: {count} 个函数")
    
    # 运行综合测试
    results = tester.run_comprehensive_test(args.functions)
    
    # 打印结果
    print_test_results(results)
    
    # 保存结果
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"💾 测试结果已保存到: {args.output}")
    
    # 返回系统状态码
    overall_summary = results.get("overall_summary", {})
    system_ready = overall_summary.get("system_ready", False)
    
    if system_ready:
        print("\n🎉 系统测试通过！QNX MCP系统已就绪。")
        return 0
    else:
        print("\n⚠️  系统测试未完全通过，请检查错误信息。")
        return 1


if __name__ == "__main__":
    exit_code = main()