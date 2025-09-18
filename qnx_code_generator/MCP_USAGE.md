# QNX Functions MCP Server Usage Guide

## Overview

QNX Functions MCP Server is a Model Context Protocol (MCP) server that allows large language models to query QNX function information through tool calls.

## Features

### 🔍 Core Functions

1. **Semantic Search**: Search QNX functions through vector similarity
2. **Function Details**: Get complete function documentation information
3. **Function List**: Browse all available QNX functions

### 🛠️ Available Tools

#### 1. search_qnx_functions
Search QNX functions (supports semantic search)

**Parameters**:
- `query` (required): Search query (function name, description, or functionality)
- `max_results` (optional): Maximum number of results (default 5, max 10)

**Example**:
```json
{
  "query": "memory allocation",
  "max_results": 5
}
```

#### 2. get_qnx_function_details
Get detailed information for a specific QNX function

**Parameters**:
- `function_name` (required): QNX function name

**Example**:
```json
{
  "function_name": "malloc"
}
```

#### 3. list_available_qnx_functions
Get list of all available QNX functions

**Parameters**:
- `limit` (optional): Maximum number to return (default 50, max 200)

**Example**:
```json
{
  "limit": 100
}
```

## Configuration and Setup

### 1. Configuration Requirements

Ensure you have run the QNX batch processor to generate function data:

```bash
# Generate QNX function data
python qnx_batch_processor.py --all --output all_qnx_functions.json
```

### 2. Thread Configuration

Configure processing parameters in `config.json`:

```json
{
  "processing_settings": {
    "max_worker_threads": 3,
    "api_request_delay_range": [0.5, 2.0],
    "enable_multithreading": true
  }
}
```

### 3. MCP Server Configuration

Create MCP configuration file (for use with Claude Code):

```json
{
  "mcpServers": {
    "qnx-functions": {
      "command": "python",
      "args": ["qnx_mcp_server.py"],
      "cwd": "/home/a2ure/Desktop/afl-qnx/gen_code_v2"
    }
  }
}
```

### 4. Test Server

Run test script to verify functionality:

```bash
python test_mcp_server.py
```

## Usage Examples

### Scenario 1: Finding Memory Allocation Functions

**User**: "I need to allocate memory in QNX, what functions are available?"

**MCP Call**:
```json
{
  "tool": "search_qnx_functions",
  "arguments": {
    "query": "memory allocation",
    "max_results": 5
  }
}
```

**Response**: Returns malloc, calloc, realloc and other related functions

### Scenario 2: Getting Function Details

**User**: "How do I use the malloc function?"

**MCP Call**:
```json
{
  "tool": "get_qnx_function_details", 
  "arguments": {
    "function_name": "malloc"
  }
}
```

**Response**: Returns complete malloc function documentation, including:
- Function prototype
- Parameter descriptions
- Return value
- Usage examples
- Related functions
- Thread safety

### Scenario 3: Browsing Available Functions

**User**: "What string processing functions does QNX have?"

**MCP Call**:
```json
{
  "tool": "search_qnx_functions",
  "arguments": {
    "query": "string processing",
    "max_results": 10
  }
}
```

**Response**: Returns strlen, strcpy, strcmp and other string-related functions

## Technical Architecture

### Component Description

1. **Vector Database Query**: Uses ChromaDB for efficient similarity search
2. **Multi-threaded Processing**: Supports configurable concurrent processing
3. **GDB Type Enhancement**: Integrates QNX GDB for precise type information
4. **Error Handling**: Comprehensive exception handling and retry mechanisms

### Data Flow

```
LLM Request → MCP Server → Vector Search → Function Data → Formatted Response → LLM
```

## Performance Optimization

### Configuration Recommendations

- **Thread Count**: Adjust based on hardware performance (recommended 3-5 threads)
- **API Delay**: Set reasonable request delays to avoid rate limiting
- **Cache Strategy**: Vector database automatically caches embedding results

### Monitoring Metrics

- Search response time
- API call success rate
- Vector database connection status

## Troubleshooting

### Common Issues

1. **Vector Database Not Found**
   ```
   Solution: Run python qnx_batch_processor.py first to generate data
   ```

2. **MCP Connection Failed**
   ```
   Solution: Check mcp_config.json path configuration
   ```

3. **Function Search Returns No Results**
   ```
   Solution: Verify ChromaDB data integrity
   ```

## Integration Example

### Claude Code Integration

Add MCP configuration to Claude Code settings to use directly in conversations:

**User**: "I need information about QNX's open function"

**Claude**: Uses MCP tools to search and return complete documentation for the open function, including parameter descriptions, usage examples, and related functions.

This enables **documentation-driven intelligent programming assistance**, greatly improving QNX development efficiency!