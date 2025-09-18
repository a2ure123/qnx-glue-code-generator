# QNX Functions MCP Server Test

This directory contains test scripts for the QNX Functions MCP Server.

## File Description

- `test_mcp_server.py` - Basic MCP server functionality test script
- `interactive_mcp_test.py` - Interactive test script for manual vector database queries
- `mcp_config.json` - MCP server configuration file
- `config.json` - Main configuration file (copied from parent directory)

## Usage

### 1. Basic Test

```bash
cd tests
python test_mcp_server.py
```

This script tests:
- Retrieving available function list
- Function search feature
- Getting function details

### 2. Interactive Test

```bash
cd tests
python interactive_mcp_test.py
```

This script provides an interactive interface for manual vector database queries.

#### Available Commands:

- `search <query>` - Search for functions (e.g., `search abort`)
- `details <name>` - Get function details (e.g., `details abort`)
- `top <query>` - Search and display best match details
- `help` - Show help
- `quit` - Exit

#### Example Usage:

```
💬 Enter command: search abort

🔍 Search query: 'abort'
--------------------------------------------------
✅ Found 3 related functions:
1. abort (similarity: 0.856)
2. aborted (similarity: 0.732)
3. abort_message (similarity: 0.689)

💬 Enter command: details abort

📋 Get function details: 'abort'
--------------------------------------------------
✅ Function name: abort

📝 Function prototype:
   void abort(void);

📖 Description:
   Terminates the program abnormally...
```

## Prerequisites

Before running the tests, please ensure:

1. **Vector database is generated**:
   ```bash
   # Run in parent directory
   python qnx_batch_processor.py --all --output all_qnx_functions.json
   ```

2. **API key is configured**:
   Make sure the correct OpenAI API key is set in `config.json`

3. **Dependencies are installed**:
   ```bash
   pip install openai chromadb
   ```

## Troubleshooting

### Common Issues

1. **"No existing database found"**
   - Solution: Run the batch processor to generate the vector database first
   - Command: `python qnx_batch_processor.py --all`

2. **API connection failed**
   - Check network connection
   - Verify API key configuration
   - Check API quota

3. **Configuration file error**
   - Ensure `config.json` exists and is correctly formatted
   - Check all required configuration items

### Debug Information

Test scripts output detailed logs, including:
- Initialization status
- API connection status
- Vector database connection status
- Search result details

If you encounter issues, check these logs to diagnose the problem.