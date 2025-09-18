# QNX-Linux Glue Code Generation System v2.0 Architecture Design

## System Overview

An intelligent glue code generation system based on RAG + MCP + Agent, used for function migration from QNX to Linux.

## Core Components

### 1. QNX Documentation RAG System
- **Tech Stack**: LlamaIndex + Chroma
- **Functionality**: Vectorized storage and semantic retrieval of QNX HTML technical documentation
- **Input**: QNX official documentation HTML files
- **Output**: Structured function information (function signature, parameters, return value, usage)

### 2. MCP Service Layer

#### 2.1 Linux Function Information MCP (`linux_func_mcp`)
- **Functionality**: Provides musl libc function implementation information
- **Tools**:
  - `get_linux_function`: Get implementation code and parameter information by function name
  - `search_similar_functions`: Search for functions with similar functionality
  - `analyze_dependencies`: Analyze function dependencies

#### 2.2 QNX Function Information MCP (`qnx_func_mcp`)
- **Functionality**: Provides QNX function information based on RAG
- **Tools**:
  - `get_qnx_function`: Retrieve function information from RAG by function name
  - `semantic_search`: Semantic search for related functions
  - `get_function_docs`: Get detailed documentation

#### 2.3 Compile Verification MCP (`compile_mcp`)
- **Functionality**: Code compilation verification and error feedback
- **Tools**:
  - `compile_code`: Compile the generated glue code
  - `analyze_errors`: Analyze compilation errors
  - `suggest_fixes`: Provide fix suggestions based on error information

#### 2.4 IDA Analysis MCP (`ida_mcp`) 
- **Functionality**: Binary code analysis support
- **Tools**:
  - `analyze_function`: Analyze binary implementation of functions
  - `find_missing_symbols`: Find missing symbol definitions
  - `extract_constants`: Extract key constants and structures

### 3. Intelligent Generation Agent

#### 3.1 Core Logic
```
Input: Target function name
↓
1. Get QNX function information (qnx_func_mcp)
2. Get corresponding Linux implementation (linux_func_mcp)
3. Function compatibility analysis
4. Select generation strategy:
   - Direct migration: Compatible parameters, direct wrapping
   - Adaptation generation: Parameters need conversion
   - Heuristic implementation: musl missing function, generate placeholder implementation
   - IDA assistance: Complex functions require binary analysis
5. Code generation (Claude 4 Sonnet)
6. Compile verification (compile_mcp)
7. Error correction loop
↓
Output: Verified glue code
```

#### 3.2 Generation Strategies

**Strategy 1: Direct Migration**
- Condition: Function signature compatible, musl has corresponding implementation
- Action: Generate simple wrapper function

**Strategy 2: Parameter Adaptation**  
- Condition: Function exists but parameters are incompatible
- Action: Generate parameter conversion code

**Strategy 3: Heuristic Implementation**
- Condition: musl lacks the function
- Action: Generate reasonable placeholder implementation based on function semantics
- Example: `uint64_t __stackavail(void) { return 0xffffffffffffffff; }`

**Strategy 4: IDA Assisted Analysis**
- Condition: Complex functions require understanding of underlying implementation
- Action: Use IDA MCP to analyze binary and guide generation

## Workflow

1. **Initialization**: Load QNX documentation into RAG system
2. **Function Query**: Receive list of target function names
3. **Information Collection**: Parallel MCP service calls to collect function information
4. **Intelligent Analysis**: Agent analyzes compatibility and selects strategy
5. **Code Generation**: Generate glue code based on strategy
6. **Compile Verification**: Verify code correctness
7. **Iterative Optimization**: Optimize based on compilation error feedback
8. **Output Delivery**: Generate final glue code files

## Advantages

1. **Intelligent**: RAG semantic retrieval + LLM reasoning
2. **Modular**: MCP standardized interfaces, easy to extend
3. **Reliable**: Compilation verification ensures code quality
4. **Flexible**: Multiple generation strategies for different scenarios
5. **Maintainable**: Clear architectural layering