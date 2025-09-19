# Test Suite

This directory contains comprehensive tests for the QNX-Linux Glue Code Generator system.

## Running Tests

Run all tests:
```bash
python run_all_tests.py
```

Run individual test suites:
```bash
python system_test_summary.py
python test_linux_mcp_system.py
python test_intelligent_agent_system.py
python test_gdb_analysis.py
```

## Test Suites

### Core System Tests
- `system_test_summary.py` - Comprehensive system integration test
- `test_linux_mcp_system.py` - Linux MCP server functionality
- `test_intelligent_agent_system.py` - LangGraph intelligent agent tests
- `test_gdb_analysis.py` - GDB analysis functionality

### Legacy Tests
- `legacy/test_qnx_system.py` - Old QNX web crawler system tests
- `legacy/test_mcp_server.py` - Old MCP server tests
- `interactive_mcp_test.py` - Interactive testing script

## Test Configuration

Test configuration files:
- `config.json` - Test-specific configuration
- `mcp_config.json` - MCP server test configuration

## Prerequisites

Before running tests:

1. **System Dependencies**:
   ```bash
   pip install langgraph chromadb
   ```

2. **Musl Library Compiled**:
   ```bash
   cd /home/a2ure/Desktop/afl-qnx/qol/musl
   ./configure --enable-shared && make
   ```

3. **Configuration**:
   - Ensure `config.json` has correct paths
   - Set up API keys if needed

## Test Results

Tests verify:
- ✅ Linux MCP server musl analysis
- ✅ QNX function hijacking mechanism
- ✅ Intelligent agent state management
- ✅ GDB integration functionality
- ✅ Glue code generation strategies

## Troubleshooting

### Common Issues

1. **LangGraph not available**:
   ```bash
   pip install langgraph
   ```

2. **musl libc.so not found**:
   ```bash
   cd /path/to/musl && make clean && ./configure --enable-shared && make
   ```

3. **Import errors**:
   - Check Python path includes src directory
   - Verify all dependencies installed

### Debug Mode

For detailed logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```