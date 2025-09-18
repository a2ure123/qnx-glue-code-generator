# QNX Glue Code Generator Documentation

## Quick Start
- 📚 [Setup Guide](SETUP_GUIDE.md) - Complete installation and configuration guide
- 🚀 [Gemini Integration](GEMINI_INTEGRATION.md) - Using Gemini AI for vectorization and JSON extraction

## System Documentation  
- 🏗️ [Architecture](architecture.md) - System architecture and design overview
- 🔧 [MCP System](README_MCP_SYSTEM.md) - Legacy MCP system documentation
- 📝 [Scripts](SCRIPTS.md) - Utility scripts documentation

## Core Components

### Gemini-based System (Recommended)
- `optimized_gemini_vectorizer.py` - Enhanced vectorization with parallel processing
- `gemini_flash_json_extractor.py` - JSON extraction using Gemini 2.5 Flash  
- `integrated_qnx_system.py` - Combined system integrating both components

### Legacy Components
- `qnx_rag.py` - Basic RAG system
- `qnx_function_mcp_server.py` - MCP server implementation
- `qnx_json_extractor.py` - Basic JSON extractor

## Usage Examples

### Basic Usage
```python
from integrated_qnx_system import IntegratedQNXSystem

# Initialize system
system = IntegratedQNXSystem()

# Process HTML document
result = system.process_single_function(html_content, "sprintf")

# Query functions
results = system.query_functions("string formatting")
```

### Batch Processing
```python
from integrated_qnx_system import ProcessingTask

# Prepare tasks
tasks = [
    ProcessingTask("html/sprintf.html", "sprintf"),
    ProcessingTask("html/printf.html", "printf"),
]

# Process batch
results = system.process_batch_functions(tasks, max_workers=4)
```

## Configuration

Set up your environment variables:
```bash
export GEMINI_API_KEY="your_gemini_api_key"
```

Update `config.json` for system settings:
```json
{
  "ai_settings": {
    "gemini": {
      "model": "gemini-2.5-flash",
      "embedding_model": "embedding-001",
      "batch_size": 32
    }
  }
}
```

## Testing

Run tests to verify system functionality:
```bash
# Test vectorizer
python tests/test_optimized_vectorizer.py

# Test JSON extractor  
python tests/test_flash_json_extractor.py

# Test integrated system
python tests/test_integrated_system.py
```