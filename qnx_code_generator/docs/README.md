# QNX-Linux Glue Code Generator Documentation

This directory contains documentation for the QNX-Linux Glue Code Generator system.

## Available Documentation

- 📚 [Setup Guide](SETUP_GUIDE.md) - Complete installation and configuration guide
- 🏗️ [MCP System](README_MCP_SYSTEM.md) - MCP server architecture and design

## System Architecture

The QNX-Linux Glue Code Generator consists of:

### Core Components
1. **QNX MCP Server** - Provides access to QNX function information
2. **Linux MCP Server** - Analyzes musl source code and generates glue code
3. **Intelligent Agent** - Coordinates the glue code generation process using LangGraph

### Key Features
- **Musl Source Analysis** - Scans musl library source code for function implementations
- **QNX Function Hijacking** - Uses ESCAPE_QNX_FUNC mechanism in dynlink.c
- **Three Generation Strategies**:
  - Create stub functions for QNX-only functions
  - Handle already escaped functions
  - Add new functions to escape mechanism
- **GDB Integration** - Analyzes compiled library functions
- **Retry Logic** - Handles compilation failures with error feedback

## Configuration

The system uses `config.json` for configuration:

```json
{
  "qnx_system": {
    "root_path": "/path/to/qnx700",
    "header_search_paths": [...]
  },
  "linux_system": {
    "musl_source_path": "/path/to/musl",
    "dynlink_path": "/path/to/musl/ldso/dynlink.c",
    "qnx_support_dir": "/path/to/qnxsupport"
  },
  "ai_settings": {
    "provider": "gemini",
    "gemini": {
      "model": "gemini-2.5-flash"
    }
  }
}
```

## Testing

See [tests/README.md](../tests/README.md) for comprehensive testing documentation.

Quick test:
```bash
cd tests
python run_all_tests.py
```