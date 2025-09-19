# QNX MCP Module

QNX Model Context Protocol (MCP) module provides comprehensive QNX function information processing pipeline. This module handles the complete workflow from web crawling QNX documentation to storing enhanced function data in vector databases.

## 🎯 Overview

The QNX MCP module implements a 4-stage pipeline:

```
Web Crawling → JSON Extraction → GDB Enhancement → Vector Storage
```

Each stage can be run independently or as part of the complete pipeline.

## 📁 Module Structure

```
src/qnx_mcp/
├── qnx_web_crawler.py          # Stage 1: Web crawling
├── claude_json_extractor.py    # Stage 2: JSON extraction  
├── qnx_gdb_type_enhancer.py    # Stage 3: GDB enhancement
├── hybrid_vectorizer.py        # Stage 4: Vector storage
├── qnx_step_processor.py       # Multi-step pipeline controller
├── qnx_batch_processor.py      # Legacy batch processor
├── qnx_mcp_server.py          # MCP server implementation
└── __init__.py                # Module exports
```

## 🚀 Pipeline Stages

### Stage 1: Web Crawling (`qnx_web_crawler.py`)

Crawls QNX documentation websites to extract function information.

**Features:**
- Parallel crawling with configurable workers
- Smart caching to avoid re-crawling
- Rate limiting and retry mechanisms
- Content filtering and validation

**Usage:**
```python
from qnx_mcp import QNXWebCrawler

crawler = QNXWebCrawler("config.json")
functions = crawler.crawl_all_functions()
```

**Configuration:**
```json
{
  "crawler_settings": {
    "max_workers": 8,
    "delay_range": [0.5, 1.0],
    "timeout": 30,
    "cache_dir": "./data/qnx_web_cache"
  }
}
```

### Stage 2: JSON Extraction (`claude_json_extractor.py`)

Converts raw HTML content to structured JSON using Claude API.

**Features:**
- Claude Haiku model for fast extraction
- Structured function information parsing
- Parameter type analysis
- Header and library information extraction

**Usage:**
```python
from qnx_mcp import ClaudeJSONExtractor

extractor = ClaudeJSONExtractor("config.json")
function_info = extractor.extract_function_info(html_content, function_name)
```

**Output Format:**
```json
{
  "name": "malloc",
  "synopsis": "void *malloc(size_t size)",
  "description": "Allocates memory...",
  "parameters": [
    {
      "name": "size",
      "type": "size_t",
      "description": "Number of bytes to allocate",
      "is_pointer": false,
      "is_const": false,
      "is_optional": false
    }
  ],
  "return_type": "void *",
  "headers": [...],
  "libraries": ["libc"],
  "classification": "ANSI, POSIX 1003.1"
}
```

### Stage 3: GDB Enhancement (`qnx_gdb_type_enhancer.py`)

Enhances function data with detailed type information using QNX GDB.

**Features:**
- Single-threaded and multi-threaded processing
- QNX libc.so.4 loading for accurate type information
- Struct/union field analysis
- Type size and classification

**Usage:**
```bash
# Single-threaded test
python src/qnx_mcp/qnx_gdb_type_enhancer.py --test

# Multi-threaded enhancement
python src/qnx_mcp/qnx_gdb_type_enhancer.py \
  --input data/processed_functions/extracted_functions.json \
  --output data/processed_functions/enhanced_functions.json \
  --workers 6
```

**Enhanced Output:**
```json
{
  "name": "acl",
  "type": "acl_t",
  "info": {
    "ptype_result": "type = struct _acl {\n    int current;\n    int max;\n    struct _acl_posix posix;\n} *",
    "type_classification": {
      "is_struct": true,
      "is_pointer": true,
      "is_union": false,
      "is_enum": false,
      "is_array": false
    },
    "fields": [],
    "size": null
  },
  "enhanced": true
}
```

### Stage 4: Vector Storage (`hybrid_vectorizer.py`)

Creates and stores vector embeddings in ChromaDB for semantic search.

**Features:**
- Hybrid OpenAI + local embedding models
- Efficient batch processing
- Metadata storage for filtering
- Semantic similarity search

**Usage:**
```python
from qnx_mcp import HybridVectorizer

vectorizer = HybridVectorizer("config.json")
vectorizer.vectorize_functions_batch(functions_data)
```

**Configuration:**
```json
{
  "vectorizer_settings": {
    "embedding_model": "text-embedding-3-small",
    "chunk_size": 100,
    "collection_name": "qnx_functions",
    "persist_directory": "./data/chroma_db"
  }
}
```

