# 测试文件说明

## 文件列表

### `demo_sprintf_query.py`
- **用途**: 演示QNX RAG系统的预期查询结果
- **功能**: 模拟查询sprintf函数，展示系统会返回什么信息
- **运行**: `python demo_sprintf_query.py`
- **特点**: 无需真实数据库，立即可运行查看效果

### `test_qnx_db.py` 
- **用途**: 测试真实的QNX RAG数据库
- **功能**: 
  - 连接已构建的ChromaDB数据库
  - 测试函数精确查询
  - 测试语义相似度搜索
  - 批量函数测试
  - 交互式查询模式
- **运行**: `python test_qnx_db.py`
- **前提**: 需要先运行索引构建脚本

## 运行顺序

1. 首先运行演示查看预期效果:
   ```bash
   python tests/demo_sprintf_query.py
   ```

2. 等索引构建完成后测试真实数据库:
   ```bash  
   python tests/test_qnx_db.py
   ```

## 测试内容

- ✅ sprintf函数详细信息展示
- ✅ 相似函数推荐
- ✅ 批量函数查询测试
- ✅ 数据库统计信息
- ✅ 交互式查询界面