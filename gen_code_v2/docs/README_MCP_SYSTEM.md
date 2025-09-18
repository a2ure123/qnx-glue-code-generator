# QNX函数文档MCP系统

## 概述

这是一个基于MCP（Model Context Protocol）的QNX函数文档系统，实现了：
- **函数名作为Key的RAG系统**：使用函数名作为唯一标识符，存储完整HTML文档
- **智能HTML内容解析**：从HTML文档中提取结构化的函数信息
- **标准JSON格式输出**：提供函数参数、头文件等信息的JSON格式

## 系统架构

```
┌─────────────────────┐    ┌──────────────────────┐    ┌─────────────────────┐
│   QNX HTML文档      │    │   函数名RAG系统      │    │   JSON信息提取器    │
│                     │───▶│  (ChromaDB)          │───▶│                     │
│ • 完整HTML内容      │    │ • 函数名 → HTML内容  │    │ • 参数解析          │
│ • 官方文档源        │    │ • 向量化搜索         │    │ • 头文件提取        │
└─────────────────────┘    └──────────────────────┘    └─────────────────────┘
                                      │
                                      ▼
                           ┌──────────────────────┐
                           │    MCP服务器         │
                           │                      │
                           │ • get_qnx_function_info
                           │ • list_qnx_functions │
                           │ • batch_get_functions│
                           │ • get_function_html  │
                           └──────────────────────┘
```

## 核心组件

### 1. Enhanced QNX RAG (`enhanced_qnx_rag.py`)
- **函数名作为Key**：直接使用函数名作为ChromaDB的ID
- **精确查找**：通过函数名直接获取HTML内容
- **相似性搜索**：基于函数名向量进行相似函数推荐
- **批量操作**：支持批量获取多个函数

### 2. JSON信息提取器 (`qnx_json_extractor.py`)
- **HTML解析**：使用BeautifulSoup解析HTML文档
- **结构化提取**：提取函数签名、参数、头文件等信息
- **标准格式**：输出标准的JSON格式数据

### 3. MCP服务器 (`qnx_function_mcp_server.py`)
- **标准MCP接口**：符合MCP协议规范
- **多种工具**：提供不同粒度的函数信息获取
- **资源管理**：管理函数列表和常用函数信息

## 安装和设置

### 环境要求
```bash
python >= 3.8
```

### 安装依赖
```bash
pip install -r requirements.txt
```

主要依赖：
- `chromadb` - 向量数据库
- `openai` - OpenAI API（用于向量化）
- `beautifulsoup4` - HTML解析
- `requests` - HTTP请求
- `mcp` - MCP协议支持

### 环境变量
```bash
export OPENAI_API_KEY="your_openai_api_key"  # 用于向量化
```

## 快速开始

### 1. 构建RAG索引
```bash
# 构建基础索引（50个函数）
python enhanced_qnx_rag.py --build --max-functions 50

# 构建完整索引
python enhanced_qnx_rag.py --build

# 重建索引
python enhanced_qnx_rag.py --rebuild
```

### 2. 测试系统
```bash
# 运行综合测试
python test_mcp_system.py

# 测试特定函数
python test_mcp_system.py --functions sprintf malloc printf

# 构建并测试
python test_mcp_system.py --build-rag --max-functions 20
```

### 3. 使用JSON提取器
```bash
# 提取单个函数
python qnx_json_extractor.py --function sprintf

# 批量提取
python qnx_json_extractor.py --batch sprintf malloc printf

# 保存到文件
python qnx_json_extractor.py --function sprintf --output sprintf.json
```

### 4. 启动MCP服务器
```bash
# 测试模式
python qnx_function_mcp_server.py --test

# MCP服务器模式（用于与Claude等模型集成）
python qnx_function_mcp_server.py
```

## MCP工具说明

### `get_qnx_function_info`
获取函数的完整结构化信息（JSON格式）

**输入**：
- `function_name` (string): 函数名称

**输出**：包含以下信息的JSON：
```json
{
  "function_name": "sprintf",
  "signature": "int sprintf(char *s, const char *format, ...)",
  "description": "格式化字符串并写入缓冲区",
  "parameters": [
    {
      "name": "s",
      "type": "char",
      "description": "目标缓冲区",
      "is_pointer": true,
      "is_const": false
    }
  ],
  "headers": [
    {
      "filename": "stdio.h",
      "is_system": true
    }
  ],
  "return_type": "int",
  "return_description": "写入的字符数",
  "url": "https://www.qnx.com/developers/docs/...",
  "examples": ["..."]
}
```

