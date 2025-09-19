#!/usr/bin/env python3
"""
Basic QNX MCP Server Test
Tests QNX MCP server functionality when data is available
"""

import sys
import os

# Add src directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir) 
src_dir = os.path.join(parent_dir, 'src')
sys.path.insert(0, src_dir)

def test_qnx_mcp_imports():
    """Test if QNX MCP server can be imported"""
    print("=== Testing QNX MCP Server Imports ===")
    
    try:
        from qnx_mcp.qnx_mcp_server import QNXFunctionsMCPServer
        print("✅ QNXFunctionsMCPServer 导入成功")
        return True
    except ImportError as e:
        print(f"❌ QNXFunctionsMCPServer 导入失败: {e}")
        return False

def test_qnx_data_availability():
    """Test if QNX data is available"""
    print("\n=== Testing QNX Data Availability ===")
    
    # Check if data directories exist
    data_dir = os.path.join(os.path.dirname(current_dir), 'data')
    processed_dir = os.path.join(data_dir, 'processed_functions')
    cache_dir = os.path.join(data_dir, 'qnx_web_cache')
    chroma_dir = os.path.join(data_dir, 'chroma_db')
    
    checks = [
        ("Data directory", os.path.exists(data_dir)),
        ("Processed functions", os.path.exists(processed_dir)),
        ("Web cache", os.path.exists(cache_dir)),
        ("ChromaDB", os.path.exists(chroma_dir)),
    ]
    
    for name, exists in checks:
        print(f"{'✅' if exists else '❌'} {name}: {'存在' if exists else '不存在'}")
    
    # Count files
    if os.path.exists(cache_dir):
        cache_count = len([f for f in os.listdir(cache_dir) if f.endswith('.html')])
        print(f"📄 缓存的HTML文件: {cache_count}")
    
    if os.path.exists(processed_dir):
        processed_count = len([f for f in os.listdir(processed_dir) if f.endswith('.json')])
        print(f"📄 处理的JSON文件: {processed_count}")
    
    return all(exists for _, exists in checks)

def test_qnx_mcp_initialization():
    """Test QNX MCP server initialization"""
    print("\n=== Testing QNX MCP Server Initialization ===")
    
    try:
        from qnx_mcp.qnx_mcp_server import QNXFunctionsMCPServer
        
        # Try to initialize (this might fail if data is not ready)
        server = QNXFunctionsMCPServer()
        print("✅ QNX MCP Server 初始化成功")
        return True
    except Exception as e:
        print(f"❌ QNX MCP Server 初始化失败: {e}")
        print("💡 这是正常的，如果QNX数据还在处理中")
        return False

def main():
    """Run all basic tests"""
    print("🧪 QNX MCP Server Basic Tests")
    print("=" * 50)
    
    tests = [
        ("Import Test", test_qnx_mcp_imports),
        ("Data Availability", test_qnx_data_availability),
        ("Server Initialization", test_qnx_mcp_initialization),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"\n❌ {test_name} 测试异常: {e}")
            results[test_name] = False
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 测试结果汇总:")
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {test_name}: {status}")
    
    print(f"\n总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print("🎉 所有测试通过！可以使用 interactive_mcp_test.py")
    else:
        print("⚠️  部分测试失败 - QNX数据可能还在处理中")
        print("💡 等待 QNX batch processor 完成后再试")

if __name__ == "__main__":
    main()