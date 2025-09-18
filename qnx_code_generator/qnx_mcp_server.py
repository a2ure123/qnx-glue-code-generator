#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QNX Functions MCP Server
Provides an MCP server for QNX function information queries, supporting vector database retrieval and detailed function information access.
"""

import asyncio
import json
import logging
import os
import sys
from typing import Any, Dict, List, Optional, Sequence
from pathlib import Path

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# MCP imports
from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
import mcp.server.stdio

# Project imports
from hybrid_vectorizer import HybridVectorizer
from openai_json_extractor import serialize_function_info
import chromadb

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class QNXFunctionsMCPServer:
    """QNX Function Information MCP Server"""
    
    def __init__(self, config_path: str = "config.json"):
        """Initialize MCP server"""
        self.config_path = config_path
        self.config = self._load_config(config_path)
        
        # Initialize vectorizer and database connection
        self.vectorizer = None
        self.chroma_client = None
        self.collection = None
        
        # Data directory
        self.data_dir = Path("./data/processed_functions")
        self.chroma_db_path = "./data/chroma_db"
        
        logger.info("QNX Functions MCP Server initialized")
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration file"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load config file: {e}")
            return {}
    
    async def initialize_vector_db(self):
        """Initialize vector database connection"""
        try:
            # Initialize vectorizer
            self.vectorizer = HybridVectorizer(self.config_path)
            
            # Initialize ChromaDB client
            self.chroma_client = chromadb.PersistentClient(path=self.chroma_db_path)
            
            # Get or create collection
            try:
                self.collection = self.chroma_client.get_collection("qnx_functions_hybrid")
                logger.info("Successfully connected to existing QNX function vector database")
            except Exception:
                logger.warning("No existing database found, please run the batch processor to generate data first")
                self.collection = None
                
        except Exception as e:
            logger.error(f"Failed to initialize vector database: {e}")
            self.vectorizer = None
            self.collection = None
    
    async def search_functions(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """Search for relevant functions"""
        if not self.collection or not self.vectorizer:
            await self.initialize_vector_db()
            
        if not self.collection:
            return []
        
        try:
            # Generate query vector
            query_result = self.vectorizer.get_single_embedding(query)
            if not query_result.success:
                logger.error(f"Failed to generate query embedding: {query_result.error}")
                return []
            
            # Search in vector database
            results = self.collection.query(
                query_embeddings=[query_result.embedding],
                n_results=min(n_results, 10),  # Limit max results
                include=["metadatas", "documents", "distances"]
            )
            
            # Format results
            formatted_results = []
            if results["metadatas"] and results["metadatas"][0]:
                for i, metadata in enumerate(results["metadatas"][0]):
                    function_name = metadata.get("function_name", "unknown")
                    distance = results["distances"][0][i] if results["distances"] else 0
                    similarity = 1 - distance  # Convert to similarity
                    
                    formatted_results.append({
                        "function_name": function_name,
                        "similarity": round(similarity, 4),
                        "distance": round(distance, 4),
                        "metadata": metadata
                    })
            
            logger.info(f"Found {len(formatted_results)} relevant functions")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Function search failed: {e}")
            return []
    
    async def get_function_details(self, function_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a function"""
        try:
            # Search processed function files
            for json_file in self.data_dir.glob("*.json"):
                if json_file.name.endswith('.stats.json'):
                    continue
                    
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    if function_name in data:
                        function_data = data[function_name]
                        
                        # Add some metadata
                        result = {
                            "function_name": function_name,
                            "source_file": str(json_file.name),
                            "function_data": function_data.get("function_data", {}),
                            "has_embedding": function_data.get("has_embedding", False)
                        }
                        
                        logger.info(f"Found function details: {function_name}")
                        return result
                        
                except Exception as e:
                    logger.warning(f"Failed to read file {json_file}: {e}")
                    continue
            
            logger.warning(f"Function not found: {function_name}")
            return None
            
        except Exception as e:
            logger.error(f"Failed to get function details: {e}")
            return None
    
    async def get_available_functions(self, limit: int = 50) -> List[str]:
        """Get list of available functions"""
        try:
            functions = set()
            
            # Scan all JSON files
            for json_file in self.data_dir.glob("*.json"):
                if json_file.name.endswith('.stats.json'):
                    continue
                    
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    functions.update(data.keys())
                    
                except Exception as e:
                    logger.warning(f"Failed to read file {json_file}: {e}")
                    continue
            
            # Convert to sorted list and limit count
            function_list = sorted(list(functions))[:limit]
            logger.info(f"Found {len(function_list)} available functions")
            return function_list
            
        except Exception as e:
            logger.error(f"Failed to get function list: {e}")
            return []


# Create MCP server instance
server = Server("qnx-functions")
qnx_server = QNXFunctionsMCPServer()

