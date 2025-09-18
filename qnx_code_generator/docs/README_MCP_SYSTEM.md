# QNX Function Documentation MCP System

## Overview

This is a QNX function documentation system based on MCP (Model Context Protocol) that implements:
- **Function Name as Key RAG System**: Uses function names as unique identifiers to store complete HTML documents
- **Intelligent HTML Content Parsing**: Extracts structured function information from HTML documents
- **Standard JSON Format Output**: Provides JSON format for function parameters, header files, and other information

## System Architecture

```
┌─────────────────────┐    ┌──────────────────────┐    ┌─────────────────────┐
│   QNX HTML Docs     │    │   Function Name RAG  │    │   JSON Info Extractor│
│                     │───▶│  (ChromaDB)          │───▶│                     │
│ • Complete HTML     │    │ • Function → HTML    │    │ • Parameter parsing │
│ • Official docs     │    │ • Vector search      │    │ • Header extraction │
└─────────────────────┘    └──────────────────────┘    └─────────────────────┘
                    │
                    ▼
               ┌──────────────────────┐
               │    MCP Server        │
               │                      │
               │ • get_qnx_function_info
               │ • list_qnx_functions │
               │ • batch_get_functions│
               │ • get_function_html  │
               └──────────────────────┘
```

## Core Components

### 1. Enhanced QNX RAG (`enhanced_qnx_rag.py`)
- **Function name as Key**: Directly uses function name as ChromaDB ID
- **Precise lookup**: Retrieve HTML content directly by function name
- **Similarity search**: Recommend similar functions based on function name vector
- **Batch operations**: Support batch retrieval of multiple functions

### 2. JSON Info Extractor (`qnx_json_extractor.py`)
- **HTML parsing**: Uses BeautifulSoup to parse HTML documents
- **Structured extraction**: Extracts function signature, parameters, header files, etc.
- **Standard format**: Outputs standard JSON format data

### 3. MCP Server (`qnx_function_mcp_server.py`)
- **Standard MCP interface**: Complies with MCP protocol specification
- **Multiple tools**: Provides function info retrieval at different granularity
- **Resource management**: Manages function list and frequently used function info

## Installation and Setup

### Environment Requirements
```bash
python >= 3.8
```

### Install Dependencies
```bash
pip install -r requirements.txt
```

Main dependencies:
- `chromadb` - Vector database
- `openai` - OpenAI API (for vectorization)
- `beautifulsoup4` - HTML parsing
- `requests` - HTTP requests
- `mcp` - MCP protocol support

### Environment Variables
```bash
export OPENAI_API_KEY="your_openai_api_key"  # For vectorization
```

## Quick Start

### 1. Build RAG Index
```bash
# Build base index (50 functions)
python enhanced_qnx_rag.py --build --max-functions 50

# Build full index
python enhanced_qnx_rag.py --build

# Rebuild index
python enhanced_qnx_rag.py --rebuild
```

### 2. Test System
```bash
# Run comprehensive tests
python test_mcp_system.py

# Test specific functions
python test_mcp_system.py --functions sprintf malloc printf

# Build and test
python test_mcp_system.py --build-rag --max-functions 20
```

### 3. Use JSON Extractor
```bash
# Extract single function
python qnx_json_extractor.py --function sprintf

# Batch extract
python qnx_json_extractor.py --batch sprintf malloc printf

# Save to file
python qnx_json_extractor.py --function sprintf --output sprintf.json
```

### 4. Start MCP Server
```bash
# Test mode
python qnx_function_mcp_server.py --test

# MCP server mode (for integration with Claude and other models)
python qnx_function_mcp_server.py
```

## MCP Tool Description

### `get_qnx_function_info`
Get complete structured information of a function (JSON format)

**Input**:
- `function_name` (string): Function name

