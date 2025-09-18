# QNX Gemini集成系统设置指南

## 快速开始

### 1. 环境准备

```bash
# 安装依赖
pip install -r requirements.txt

# 复制环境变量模板
cp .env.example .env

# 编辑.env文件，添加你的API密钥
nano .env
```

### 2. API密钥配置

**获取Gemini API密钥:**
1. 访问 [Google AI Studio](https://aistudio.google.com/app/apikey)
2. 创建新的API密钥
3. 将密钥添加到`.env`文件：

```bash
# 在.env文件中添加
GEMINI_API_KEY=your_actual_gemini_api_key_here
```

**或者直接设置环境变量:**
```bash
export GEMINI_API_KEY="your_actual_gemini_api_key_here"
```

### 3. 验证安装

```bash
# 运行基本测试（不需要API密钥）
python -c "
from optimized_gemini_vectorizer import OptimizedGeminiVectorizer
from gemini_flash_json_extractor import GeminiFlashJSONExtractor
from integrated_qnx_system import IntegratedQNXSystem
print('✓ 所有模块导入成功')
"
```

### 4. 运行完整测试（需要API密钥）

```bash
# 测试向量化器
python tests/test_optimized_vectorizer.py

# 测试JSON提取器
python tests/test_flash_json_extractor.py

# 测试集成系统
python tests/test_integrated_system.py
```

## 文件结构

```
gen_code_v2/
├── config.json                    # 主配置文件
├── .env.example                   # 环境变量模板
├── requirements.txt               # Python依赖
├── GEMINI_INTEGRATION.md          # 详细文档
├── SETUP_GUIDE.md                 # 本文件
│
├── 核心模块/
│   ├── optimized_gemini_vectorizer.py    # 优化向量化器
│   ├── gemini_flash_json_extractor.py    # JSON提取器
│   ├── integrated_qnx_system.py          # 集成系统
│   ├── gemini_qnx_rag.py                 # 基础RAG系统
│   └── qnx_function_mcp_server.py        # MCP服务器
│
├── tests/                         # 测试文件
│   ├── test_optimized_vectorizer.py
│   ├── test_flash_json_extractor.py
│   ├── test_integrated_system.py
│   ├── test_core_functions.py
│   ├── test_mcp_system.py
│   └── test_vector_query.py
│
├── scripts/                       # 工具脚本
│   ├── qnx_full_index.py
│   └── analyze_qnx_structure.py
│
├── docs/                          # 文档
└── data/                          # 数据和缓存
    ├── chroma_db/                 # 向量数据库
    ├── qnx_cache/                 # JSON缓存
    └── html_cache/                # HTML缓存
```

## 核心组件

### 1. 优化向量化器 (OptimizedGeminiVectorizer)
- 使用 `gemini-embedding-001` 进行向量化
- 支持批量处理和并行操作
- 自动错误重试机制

### 2. JSON提取器 (GeminiFlashJSONExtractor)
- 使用 `gemini-2.5-flash` 进行JSON提取
- 结构化输出，强制JSON格式
- 智能HTML内容清理

### 3. 集成系统 (IntegratedQNXSystem)
- 结合向量化和JSON提取
- 智能缓存管理
- 完整的统计和监控

## 使用示例

### 基本使用

```python
from integrated_qnx_system import IntegratedQNXSystem

# 初始化系统
system = IntegratedQNXSystem()

# 处理HTML文档
with open("qnx_function.html", "r") as f:
    html_content = f.read()

# 提取和向量化
result = system.process_single_function(html_content, "sprintf")
print(f"处理结果: {result.success}")

# 查询函数
results = system.query_functions("字符串格式化函数")
for result in results:
    print(f"函数: {result['function_name']}, 相似度: {result['similarity']:.3f}")
```

### 批量处理

```python
from integrated_qnx_system import ProcessingTask

# 准备任务
tasks = [
    ProcessingTask("html/sprintf.html", "sprintf", priority=1),
    ProcessingTask("html/printf.html", "printf", priority=1),
]

# 批量处理
results = system.process_batch_functions(tasks, max_workers=4)

# 分析结果
successful = [r for r in results if r.success]
print(f"成功: {len(successful)}/{len(tasks)}")
```

## 故障排除

### 常见问题

1. **模块导入错误**
   ```
   ImportError: No module named 'google.generativeai'
   ```
   解决: `pip install google-generativeai`

2. **API密钥错误**
   ```
   ValueError: 请设置环境变量 GEMINI_API_KEY
   ```
   解决: 检查API密钥设置

3. **ChromaDB权限错误**
   ```
   PermissionError: [Errno 13] Permission denied: './data/chroma_db'
   ```
   解决: `chmod -R 755 ./data`

### 调试模式

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# 现在运行你的代码，会有详细日志
```

### 检查配置

```python
import json
with open('config.json') as f:
    config = json.load(f)
print(json.dumps(config, indent=2))
```

## 性能优化建议

1. **并发设置**: 根据你的硬件调整 `max_workers` (建议4-8)
2. **批量大小**: 调整 `batch_size` (默认32)
3. **缓存管理**: 定期清理过期缓存
4. **API限制**: 注意Gemini API的速率限制

## 下一步

1. 阅读 `GEMINI_INTEGRATION.md` 了解详细功能
2. 运行测试验证系统工作正常
3. 根据需要调整配置参数
4. 开始处理你的QNX文档

## 支持

如果遇到问题，请检查:
1. API密钥是否正确设置
2. 依赖是否完全安装
3. 网络连接是否正常
4. 日志中的错误信息