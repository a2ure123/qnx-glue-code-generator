# QNX-Linux Glue Code Generator

An intelligent system for generating C glue code that bridges QNX functions to Linux equivalents. The system uses MCP (Model Context Protocol) servers to provide function information from both QNX and Linux systems, then generates appropriate wrapper code for function migration.

## 🎯 Project Overview

This project implements a complete pipeline for migrating QNX applications to Linux by automatically generating glue code. The system analyzes QNX functions, finds Linux equivalents, and generates C wrapper functions that maintain compatibility.

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   QNX MCP       │    │   Linux MCP     │    │  Glue Code      │
│   Server        │    │   Server        │    │  Generator      │
│                 │    │                 │    │                 │
│ • QNX Docs RAG  │    │ • musl libc     │    │ • Strategy      │
│ • Function Info │────│ • glibc info    │────│   Analysis      │
│ • Vector Search │    │ • Compatibility │    │ • Code          │
│                 │    │   Analysis      │    │   Templates     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 📁 Project Structure

```
qnx_code_generator/
├── 🎮 Main Entry Point
│   └── main.py                     # Command-line interface
│
├── 📦 Source Code
│   ├── qnx_mcp/                    # QNX MCP Server
│   │   ├── qnx_mcp_server.py       # QNX function information server
│   │   ├── qnx_web_crawler.py      # QNX documentation crawler
│   │   ├── qnx_step_processor.py   # Multi-step processing pipeline
│   │   ├── claude_json_extractor.py # Claude API JSON extraction
│   │   ├── hybrid_vectorizer.py    # Vector embedding system
│   │   └── qnx_gdb_type_enhancer.py # GDB type analysis (single & multi-threaded)
│   │
│   ├── linux_mcp/                  # Linux MCP Server
│   │   └── linux_mcp_server.py     # Linux function information server
│   │
│   ├── glue_generator/             # Code Generation Engine
│   │   └── code_generator.py       # Main glue code generator
│   │
│   └── core/                       # Shared Utilities
│       └── mcp_client.py           # MCP client utilities
│
├── 📚 Documentation
│   ├── README.md                   # This file
│   ├── MCP_USAGE.md                # MCP server usage guide
│   ├── docs/                       # Detailed documentation
│   │   ├── architecture.md         # System architecture
│   │   ├── SETUP_GUIDE.md          # Installation guide
│   │   └── README_MCP_SYSTEM.md    # MCP system details
│   │
├── 🧪 Tests
│   ├── test_mcp_server.py          # MCP server tests
│   └── test_qnx_system.py          # System integration tests
│
├── 🛠️ Utilities
│   └── scripts/                    # Helper scripts
│       ├── analyze_qnx_structure.py
│       └── qnx_full_index.py
│
├── ⚙️ Configuration
│   ├── config.json                 # System configuration
│   ├── requirements.txt            # Python dependencies
│   └── .env.example                # Environment variables template
│
└── 📊 Data (Generated at runtime)
    ├── qnx_web_cache/              # QNX documentation cache
    ├── processed_functions/         # Processed function data
    │   ├── extracted_functions.json  # Raw JSON extracted functions (1618 functions)
    │   └── qnx_functions_enhanced_full.json # GDB enhanced functions with type info
    └── chroma_db/                  # Vector database
```

## 🚀 Quick Start

### 1. Installation

```bash
# Clone the repository
git clone <repository-url>
cd qnx_code_generator

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env and add your API keys
```

### 2. Initialize QNX Knowledge Base

```bash
# Two-step process: JSON extraction then GDB enhancement

# Step 1: Extract all QNX functions to JSON (without GDB enhancement)
source .env && python src/qnx_mcp/qnx_step_processor.py --skip-discover --skip-crawl --skip-gdb

# Step 2: Apply GDB type enhancement to extracted functions (multi-threaded)
python src/qnx_mcp/qnx_gdb_type_enhancer.py --input data/processed_functions/extracted_functions.json --output data/processed_functions/qnx_functions_enhanced_full.json --workers 6
```

### 3. Generate Glue Code

```bash
# Generate glue code for specific functions
python main.py -f malloc free printf sprintf -o output/glue.c

# Generate from a function list file
echo -e "malloc\nfree\nprintf" > functions.txt
python main.py --functions-file functions.txt -o output/glue.c

# Run system test
python main.py --test
```

