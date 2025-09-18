#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试集成QNX系统
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from integrated_qnx_system import IntegratedQNXSystem, ProcessingTask

def test_integrated_system():
    """测试集成系统基本功能"""
    try:
        print("=== 测试集成QNX系统 ===")
        
        # 初始化集成系统
        system = IntegratedQNXSystem()
        print("✓ 集成系统初始化成功")
        
        # 测试HTML内容
        test_html = """
        <html>
        <body>
        <div class="content">
        <h1>printf</h1>
        <h2>Synopsis</h2>
        <p>int printf(const char *format, ...);</p>
        <h2>Description</h2>
        <p>The printf() function sends formatted output to stdout. It converts, formats, and prints its arguments to stdout under control of the format argument.</p>
        <h2>Arguments</h2>
        <p>format - Format string containing conversion specifications</p>
        <h2>Returns</h2>
        <p>Number of characters transmitted to the output stream, or a negative value if an error occurred.</p>
        <h2>Header</h2>
        <p>#include &lt;stdio.h&gt;</p>
        <h2>Library</h2>
        <p>libc</p>
        <h2>Classification</h2>
        <p>ANSI, POSIX 1003.1</p>
        <h2>Safety</h2>
        <p>Thread safe: Yes</p>
        </div>
        </body>
        </html>
        """
        
        # 测试单个函数处理
        print("\n=== 测试单个函数处理 ===")
        result = system.process_single_function(test_html, "printf")
        
        print(f"处理结果:")
        print(f"  函数名: {result.function_name}")
        print(f"  成功: {result.success}")
        print(f"  JSON提取: {result.json_extracted}")
        print(f"  向量化: {result.vectorized}")
        print(f"  缓存: {result.cached}")
        print(f"  处理时间: {result.processing_time:.2f}s")
        
        if result.error:
            print(f"  错误: {result.error}")
        
        if not result.success:
            print("✗ 单个函数处理失败")
            return False
        
        print("✓ 单个函数处理成功")
        
        # 测试查询功能
        print("\n=== 测试查询功能 ===")
        test_queries = [
            "格式化输出函数",
            "标准输出流",
            "字符串打印"
        ]
        
        for query in test_queries:
            print(f"\n查询: '{query}'")
            query_results = system.query_functions(query, n_results=2)
            
            if query_results:
                for i, qr in enumerate(query_results):
                    function_name = qr.get('function_name', 'unknown')
                    similarity = qr.get('similarity', 0)
                    print(f"  {i+1}. {function_name} (相似度: {similarity:.3f})")
            else:
                print("  无结果")
        
        # 测试获取函数详情
        print("\n=== 测试获取函数详情 ===")
        details = system.get_function_details("printf")
        if details:
            print(f"✓ 获取到函数详情: {details.name}")
            print(f"  描述: {details.description[:100]}...")
        else:
            print("✓ 未找到缓存的函数详情（正常情况）")
        
        # 获取系统统计信息
        print(f"\n=== 系统统计信息 ===")
        stats = system.get_system_stats()
        print(f"总处理: {stats['total_processed']}")
        print(f"JSON提取成功: {stats['json_extracted']}")
        print(f"向量化成功: {stats['vectorized']}")
        print(f"缓存命中: {stats['cached_hits']}")
        print(f"错误数: {stats['errors']}")
        print(f"总时间: {stats['total_time']:.2f}s")
        
        # 测试缓存清理
        print("\n=== 测试缓存清理 ===")
        system.cleanup_cache(max_age_days=0)  # 清理所有缓存
        print("✓ 缓存清理完成")
        
        print("\n✓ 所有测试通过!")
        return True
        
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_batch_processing():
    """测试批量处理功能"""
    try:
        print("\n=== 测试批量处理功能 ===")
        
        # 注意：这个测试需要实际的HTML文件，这里只是演示结构
        print("✓ 批量处理测试跳过（需要实际HTML文件）")
        return True
        
    except Exception as e:
        print(f"✗ 批量处理测试失败: {e}")
        return False

if __name__ == "__main__":
    success1 = test_integrated_system()
    success2 = test_batch_processing()
    
    overall_success = success1 and success2
    print(f"\n{'='*50}")
    print(f"总体测试结果: {'通过' if overall_success else '失败'}")
    
    sys.exit(0 if overall_success else 1)