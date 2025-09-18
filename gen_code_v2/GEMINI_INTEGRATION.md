# Gemini集成说明

## 概述

本项目现已集成Gemini AI进行向量化和JSON数据提取，提供更高效的QNX函数文档处理能力。

## 新增组件

### 1. 优化的Gemini向量化器 (`optimized_gemini_vectorizer.py`)

**特性:**
- 使用 `gemini-embedding-001` 模型进行向量化
- 支持并行处理和批量embedding
- 自动错误重试和指数退避
- 高效的ChromaDB存储

**主要功能:**
```python
from optimized_gemini_vectorizer import OptimizedGeminiVectorizer

# 初始化
vectorizer = OptimizedGeminiVectorizer()

# 向量化文档
documents = [{"id": "func1", "content": "函数描述", "metadata": {...}}]
stats = vectorizer.vectorize_documents(documents)

# 查询相似文档
results = vectorizer.query_similar("查询文本", n_results=5)
```

### 2. Gemini 2.5 Flash JSON提取器 (`gemini_flash_json_extractor.py`)

**特性:**
- 使用 `gemini-2.5-flash` 模型进行JSON提取
- 结构化输出，强制JSON格式
- 智能HTML内容清理
- 标准化的QNX函数信息格式

**主要功能:**
```python
from gemini_flash_json_extractor import GeminiFlashJSONExtractor

# 初始化
extractor = GeminiFlashJSONExtractor()

# 从HTML提取函数信息
function_info = extractor.extract_function_info(html_content, "function_name")

# 批量提取
html_files = [{"content": html, "function_name": "func"}]
results = extractor.extract_batch_functions(html_files)
```

### 3. 集成QNX系统 (`integrated_qnx_system.py`)

**特性:**
- 结合向量化和JSON提取
- 智能缓存机制
- 并行处理支持
- 完整的统计和监控

**主要功能:**
```python
from integrated_qnx_system import IntegratedQNXSystem

# 初始化集成系统
system = IntegratedQNXSystem()

# 处理单个函数
result = system.process_single_function(html_content, "function_name")

# 批量处理
tasks = [ProcessingTask("file.html", "func_name")]
results = system.process_batch_functions(tasks)

# 查询函数
query_results = system.query_functions("查询文本")

# 获取函数详情
details = system.get_function_details("function_name")
```

## 配置说明

### 环境变量设置
```bash
# 设置Gemini API密钥
export GEMINI_API_KEY="your_gemini_api_key"
```

### 配置文件 (`config.json`)

已更新配置支持Gemini集成：

```json
{
  "ai_settings": {
    "provider": "gemini",
    "gemini": {
      "api_key_env": "GEMINI_API_KEY",
      "model": "gemini-2.5-flash",
      "embedding_model": "embedding-001",
      "max_tokens": 4000,
      "temperature": 0.1,
      "batch_size": 32
    }
  }
}
```

## 性能优化

### 1. 向量化优化
- **并行处理**: 支持多线程并行embedding
- **批量处理**: 优化的批量大小 (32)
- **错误重试**: 指数退避重试策略
- **速率限制**: 防止API限制

### 2. JSON提取优化
- **强制JSON输出**: 使用 `response_mime_type="application/json"`
- **内容清理**: 智能HTML清理，减少token使用
- **结构化提示**: 优化的提示模板

### 3. 缓存机制
- **智能缓存**: 基于内容哈希的缓存
- **快速查找**: 避免重复处理
- **缓存清理**: 自动过期清理

## 使用流程

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 设置环境变量
```bash
export GEMINI_API_KEY="your_api_key"
```

### 3. 基本使用
```python
# 导入集成系统
from integrated_qnx_system import IntegratedQNXSystem

# 初始化
system = IntegratedQNXSystem()

# 处理HTML文档
with open("qnx_function.html", "r") as f:
    html_content = f.read()

result = system.process_single_function(html_content, "sprintf")

# 查询函数
results = system.query_functions("字符串格式化")

# 获取统计信息
stats = system.get_system_stats()
```

### 4. 批量处理
```python
from integrated_qnx_system import ProcessingTask

# 准备任务列表
tasks = [
    ProcessingTask("html/sprintf.html", "sprintf", priority=1),
    ProcessingTask("html/printf.html", "printf", priority=1),
]

# 批量处理
results = system.process_batch_functions(tasks, max_workers=4)

# 分析结果
successful = [r for r in results if r.success]
print(f"成功处理: {len(successful)}/{len(tasks)}")
```

## 监控和统计

### 系统统计信息
```python
stats = system.get_system_stats()
print(f"总处理数: {stats['total_processed']}")
print(f"JSON提取成功: {stats['json_extracted']}")
print(f"向量化成功: {stats['vectorized']}")
print(f"缓存命中: {stats['cached_hits']}")
print(f"错误数: {stats['errors']}")
```

### 性能监控
- 处理时间统计
- 成功率监控
- 缓存效率
- API使用统计

## 错误处理

### 常见错误及解决方案

1. **API密钥错误**
   ```
   错误: 请设置环境变量 GEMINI_API_KEY
   解决: export GEMINI_API_KEY="your_key"
   ```

2. **JSON解析失败**
   ```
   错误: JSON解析失败
   解决: 检查输入HTML格式，使用更清晰的函数文档
   ```

3. **向量化失败**
   ```
   错误: 获取embedding失败
   解决: 检查网络连接和API配额
   ```

## 最佳实践

### 1. 批量处理
- 使用批量处理提高效率
- 合理设置并发数 (建议4-8)
- 按优先级排序任务

### 2. 缓存管理
- 定期清理过期缓存
- 监控缓存命中率
- 备份重要缓存文件

### 3. 错误处理
- 实现重试机制
- 记录详细错误日志
- 监控API使用情况

## 扩展功能

### 1. 自定义提取模板
可以修改JSON提取提示模板来适应不同的文档格式。

### 2. 多模型支持
可以轻松添加其他AI模型的支持。

### 3. 数据导出
支持将处理结果导出为各种格式 (JSON, CSV, XML等)。

## 故障排除

### 调试模式
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### 性能分析
```python
# 获取详细统计
stats = system.get_system_stats()
vectorizer_stats = stats['vectorizer']
print(f"向量化处理时间: {vectorizer_stats['processing_time']}")
```

### 缓存清理
```python
# 清理30天前的缓存
system.cleanup_cache(max_age_days=30)
```