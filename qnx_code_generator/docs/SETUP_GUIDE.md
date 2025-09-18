# QNX Gemini Integration System Setup Guide

## Quick Start

### 1. Environment Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Copy environment variable template
cp .env.example .env

# Edit .env file and add your API keys
nano .env
```

### 2. API Key Configuration

**Get Gemini API Key:**
1. Visit [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Create a new API key
3. Add the key to `.env` file:

```bash
# Add to .env file
GEMINI_API_KEY=your_actual_gemini_api_key_here
```

**Or set environment variable directly:**
```bash
export GEMINI_API_KEY="your_actual_gemini_api_key_here"
```

### 3. Verify Installation

```bash
# Run basic test (no API key required)
python -c "
from optimized_gemini_vectorizer import OptimizedGeminiVectorizer
from gemini_flash_json_extractor import GeminiFlashJSONExtractor
from integrated_qnx_system import IntegratedQNXSystem
print('✓ All modules imported successfully')
"
```

### 4. Run Complete Tests (API key required)

```bash
# Test vectorizer
python tests/test_optimized_vectorizer.py

# Test JSON extractor
python tests/test_flash_json_extractor.py

# Test integrated system
python tests/test_integrated_system.py
```

## File Structure

```
gen_code_v2/
├── config.json                    # Main configuration file
├── .env.example                   # Environment variable template
├── requirements.txt               # Python dependencies
├── GEMINI_INTEGRATION.md          # Detailed documentation
├── SETUP_GUIDE.md                 # This file
│
├── Core Modules/
│   ├── optimized_gemini_vectorizer.py    # Optimized vectorizer
│   ├── gemini_flash_json_extractor.py    # JSON extractor
│   ├── integrated_qnx_system.py          # Integrated system
│   ├── gemini_qnx_rag.py                 # Basic RAG system
│   └── qnx_function_mcp_server.py        # MCP server
│
├── tests/                         # Test files
│   ├── test_optimized_vectorizer.py
│   ├── test_flash_json_extractor.py
│   ├── test_integrated_system.py
│   ├── test_core_functions.py
│   ├── test_mcp_system.py
│   └── test_vector_query.py
│
├── scripts/                       # Utility scripts
│   ├── qnx_full_index.py
│   └── analyze_qnx_structure.py
│
├── docs/                          # Documentation
└── data/                          # Data and cache
    ├── chroma_db/                 # Vector database
    ├── qnx_cache/                 # JSON cache
    └── html_cache/                # HTML cache
```

## Core Components

### 1. Optimized Vectorizer (OptimizedGeminiVectorizer)
- Uses `gemini-embedding-001` for vectorization
- Supports batch processing and parallel operations
- Automatic error retry mechanism

### 2. JSON Extractor (GeminiFlashJSONExtractor)
- Uses `gemini-2.5-flash` for JSON extraction
- Structured output with enforced JSON format
- Intelligent HTML content cleaning

### 3. Integrated System (IntegratedQNXSystem)
- Combines vectorization and JSON extraction
- Intelligent cache management
- Complete statistics and monitoring

## Usage Examples

### Basic Usage

```python
from integrated_qnx_system import IntegratedQNXSystem

# Initialize system
system = IntegratedQNXSystem()

# Process HTML document
with open("qnx_function.html", "r") as f:
    html_content = f.read()

# Extract and vectorize
result = system.process_single_function(html_content, "sprintf")
print(f"Processing result: {result.success}")

# Query functions
results = system.query_functions("string formatting function")
for result in results:
    print(f"Function: {result['function_name']}, Similarity: {result['similarity']:.3f}")
```

### Batch Processing

```python
from integrated_qnx_system import ProcessingTask

# Prepare tasks
tasks = [
    ProcessingTask("html/sprintf.html", "sprintf", priority=1),
    ProcessingTask("html/printf.html", "printf", priority=1),
]

# Batch processing
results = system.process_batch_functions(tasks, max_workers=4)

# Analyze results
successful = [r for r in results if r.success]
print(f"Successful: {len(successful)}/{len(tasks)}")
```

## Troubleshooting

### Common Issues

1. **Module Import Error**
   ```
   ImportError: No module named 'google.generativeai'
   ```
   Solution: `pip install google-generativeai`

2. **API Key Error**
   ```
   ValueError: Please set environment variable GEMINI_API_KEY
   ```
   Solution: Check API key configuration

3. **ChromaDB Permission Error**
   ```
   PermissionError: [Errno 13] Permission denied: './data/chroma_db'
   ```
   Solution: `chmod -R 755 ./data`

### Debug Mode

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Now run your code, detailed logs will be available
```

### Check Configuration

```python
import json
with open('config.json') as f:
    config = json.load(f)
print(json.dumps(config, indent=2))
```

## Performance Optimization Recommendations

1. **Concurrency Settings**: Adjust `max_workers` based on your hardware (recommended 4-8)
2. **Batch Size**: Adjust `batch_size` (default 32)
3. **Cache Management**: Regularly clean expired cache
4. **API Limits**: Pay attention to Gemini API rate limits

## Next Steps

1. Read `GEMINI_INTEGRATION.md` for detailed functionality
2. Run tests to verify system works properly
3. Adjust configuration parameters as needed
4. Start processing your QNX documentation

## Support

If you encounter issues, please check:
1. API key is correctly configured
2. Dependencies are fully installed
3. Network connection is working
4. Error messages in logs