### `list_qnx_functions`
列出可用的QNX函数名

**输入**：
- `limit` (integer, 可选): 返回函数数量限制，默认50

**输出**：
```json
{
  "available_functions": ["sprintf", "malloc", "printf", ...],
  "total_count": 50,
  "limit": 50,
  "rag_status": "ready",
  "total_in_rag": 1500
}
```

### `batch_get_qnx_functions`
批量获取多个函数的信息

**输入**：
- `function_names` (array): 函数名列表

**输出**：
```json
{
  "batch_results": {
    "sprintf": { ... },
    "malloc": { ... }
  },
  "summary": {
    "requested": 2,
    "successful": 2,
    "failed": 0,
    "failed_functions": []
  }
}
```

### `get_qnx_function_html`
获取函数的原始HTML文档

**输入**：
- `function_name` (string): 函数名称

**输出**：
```json
{
  "function_name": "sprintf",
  "html_content": "<html>...",
  "metadata": {
    "url": "...",
    "function_name": "sprintf"
  },
  "source": "enhanced_rag"
}
```

## 使用示例

### Python脚本中使用
```python
from enhanced_qnx_rag import EnhancedQNXRAG
from qnx_json_extractor import QNXJSONExtractor

# 初始化系统
rag = EnhancedQNXRAG()
extractor = QNXJSONExtractor()

# 获取函数信息
function_info = extractor.extract_function_json("sprintf")
print(json.dumps(function_info, indent=2))

# 批量获取
batch_info = extractor.batch_extract_functions(["sprintf", "malloc", "printf"])
```

### 与Claude等大模型集成
1. 启动MCP服务器：
```bash
python qnx_function_mcp_server.py
```

2. 在Claude Code中配置MCP服务器，然后可以：
```
请使用get_qnx_function_info工具获取sprintf函数的详细信息
```

## 性能和优化

### RAG系统优化
- **函数名作为Key**：避免了向量相似性搜索的开销，实现O(1)精确查找
- **缓存机制**：HTML内容本地缓存，减少网络请求
- **批量操作**：支持批量获取，提高效率

### 内存使用
- **按需加载**：只在需要时加载HTML内容
- **ChromaDB持久化**：向量数据持久化存储，避免重复构建

### 网络优化
- **本地缓存**：HTML文档本地缓存，避免重复下载
- **批量请求**：减少HTTP请求次数

## 故障排除

### 常见问题

1. **RAG索引未构建**
```bash
python enhanced_qnx_rag.py --build
```

2. **OpenAI API Key未设置**
```bash
export OPENAI_API_KEY="your_api_key"
```

3. **函数未找到**
   - 检查函数名拼写
   - 确认函数在QNX文档中存在
   - 重新构建RAG索引

4. **HTML解析失败**
   - 检查网络连接
   - 确认QNX文档网站可访问
   - 清理HTML缓存：`rm -rf data/qnx_html_cache/`

### 调试方法
```bash
# 查看RAG状态
python enhanced_qnx_rag.py --verify

# 测试特定函数
python test_mcp_system.py --functions your_function_name

# 详细日志
export PYTHONPATH=. && python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
from qnx_json_extractor import QNXJSONExtractor
extractor = QNXJSONExtractor()
result = extractor.extract_function_json('sprintf')
print(result)
"
```

## 扩展和定制

### 添加新的数据源
1. 在`enhanced_qnx_rag.py`中修改`_discover_all_functions`方法
2. 添加新的HTML解析逻辑

### 自定义JSON格式
1. 修改`qnx_json_extractor.py`中的`QNXFunctionSpec`数据类
2. 更新提取逻辑

### 添加新的MCP工具
1. 在`qnx_function_mcp_server.py`中添加新的`@self.server.call_tool()`方法
2. 实现相应的逻辑

## 技术细节

### 向量化策略
- 使用OpenAI的`text-embedding-3-small`模型
- 只对函数名进行向量化，不是整个文档内容
- 支持相似性搜索和精确匹配

### HTML解析策略
- 使用BeautifulSoup进行HTML解析
- 基于QNX文档的HTML结构特点进行信息提取
- 支持多种文档格式和布局

### 数据存储
- ChromaDB作为向量数据库
- 函数名作为唯一ID
- HTML内容作为文档存储
- 元数据包含URL、类型等信息

---

## 许可证
MIT License

## 贡献
欢迎提交Issue和Pull Request！