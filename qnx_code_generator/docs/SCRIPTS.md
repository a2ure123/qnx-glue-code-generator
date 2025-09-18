# Script File Description

## File List

### `analyze_qnx_structure.py`
- **Purpose**: Analyze QNX HTML document structure
- **Features**: 
  - Discover URL patterns in QNX documentation
  - Parse HTML page structure
  - Generate structure analysis report
- **Output**: `data/qnx_structure_analysis.json`
- **Status**: Analysis completed, 2004 functions found

### `qnx_full_index.py`
- **Purpose**: Full QNX index builder
- **Features**: 
  - Process all QNX functions (including multiple documents with duplicate function names)
  - Support batch building
  - Handle multiple variants of duplicate functions
- **Note**: Most comprehensive functionality, but requires stable network connection
- **Status**: Available but frequent network issues

## Usage Instructions

These scripts are mainly used during development and analysis. For regular use, it is recommended to use the core files in the main directory:
- `qnx_rag.py` - Basic RAG system
- `qnx_robust_index.py` - Recommended robust builder