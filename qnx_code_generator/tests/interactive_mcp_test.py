#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Interactive QNX Vector Database Test Script
Allows manual testing of vectorized database query functionality
"""

import sys
import os
import json
from typing import List, Dict, Any

# Add src directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir) 
src_dir = os.path.join(parent_dir, 'src', 'qnx_mcp')
sys.path.insert(0, src_dir)

try:
    from hybrid_vectorizer import HybridVectorizer
except ImportError:
    print("❌ 错误: 找不到向量化模块")
    print("请确保:")
    print("1. QNX 数据已经处理完成")
    print("2. 向量数据库已经建立")
    print("3. src/qnx_mcp/hybrid_vectorizer.py 文件存在")
    sys.exit(1)

class InteractiveVectorTester:
    """Interactive Vector Database Tester"""
    
    def __init__(self):
        """Initialize tester"""
        self.vectorizer = None
        self.is_initialized = False
        self.functions_data = None  # Cache for full function data
    
    def initialize(self):
        """Initialize vector database"""
        if not self.is_initialized:
            print("🔧 Initializing vector database connection...")
            try:
                # Change to parent directory to find config.json
                os.chdir(parent_dir)
                self.vectorizer = HybridVectorizer("config.json")
                collection = self.vectorizer.create_or_get_collection()
                count = collection.count()
                print(f"✅ Vector database connected successfully ({count} functions)")
                self.is_initialized = True
                
                if count == 0:
                    print("⚠️  Database is empty. Please run the batch processor first.")
                    return False
                
                # Load full function data from JSON file
                self._load_full_function_data()
                
            except Exception as e:
                print(f"❌ Vector database connection failed: {e}")
                return False
        return True
    
    def _load_full_function_data(self):
        """Load full function data from JSON file"""
        try:
            # Try to load the enhanced functions file
            enhanced_file = os.path.join(parent_dir, "data", "processed_functions", "qnx_functions_enhanced_full.json")
            if os.path.exists(enhanced_file):
                with open(enhanced_file, 'r', encoding='utf-8') as f:
                    self.functions_data = json.load(f)
                print(f"📁 Loaded full function data ({len(self.functions_data)} functions with GDB enhancement)")
                return
            
            # Fallback to basic extracted functions
            basic_file = os.path.join(parent_dir, "data", "processed_functions", "extracted_functions.json")
            if os.path.exists(basic_file):
                with open(basic_file, 'r', encoding='utf-8') as f:
                    self.functions_data = json.load(f)
                print(f"📁 Loaded basic function data ({len(self.functions_data)} functions)")
                return
            
            print("⚠️  No function data files found")
        except Exception as e:
            print(f"⚠️  Failed to load function data: {e}")
            self.functions_data = None
    
    def search_functions(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Search functions"""
        if not self.initialize():
            return []
        
        print(f"\n🔍 Search query: '{query}'")
        print("-" * 50)
        
        try:
            results = self.vectorizer.query_similar(query, max_results)
            
            if not results:
                print("❌ No related functions found")
                return []
            
            print(f"✅ Found {len(results)} related functions:")
            formatted_results = []
            for i, result in enumerate(results, 1):
                func_name = result.get('metadata', {}).get('function_name', 'unknown')
                similarity = result.get('similarity', 0)
                print(f"{i}. {func_name} (similarity: {similarity:.3f})")
                formatted_results.append({
                    'function_name': func_name,
                    'similarity': similarity,
                    'document': result.get('document', ''),
                    'metadata': result.get('metadata', {})
                })
            
            return formatted_results
        except Exception as e:
            print(f"❌ Search failed: {e}")
            return []
    
    def get_function_details(self, function_name: str):
        """Get function details with full information including GDB enhancement"""
        if not self.initialize():
            return None
        
        print(f"\n📋 Getting function details: '{function_name}'")
        print("=" * 80)
        
        try:
            # Get function data from cached JSON
            if not self.functions_data or function_name not in self.functions_data:
                print(f"❌ Function '{function_name}' not found in database")
                return None
            
            func_data = self.functions_data[function_name]
            
            # Basic Information
            print(f"✅ Function: {func_data.get('name', function_name)}")
            
            if func_data.get("synopsis"):
                print(f"\n📝 Synopsis:")
                print(f"   {func_data['synopsis']}")
            
            if func_data.get("description"):
                print(f"\n📖 Description:")
                desc_lines = func_data['description'].split('\n')
                for line in desc_lines[:3]:  # Show first 3 lines
                    print(f"   {line}")
                if len(desc_lines) > 3:
                    print(f"   ... (and {len(desc_lines) - 3} more lines)")
            
            # Parameters with GDB Enhancement
            if func_data.get("parameters"):
                print(f"\n📥 Parameters ({len(func_data['parameters'])}):")
                for i, param in enumerate(func_data["parameters"]):
                    param_type = param.get('type', 'unknown')
                    param_name = param.get('name', f'param{i}')
                    param_desc = param.get('description', '')
                    
                    print(f"   {i+1}. {param_name} ({param_type})")
                    
                    if param_desc:
                        print(f"      📝 {param_desc[:100]}{'...' if len(param_desc) > 100 else ''}")
                    
                    # Show GDB enhancement info if available
                    if param.get('enhanced') and param.get('info'):
                        info = param['info']
                        if info.get('ptype_result'):
                            gdb_type = info['ptype_result']
                            print(f"      🔍 GDB Type: {gdb_type[:100]}{'...' if len(gdb_type) > 100 else ''}")
                        
                        if info.get('type_classification'):
                            tc = info['type_classification']
                            type_flags = []
                            if tc.get('is_struct'): type_flags.append('struct')
                            if tc.get('is_union'): type_flags.append('union')
                            if tc.get('is_enum'): type_flags.append('enum')
                            if tc.get('is_pointer'): type_flags.append('pointer')
                            if tc.get('is_array'): type_flags.append('array')
                            if type_flags:
                                print(f"      📊 Type Info: {', '.join(type_flags)}")
                    print()
            
            # Return Information
            if func_data.get("return_type"):
                print(f"📤 Return Type: {func_data['return_type']}")
                if func_data.get("return_description"):
                    print(f"   📝 {func_data['return_description']}")
            
            # Headers and Libraries
            if func_data.get("headers"):
                print(f"\n📂 Headers:")
                for header in func_data["headers"]:
                    print(f"   - {header.get('filename', '')} ({header.get('path', '')})")
            
            if func_data.get("libraries"):
                print(f"\n📚 Libraries: {', '.join(func_data['libraries'])}")
            
            # Classification and Safety
            if func_data.get("classification"):
                print(f"\n🏷️  Classification: {func_data['classification']}")
            
            if func_data.get("safety"):
                safety = func_data["safety"]
                print(f"\n🛡️  Safety:")
                if isinstance(safety, dict):
                    for key, value in safety.items():
                        print(f"   - {key.replace('_', ' ').title()}: {value}")
                else:
                    print(f"   {safety}")
            
            # Related Functions
            if func_data.get("see_also"):
                related = func_data["see_also"][:5]  # Show first 5
                print(f"\n🔗 Related: {', '.join(related)}")
            
            return func_data
            
        except Exception as e:
            print(f"❌ Error getting function details: {e}")
            return None
    
    def show_database_stats(self):
        """Show database statistics"""
        if not self.initialize():
            return
        
        print(f"\n📊 Database Statistics")
        print("=" * 50)
        
        # Vector database stats
        try:
            collection = self.vectorizer.create_or_get_collection()
            vector_count = collection.count()
            print(f"🔢 Vector Database: {vector_count} functions")
        except Exception as e:
            print(f"❌ Vector database error: {e}")
        
        # JSON data stats
        if self.functions_data:
            total_functions = len(self.functions_data)
            enhanced_functions = 0
            
            for func_data in self.functions_data.values():
                if func_data.get("parameters"):
                    for param in func_data["parameters"]:
                        if param.get("enhanced"):
                            enhanced_functions += 1
                            break
            
            print(f"📁 JSON Database: {total_functions} functions")
            print(f"🔍 GDB Enhanced: {enhanced_functions} functions")
            print(f"📈 Enhancement Rate: {enhanced_functions/total_functions*100:.1f}%")
        else:
            print("📁 JSON Database: Not loaded")
    
    def run_interactive_session(self):
        """Run interactive session"""
        print("=" * 60)
        print("🧪 QNX Functions Vector Database Interactive Tester")
        print("=" * 60)
        print()
        print("Command help:")
        print("  search <query>     - Search functions (e.g.: search abort)")
        print("  details <name>     - Get full function details with GDB info (e.g.: details malloc)")
        print("  top <query>        - Search and show best match details")
        print("  stats              - Show database statistics")
        print("  count              - Show function count")
        print("  help               - Show help")
        print("  quit               - Exit")
        print()
        
        # Initialization
        if not self.initialize():
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
                    print("  details <name>     - Get full function details with GDB info") 
                    print("  top <query>        - Search and show best match details")
                    print("  stats              - Show database statistics")
                    print("  count              - Show function count")
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
                    self.search_functions(query)
                
                elif command == "details":
                    if len(parts) < 2:
                        print("❌ Please provide a function name (e.g.: details abort)")
                        continue
                    
                    function_name = parts[1]
                    self.get_function_details(function_name)
                
                elif command == "top":
                    if len(parts) < 2:
                        print("❌ Please provide a search query (e.g.: top abort)")
                        continue
                    
                    query = parts[1]
                    results = self.search_functions(query, 1)
                    
                    if results:
                        best_match = results[0]
                        print(f"\n🏆 Best match function: {best_match['function_name']}")
                        self.get_function_details(best_match['function_name'])
                
                elif command in ["stats", "statistics"]:
                    self.show_database_stats()
                
                elif command in ["count", "num"]:
                    if not self.initialize():
                        continue
                    
                    try:
                        collection = self.vectorizer.create_or_get_collection()
                        vector_count = collection.count()
                        
                        if self.functions_data:
                            json_count = len(self.functions_data)
                            print(f"\n📊 Function Count:")
                            print(f"   🔢 Vector Database: {vector_count} functions")
                            print(f"   📁 JSON Database: {json_count} functions")
                        else:
                            print(f"\n📊 Vector Database: {vector_count} functions")
                    except Exception as e:
                        print(f"❌ Error getting count: {e}")
                
                else:
                    # Default: treat as search query
                    print(f"🔍 Treating '{user_input}' as a search query...")
                    results = self.search_functions(user_input, 3)
                    
                    if results:
                        print(f"\n💡 To view details, use: details {results[0]['function_name']}")
                        print(f"💡 To view best match details, use: top {user_input}")
            
            except KeyboardInterrupt:
                print("\n\n👋 User interrupted, exiting program")
                break
            except Exception as e:
                print(f"❌ Error: {e}")

def main():
    """Main function"""
    tester = InteractiveVectorTester()
    tester.run_interactive_session()

if __name__ == "__main__":
    main()