**Output**: JSON containing the following info:
```json
{
  "function_name": "sprintf",
  "signature": "int sprintf(char *s, const char *format, ...)",
  "description": "Format string and write to buffer",
  "parameters": [
  {
    "name": "s",
    "type": "char",
    "description": "Target buffer",
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
  "return_description": "Number of characters written",
  "url": "https://www.qnx.com/developers/docs/...",
  "examples": ["..."]
}
```

### `list_qnx_functions`
List available QNX function names

**Input**:
- `limit` (integer, optional): Limit on number of functions returned, default 50

**Output**:
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
Batch retrieve information for multiple functions

**Input**:
- `function_names` (array): List of function names

**Output**:
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
Get the original HTML document of a function

**Input**:
- `function_name` (string): Function name

**Output**:
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

## Usage Examples

### Use in Python Script
```python
from enhanced_qnx_rag import EnhancedQNXRAG
from qnx_json_extractor import QNXJSONExtractor

# Initialize system
rag = EnhancedQNXRAG()
extractor = QNXJSONExtractor()

# Get function info
function_info = extractor.extract_function_json("sprintf")
print(json.dumps(function_info, indent=2))

# Batch get
batch_info = extractor.batch_extract_functions(["sprintf", "malloc", "printf"])
```

### Integration with Claude and Other LLMs
1. Start MCP server:
```bash
python qnx_function_mcp_server.py
```

2. Configure MCP server in Claude Code, then you can:
```
Please use the get_qnx_function_info tool to get detailed info for the sprintf function
```

## Performance and Optimization

### RAG System Optimization
- **Function name as Key**: Avoids vector similarity search overhead, enables O(1) precise lookup
- **Caching mechanism**: Local cache of HTML content, reduces network requests
- **Batch operations**: Supports batch retrieval, improves efficiency

### Memory Usage
- **On-demand loading**: Load HTML content only when needed
- **ChromaDB persistence**: Persistent storage of vector data, avoids repeated index building

### Network Optimization
- **Local cache**: HTML documents cached locally, avoids repeated downloads
- **Batch requests**: Reduces number of HTTP requests

## Troubleshooting

### Common Issues

1. **RAG index not built**
```bash
python enhanced_qnx_rag.py --build
```

2. **OpenAI API Key not set**
```bash
export OPENAI_API_KEY="your_api_key"
```

3. **Function not found**
   - Check function name spelling
   - Make sure the function exists in QNX docs
   - Rebuild RAG index

4. **HTML parsing failed**
   - Check network connection
   - Make sure QNX docs website is accessible
   - Clear HTML cache: `rm -rf data/qnx_html_cache/`

### Debugging Methods
```bash
# Check RAG status
python enhanced_qnx_rag.py --verify

# Test specific function
python test_mcp_system.py --functions your_function_name

# Detailed logs
export PYTHONPATH=. && python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
from qnx_json_extractor import QNXJSONExtractor
extractor = QNXJSONExtractor()
result = extractor.extract_function_json('sprintf')
print(result)
"
```

## Extension and Customization

### Add New Data Source
1. Modify `_discover_all_functions` method in `enhanced_qnx_rag.py`
2. Add new HTML parsing logic

### Customize JSON Format
1. Modify `QNXFunctionSpec` dataclass in `qnx_json_extractor.py`
2. Update extraction logic

### Add New MCP Tool
1. Add new `@self.server.call_tool()` method in `qnx_function_mcp_server.py`
2. Implement corresponding logic

## Technical Details

### Vectorization Strategy
- Uses OpenAI's `text-embedding-3-small` model
- Only vectorizes function names, not entire document content
- Supports similarity search and exact match

### HTML Parsing Strategy
- Uses BeautifulSoup for HTML parsing
- Extracts info based on QNX docs HTML structure
- Supports multiple document formats and layouts

### Data Storage
- ChromaDB as vector database
- Function name as unique ID
- HTML content stored as document
- Metadata includes URL, type, etc.

---

## License
MIT License

## Contribution
Issues and Pull Requests are welcome!