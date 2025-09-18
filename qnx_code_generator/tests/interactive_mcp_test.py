#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Interactive QNX MCP Server Test Script
Allows manual testing of vectorized database query functionality
"""

import asyncio
import sys
import os
from typing import List, Dict, Any

# Add parent directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from qnx_mcp_server import QNXFunctionsMCPServer

class InteractiveMCPTester:
    """Interactive MCP Server Tester"""
    
    def __init__(self):
        """Initialize tester"""
        self.server = QNXFunctionsMCPServer()
        self.is_initialized = False
    
    async def initialize(self):
        """Initialize MCP server"""
        if not self.is_initialized:
            print("🔧 Initializing vector database connection...")
            await self.server.initialize_vector_db()
            self.is_initialized = True
            
            if self.server.collection:
                print("✅ Vector database connected successfully")
            else:
                print("❌ Vector database connection failed. Please ensure the batch processor has generated data.")
                return False
        return True
    
    async def search_functions(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Search functions"""
        if not await self.initialize():
            return []
        
        print(f"\n🔍 Search query: '{query}'")
        print("-" * 50)
        
        results = await self.server.search_functions(query, max_results)
        
        if not results:
            print("❌ No related functions found")
            return []
        
        print(f"✅ Found {len(results)} related functions:")
        for i, result in enumerate(results, 1):
            print(f"{i}. {result['function_name']} (similarity: {result['similarity']:.3f})")
        
        return results
    
    async def get_function_details(self, function_name: str):
        """Get function details"""
        if not await self.initialize():
            return None
        
        print(f"\n📋 Getting function details: '{function_name}'")
        print("-" * 50)
        
        details = await self.server.get_function_details(function_name)
        
        if not details:
            print(f"❌ No details found for function '{function_name}'")
            return None
        
        func_data = details.get("function_data", {})
        
        print(f"✅ Function name: {func_data.get('name', function_name)}")
        
        if func_data.get("synopsis"):
            print(f"\n📝 Function prototype:")
            print(f"   {func_data['synopsis']}")
        
        if func_data.get("description"):
            desc = func_data['description']
            # Limit description length
            if len(desc) > 200:
                desc = desc[:200] + "..."
            print(f"\n📖 Description:")
            print(f"   {desc}")
        
        if func_data.get("parameters"):
            print(f"\n📥 Parameters ({len(func_data['parameters'])}):")
            for param in func_data["parameters"][:3]:  # Show only first 3 parameters
                print(f"   - {param.get('name', '')} ({param.get('type', '')})")
            if len(func_data["parameters"]) > 3:
                print(f"   ... {len(func_data['parameters']) - 3} more parameters")
        
        if func_data.get("return_type"):
            print(f"\n📤 Return type: {func_data['return_type']}")
        
        if func_data.get("headers"):
            print(f"\n📂 Header files:")
            for header in func_data["headers"][:2]:  # Show only first 2 headers
                print(f"   - {header.get('filename', '')}")
        
        return details
    
    async def run_interactive_session(self):
        """Run interactive session"""
        print("=" * 60)
        print("🧪 QNX Functions Vector Database Interactive Tester")
        print("=" * 60)
        print()
        print("Command help:")
        print("  search <query>     - Search functions (e.g.: search abort)")
        print("  details <name>     - Get function details (e.g.: details abort)")
        print("  top <query>        - Search and show best match details")
        print("  help               - Show help")
        print("  quit               - Exit")
        print()
        
        # Initialization
        if not await self.initialize():
            print("Initialization failed, exiting program")
            return
        
        while True:
            try:
                user_input = input("\n💬 Enter command: ").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("👋 Goodbye!")
                    break
                
                if user_input.lower() in ['help', 'h']:
                    print("\nCommand help:")
                    print("  search <query>     - Search functions")
                    print("  details <name>     - Get function details") 
                    print("  top <query>        - Search and show best match details")
                    print("  help               - Show help")
                    print("  quit               - Exit")
                    continue
                
                parts = user_input.split(maxsplit=1)
                command = parts[0].lower()
                
                if command == "search":
                    if len(parts) < 2:
                        print("❌ Please provide a search query (e.g.: search abort)")
                        continue
                    
                    query = parts[1]
                    await self.search_functions(query)
                
                elif command == "details":
                    if len(parts) < 2:
                        print("❌ Please provide a function name (e.g.: details abort)")
                        continue
                    
                    function_name = parts[1]
                    await self.get_function_details(function_name)
                
                elif command == "top":
                    if len(parts) < 2:
                        print("❌ Please provide a search query (e.g.: top abort)")
                        continue
                    
                    query = parts[1]
                    results = await self.search_functions(query, 1)
                    
                    if results:
                        best_match = results[0]
                        print(f"\n🏆 Best match function: {best_match['function_name']}")
                        await self.get_function_details(best_match['function_name'])
                
                else:
                    # Default: treat as search query
                    print(f"🔍 Treating '{user_input}' as a search query...")
                    results = await self.search_functions(user_input, 3)
                    
                    if results:
                        print(f"\n💡 To view details, use: details {results[0]['function_name']}")
                        print(f"💡 To view best match details, use: top {user_input}")
            
            except KeyboardInterrupt:
                print("\n\n👋 User interrupted, exiting program")
                break
            except Exception as e:
                print(f"❌ Error: {e}")

async def main():
    """Main function"""
    tester = InteractiveMCPTester()
    await tester.run_interactive_session()

if __name__ == "__main__":
    asyncio.run(main())