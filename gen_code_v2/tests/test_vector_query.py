#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试向量化数据库查询功能
输入函数名，查询对应的向量化信息和HTML内容
"""

import os
import sys
import json
import logging
from typing import Optional, Dict, Any

# 添加父目录到Python路径以导入模块
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from enhanced_qnx_rag import EnhancedQNXRAG
from qnx_json_extractor import QNXJSONExtractor

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 禁用第三方库的详细日志
logging.getLogger("chromadb.telemetry").setLevel(logging.ERROR)
logging.getLogger("backoff").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.WARNING)


def test_vector_query(function_name: str):
    """测试向量化数据库查询功能"""
    print(f"🔍 查询函数: {function_name}")
    print("=" * 60)
    
    try:
        # 初始化RAG系统
        rag = EnhancedQNXRAG()
        
        # 检查系统状态
        stats = rag.get_collection_stats()
        print(f"📊 数据库状态: {stats['status']}")
        print(f"📊 总函数数: {stats.get('total_functions', 0)}")
        
        if stats['status'] != 'ready':
            print("❌ 向量数据库未就绪")
            return
        
        # 1. 精确查找
        print(f"\n1️⃣ 精确查找: {function_name}")
        result = rag.get_function_by_name(function_name)
        
        if result:
            print("✅ 找到函数!")
            print(f"   函数名: {result['function_name']}")
            print(f"   HTML长度: {len(result['html_content'])} 字符")
            print(f"   URL: {result['metadata'].get('url', 'N/A')}")
            print(f"   内容类型: {result['metadata'].get('content_type', 'N/A')}")
            
            # 显示HTML内容预览
            html_preview = result['html_content'][:500] + "..." if len(result['html_content']) > 500 else result['html_content']
            print(f"\n   HTML预览:\n   {html_preview}")
            
        else:
            print("❌ 未找到该函数")
            return
        
        # 2. 相似性搜索
        print(f"\n2️⃣ 相似性搜索 (Top 5):")
        similar_results = rag.search_similar_functions(function_name, top_k=5)
        
        if similar_results:
            for i, sim_result in enumerate(similar_results, 1):
                print(f"   {i}. {sim_result['function_name']} (相似度: {sim_result['similarity_score']:.3f})")
        else:
            print("   没有找到相似函数")
        
        # 3. 提取JSON信息
        print(f"\n3️⃣ JSON信息提取:")
        extractor = QNXJSONExtractor()
        json_info = extractor.extract_function_json(function_name)
        
        if json_info:
            print("✅ JSON提取成功!")
            print(f"   函数签名: {json_info.get('signature', 'N/A')}")
            print(f"   参数数量: {len(json_info.get('parameters', []))}")
            print(f"   头文件数量: {len(json_info.get('headers', []))}")
            print(f"   返回类型: {json_info.get('return_type', 'N/A')}")
            
            # 显示参数信息
            if json_info.get('parameters'):
                print("   参数信息:")
                for param in json_info['parameters'][:3]:  # 显示前3个参数
                    print(f"     - {param.get('name', 'N/A')}: {param.get('type', 'N/A')}")
            
            # 显示头文件信息
            if json_info.get('headers'):
                print("   头文件:")
                for header in json_info['headers'][:3]:  # 显示前3个头文件
                    print(f"     - {header.get('filename', 'N/A')}")
            
            # 保存详细JSON到文件
            output_file = f"{function_name}_detail.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(json_info, f, indent=2, ensure_ascii=False)
            print(f"   详细信息已保存到: {output_file}")
            
        else:
            print("❌ JSON提取失败")
        
        # 4. 向量信息
        print(f"\n4️⃣ 向量化信息:")
        
        # 尝试获取向量(通过相似性搜索结果)
        if similar_results and similar_results[0]['function_name'] == function_name:
            print("✅ 向量化成功")
            print(f"   向量维度: 预计1536维 (OpenAI embedding)")
            print(f"   存储ID: {function_name}")
        else:
            print("❌ 未找到向量信息")
        
    except Exception as e:
        logger.error(f"查询失败: {e}")
        print(f"❌ 查询过程中出现错误: {e}")


def interactive_query():
    """交互式查询模式"""
    print("🚀 向量化数据库查询测试工具")
    print("输入函数名查询，输入 'quit' 退出")
    print("-" * 60)
    
    while True:
        try:
            function_name = input("\n请输入函数名: ").strip()
            
            if function_name.lower() in ['quit', 'exit', 'q']:
                print("👋 再见!")
                break
            
            if not function_name:
                print("请输入有效的函数名")
                continue
            
            test_vector_query(function_name)
            print("\n" + "=" * 60)
            
        except KeyboardInterrupt:
            print("\n👋 再见!")
            break
        except Exception as e:
            print(f"❌ 输入处理错误: {e}")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="测试向量化数据库查询")
    parser.add_argument("--function", "-f", help="要查询的函数名")
    parser.add_argument("--interactive", "-i", action="store_true", help="交互式模式")
    
    args = parser.parse_args()
    
    if args.function:
        # 单次查询模式
        test_vector_query(args.function)
    elif args.interactive:
        # 交互式模式
        interactive_query()
    else:
        # 默认交互式模式
        interactive_query()


if __name__ == "__main__":
    main()