## 🔧 Migration Strategies

The system uses multiple strategies for function migration:

### 1. **Direct Wrapper**
For functions with identical signatures:
```c
// QNX malloc -> Linux malloc
void* malloc(size_t size) {
    return malloc(size);  // Direct mapping
}
```

### 2. **Parameter Adaptation**
For functions needing parameter conversion:
```c
// QNX function with different parameter types
int qnx_function(qnx_type_t param) {
    linux_type_t converted = convert_param(param);
    return linux_function(converted);
}
```

### 3. **Heuristic Implementation**
For QNX-specific functions without Linux equivalents:
```c
// QNX-specific function - placeholder implementation
uint64_t __stackavail(void) {
    // Return large value indicating plenty of stack space
    return 0xffffffffffffffff;
}
```

### 4. **Complex Migration**
For functions requiring detailed analysis and custom logic.

## 🛠️ MCP Servers

### QNX MCP Server
- **Purpose**: Provides QNX function information
- **Tools**:
  - `get_qnx_function_info`: Get detailed function information
  - `search_qnx_functions`: Search functions by name/description
  - `list_qnx_functions`: List available functions

### Linux MCP Server  
- **Purpose**: Provides Linux function information
- **Tools**:
  - `get_linux_function_info`: Get Linux function details
  - `search_linux_functions`: Search Linux functions
  - `analyze_function_compatibility`: Compare QNX vs Linux functions

## 📊 Usage Examples

### Command Line Usage

```bash
# Basic usage
python main.py -f printf sprintf malloc

# With output file
python main.py -f printf sprintf -o my_glue_code.c

# Process many functions
python main.py --functions-file all_functions.txt --output output/

# Test the system
python main.py --test

# List available functions
python main.py --list-functions
```

### Python API Usage

```python
from src.glue_generator.code_generator import GlueCodeGenerator

# Initialize generator
generator = GlueCodeGenerator()

# Generate code for functions
results = await generator.generate_bulk_glue_code([
    "malloc", "free", "printf", "pthread_create"
])

# Access generated code
print(results["header_code"])
print(results["function_code"])
print(results["statistics"])
```

## 🔍 Output Format

The system generates:

1. **C Header Code**: Includes and declarations
2. **C Function Code**: Wrapper function implementations
3. **Migration Report**: JSON report with statistics and migration plans

Example output structure:
```c
// QNX to Linux glue code
// Generated automatically - do not edit manually

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// Direct wrapper for malloc -> malloc
void* malloc(size_t size) {
    return malloc(size);
}

// Heuristic implementation for qnx_specific_func
int qnx_specific_func(void) {
    // TODO: Implement based on QNX behavior
    return 0; // Placeholder
}
```

## ⚙️ Configuration

### Environment Variables
```bash
OPENAI_API_KEY=your_openai_key_here    # For QNX documentation processing
GEMINI_API_KEY=your_gemini_key_here    # Alternative AI provider
CLAUDE_API_KEY=your_claude_key_here    # For Claude API access
```

### config.json
```json
{
  "ai_settings": {
    "openai": {
      "chat_model": "gpt-4o-mini",
      "embedding_model": "text-embedding-3-small"
    }
  },
  "qnx_system": {
    "root_path": "/path/to/qnx700",
    "gdb_executable": "ntox86_64-gdb"
  },
  "claude_api": {
    "endpoint": "http://your-claude-server:3000/api",
    "model": "claude-3-sonnet"
  }
}
```

## 🧪 Testing

```bash
# Run MCP server tests
python tests/test_mcp_server.py

# Run system integration tests  
python tests/test_qnx_system.py

# Run interactive MCP test
python tests/interactive_mcp_test.py
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

## 🔗 Related Documentation

- [MCP Usage Guide](MCP_USAGE.md) - Detailed MCP server usage
- [Architecture Design](docs/architecture.md) - System architecture details
- [Setup Guide](docs/SETUP_GUIDE.md) - Detailed installation instructions

## 🆘 Support

For issues and questions:
1. Check the documentation in the `docs/` directory
2. Review existing issues on GitHub
3. Create a new issue with detailed information

---

**Note**: This system is designed for QNX to Linux migration assistance. The generated code should be reviewed and tested thoroughly before production use.