## 🔧 Complete Pipeline Usage

### Option 1: Step-by-Step Processing

```bash
# Step 1: JSON extraction only (skip crawling and GDB)
source .env && python src/qnx_mcp/qnx_step_processor.py \
  --skip-discover --skip-crawl --skip-gdb

# Step 2: GDB enhancement
python src/qnx_mcp/qnx_gdb_type_enhancer.py \
  --input data/processed_functions/extracted_functions.json \
  --output data/processed_functions/enhanced_functions.json \
  --workers 6

# Step 3: Vector storage
python src/qnx_mcp/hybrid_vectorizer.py \
  --input data/processed_functions/enhanced_functions.json
```

### Option 2: Automated Pipeline

```python
from qnx_mcp import QNXStepProcessor

processor = QNXStepProcessor("config.json")
processor.run_pipeline()
```

## 📊 Performance Metrics

### Typical Processing Times
- **Web Crawling**: ~2-3 hours for 1650+ functions (8 workers)
- **JSON Extraction**: ~45 minutes for 1650+ functions (Claude API)
- **GDB Enhancement**: ~8 minutes for 1618 functions (6 workers)
- **Vector Storage**: ~5 minutes for 1618 functions

### Output Sizes
- **Raw HTML Cache**: ~500MB
- **JSON Functions**: ~3MB (1618 functions)
- **GDB Enhanced**: ~4.3MB (126K+ lines)
- **Vector Database**: ~50MB

## ⚙️ Configuration

### Required Environment Variables
```bash
OPENAI_API_KEY=your_openai_key      # For embeddings
CLAUDE_API_KEY=your_claude_key      # For JSON extraction
```

### config.json Structure
```json
{
  "qnx_system": {
    "root_path": "/path/to/qnx700",
    "gdb_executable": "ntox86_64-gdb"
  },
  "claude_api": {
    "endpoint": "http://your-claude-server:3000/api",
    "model": "claude-3-haiku"
  },
  "ai_settings": {
    "openai": {
      "embedding_model": "text-embedding-3-small"
    }
  },
  "crawler_settings": {
    "max_workers": 8,
    "delay_range": [0.5, 1.0]
  },
  "vectorizer_settings": {
    "collection_name": "qnx_functions",
    "persist_directory": "./data/chroma_db"
  }
}
```

## 🔍 Data Flow

```
QNX Docs Website
       ↓ (crawl)
   HTML Content
       ↓ (extract)
   JSON Functions
       ↓ (enhance)
 GDB-Enhanced JSON
       ↓ (vectorize)
   ChromaDB Storage
       ↓ (query)
   MCP Server API
```

## 🎯 Output Files

```
data/
├── qnx_web_cache/                    # Cached HTML content
├── processed_functions/
│   ├── extracted_functions.json     # Stage 2 output
│   └── enhanced_functions.json      # Stage 3 output
└── chroma_db/                        # Stage 4 output
    ├── chroma.sqlite3
    └── [uuid-collections]/
```

## 🧪 Testing

```bash
# Test individual components
python src/qnx_mcp/qnx_web_crawler.py --test
python src/qnx_mcp/qnx_gdb_type_enhancer.py --test
python src/qnx_mcp/hybrid_vectorizer.py --test

# Test complete pipeline with limited functions
python src/qnx_mcp/qnx_step_processor.py --max-functions 10
```

## 🚨 Common Issues

### GDB Enhancement Fails
- Ensure QNX SDK is properly installed
- Check `qnx_system.root_path` in config
- Verify `ntox86_64-gdb` is in PATH

### Claude API Errors
- Check `CLAUDE_API_KEY` environment variable
- Verify Claude server endpoint is accessible
- Monitor rate limits

### Vector Storage Issues  
- Ensure sufficient disk space for ChromaDB
- Check OpenAI API key for embeddings
- Verify write permissions in output directory

## 📚 API Reference

See individual module docstrings for detailed API documentation:
- `QNXWebCrawler` - Web crawling functionality
- `ClaudeJSONExtractor` - JSON extraction from HTML
- `QNXGDBTypeEnhancer` - GDB type enhancement
- `MultiThreadGDBEnhancer` - Multi-threaded GDB processing
- `HybridVectorizer` - Vector embedding and storage
- `QNXStepProcessor` - Pipeline orchestration

## 🔗 Integration

This module integrates with:
- **QNX MCP Server**: Provides function lookup API
- **Glue Code Generator**: Consumes enhanced function data
- **Vector Search**: Enables semantic function discovery