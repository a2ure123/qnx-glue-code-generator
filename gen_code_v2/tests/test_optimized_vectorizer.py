#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试优化的Gemini向量化器
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from optimized_gemini_vectorizer import OptimizedGeminiVectorizer

def test_vectorizer():
    """测试向量化器基本功能"""
    try:
        print("=== 测试优化Gemini向量化器 ===")
        
        # 初始化向量化器
        vectorizer = OptimizedGeminiVectorizer()
        print("✓ 向量化器初始化成功")
        
        # 测试文档
        test_docs = [
            {
                "id": "sprintf_test",
                "content": "sprintf函数用于格式化字符串输出到缓冲区，参数包括目标缓冲区和格式字符串",
                "metadata": {"function": "sprintf", "type": "stdio", "category": "string"}
            },
            {
                "id": "printf_test", 
                "content": "printf函数用于格式化输出到标准输出流，是C语言标准库函数",
                "metadata": {"function": "printf", "type": "stdio", "category": "output"}
            },
            {
                "id": "malloc_test",
                "content": "malloc函数用于动态内存分配，返回分配内存的指针",
                "metadata": {"function": "malloc", "type": "stdlib", "category": "memory"}
            }
        ]
        
        # 执行向量化
        print("开始向量化测试文档...")
        stats = vectorizer.vectorize_documents(test_docs, reset_db=True)
        print(f"✓ 向量化完成: {stats}")
        
        # 测试查询
        print("\n=== 测试查询功能 ===")
        test_queries = [
            "字符串格式化函数",
            "内存分配",
            "标准输出",
            "缓冲区操作"
        ]
        
        for query in test_queries:
            print(f"\n查询: '{query}'")
            results = vectorizer.query_similar(query, n_results=2)
            
            if results:
                for i, result in enumerate(results):
                    similarity = result.get('similarity', 0)
                    metadata = result.get('metadata', {})
                    function_name = metadata.get('function', 'unknown')
                    print(f"  {i+1}. {function_name} (相似度: {similarity:.3f})")
            else:
                print("  无结果")
        
        # 获取统计信息
        print(f"\n=== 统计信息 ===")
        stats = vectorizer.get_stats()
        print(f"总处理: {stats['total_processed']}")
        print(f"成功向量化: {stats['successful_embeddings']}")
        print(f"失败向量化: {stats['failed_embeddings']}")
        print(f"处理时间: {stats['processing_time']:.2f}s")
        
        print("\n✓ 所有测试通过!")
        return True
        
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_vectorizer()
    sys.exit(0 if success else 1)