@server.list_tools()
async def handle_list_tools() -> List[types.Tool]:
    """List available tools"""
    return [
        types.Tool(
            name="search_qnx_functions",
            description="Search for QNX functions using semantic similarity",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (function name, description, or functionality)"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default: 5)",
                        "default": 5,
                        "minimum": 1,
                        "maximum": 10
                    }
                },
                "required": ["query"]
            }
        ),
        types.Tool(
            name="get_qnx_function_details",
            description="Get detailed information about a specific QNX function",
            inputSchema={
                "type": "object",
                "properties": {
                    "function_name": {
                        "type": "string",
                        "description": "Name of the QNX function to get details for"
                    }
                },
                "required": ["function_name"]
            }
        ),
        types.Tool(
            name="list_available_qnx_functions",
            description="Get a list of all available QNX functions in the database",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of functions to return (default: 50)",
                        "default": 50,
                        "minimum": 1,
                        "maximum": 200
                    }
                }
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[types.TextContent]:
    """Handle tool calls"""
    try:
        if name == "search_qnx_functions":
            query = arguments.get("query", "")
            max_results = arguments.get("max_results", 5)
            
            if not query:
                return [types.TextContent(
                    type="text",
                    text="Error: Query parameter is required"
                )]
            
            results = await qnx_server.search_functions(query, max_results)
            
            if not results:
                return [types.TextContent(
                    type="text", 
                    text=f"No QNX functions found for query: '{query}'"
                )]
            
            # Format search results
            result_text = f"Found {len(results)} QNX functions for query: '{query}'\n\n"
            
            for i, result in enumerate(results, 1):
                result_text += f"{i}. **{result['function_name']}**\n"
                result_text += f"   Similarity: {result['similarity']:.3f}\n"
                result_text += f"   Use `get_qnx_function_details` with function_name='{result['function_name']}' for full details\n\n"
            
            return [types.TextContent(type="text", text=result_text)]
        
        elif name == "get_qnx_function_details":
            function_name = arguments.get("function_name", "")
            
            if not function_name:
                return [types.TextContent(
                    type="text",
                    text="Error: function_name parameter is required"
                )]
            
            details = await qnx_server.get_function_details(function_name)
            
            if not details:
                return [types.TextContent(
                    type="text",
                    text=f"Function '{function_name}' not found in QNX database"
                )]
            
            # Format function details
            func_data = details.get("function_data", {})
            
            result_text = f"# QNX Function: {function_name}\n\n"
            
            if func_data.get("synopsis"):
                result_text += f"## Synopsis\n```c\n{func_data['synopsis']}\n```\n\n"
            
            if func_data.get("description"):
                result_text += f"## Description\n{func_data['description']}\n\n"
            
            if func_data.get("parameters"):
                result_text += "## Parameters\n"
                for param in func_data["parameters"]:
                    result_text += f"- **{param.get('name', '')}** ({param.get('type', '')}): {param.get('description', '')}\n"
                result_text += "\n"
            
            if func_data.get("return_type") or func_data.get("return_description"):
                result_text += "## Returns\n"
                if func_data.get("return_type"):
                    result_text += f"Type: `{func_data['return_type']}`\n"
                if func_data.get("return_description"):
                    result_text += f"{func_data['return_description']}\n"
                result_text += "\n"
            
            if func_data.get("headers"):
                result_text += "## Headers\n"
                for header in func_data["headers"]:
                    result_text += f"- `{header.get('filename', '')}`\n"
                result_text += "\n"
            
            if func_data.get("examples"):
                result_text += "## Examples\n"
                for example in func_data["examples"]:
                    result_text += f"```c\n{example}\n```\n"
                result_text += "\n"
            
            if func_data.get("see_also"):
                result_text += "## See Also\n"
                for related in func_data["see_also"]:
                    result_text += f"- {related}\n"
                result_text += "\n"
            
            if func_data.get("classification"):
                result_text += f"**Classification**: {func_data['classification']}\n"
            
            if func_data.get("safety"):
                result_text += f"**Thread Safety**: {func_data['safety']}\n"
            
            return [types.TextContent(type="text", text=result_text)]
        
        elif name == "list_available_qnx_functions":
            limit = arguments.get("limit", 50)
            
            functions = await qnx_server.get_available_functions(limit)
            
            if not functions:
                return [types.TextContent(
                    type="text",
                    text="No QNX functions found in database. Please run the batch processor first."
                )]
            
            result_text = f"Available QNX Functions ({len(functions)} total):\n\n"
            
            # Display grouped by first letter
            current_letter = ""
            for func in functions:
                first_letter = func[0].upper()
                if first_letter != current_letter:
                    current_letter = first_letter
                    result_text += f"\n**{current_letter}**\n"
                
                result_text += f"- {func}\n"
            
            result_text += f"\nUse `get_qnx_function_details` to get detailed information about any function.\n"
            result_text += f"Use `search_qnx_functions` to find functions by description or functionality.\n"
            
            return [types.TextContent(type="text", text=result_text)]
        
        else:
            return [types.TextContent(
                type="text",
                text=f"Unknown tool: {name}"
            )]
    
    except Exception as e:
        logger.error(f"Tool call error: {e}")
        return [types.TextContent(
            type="text",
            text=f"Error executing tool '{name}': {str(e)}"
        )]

async def main():
    """Main function"""
    # Initialize vector database connection
    await qnx_server.initialize_vector_db()
    
    # Run MCP server
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream, 
            write_stream, 
            InitializationOptions(
                server_name="qnx-functions",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={}
                )
            )
        )

if __name__ == "__main__":
    asyncio.run(main())