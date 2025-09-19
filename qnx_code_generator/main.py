#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QNX-Linux Glue Code Generator Main Entry Point

This is the main entry point for the QNX to Linux glue code generation system.
It coordinates between QNX MCP server, Linux MCP server, and the code generator
to produce C code that bridges QNX functions to Linux equivalents.
"""

import asyncio
import argparse
import json
import logging
import sys
from pathlib import Path
from typing import List

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from glue_generator.intelligent_agent import IntelligentGlueAgent

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def generate_glue_code_with_agent(functions: List[str], output_file: str = None):
    """Generate glue code for specified functions using intelligent agent"""
    try:
        # Initialize intelligent agent
        logger.info("Initializing QNX-Linux Intelligent Glue Agent...")
        agent = IntelligentGlueAgent()
        
        # Generate glue code using intelligent agent
        logger.info(f"Processing {len(functions)} functions with intelligent agent...")
        results = await agent.generate_glue_code_for_functions(functions)
        
        # Format and output results
        if output_file:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write summary report
            report_path = output_path.with_suffix('.json')
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            logger.info(f"Intelligent agent report written to: {report_path}")
        else:
            print("=== Intelligent Agent Results ===")
            print(json.dumps(results, indent=2, ensure_ascii=False))
        
        return results
        
    except Exception as e:
        logger.error(f"Intelligent agent processing failed: {e}")
        raise

async def generate_single_function_glue_code(function_name: str, output_dir: str = None):
    """Generate glue code for a single function using intelligent agent"""
    try:
        logger.info(f"Generating glue code for function '{function_name}'...")
        
        # Initialize intelligent agent
        agent = IntelligentGlueAgent()
        
        # Process single function
        results = await agent.generate_glue_code_for_functions([function_name])
        
        if results["completed"]:
            logger.info(f"✅ Function '{function_name}' processed successfully!")
            print(f"\n🎉 Successfully generated glue code for function '{function_name}'")
            
            if output_dir:
                output_path = Path(output_dir) / f"{function_name}_glue_report.json"
                output_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(results, f, indent=2, ensure_ascii=False)
                print(f"📄 Detailed report saved to: {output_path}")
        else:
            logger.error(f"❌ Function '{function_name}' processing failed")
            print(f"\n❌ Failed to generate glue code for function '{function_name}'")
            if results["failed"]:
                print(f"Reason: Check logs for details")
        
        # Print summary
        success_rate = results["summary"]["success_rate"] * 100
        print(f"\n📊 Processing Statistics:")
        print(f"   Total functions: {results['total_functions']}")
        print(f"   Completed: {results['summary']['total_completed']}")
        print(f"   Failed: {results['summary']['total_failed']}")
        print(f"   Success rate: {success_rate:.1f}%")
        
        return results
        
    except Exception as e:
        logger.error(f"Single function processing failed: {e}")
        print(f"❌ Error processing function '{function_name}': {e}")
        raise

async def test_system():
    """Test the intelligent agent with a few sample functions"""
    test_functions = [
        "malloc", "free", "printf"
    ]
    
    logger.info("Testing intelligent agent system...")
    results = await generate_glue_code_with_agent(test_functions, "output/test_glue_agent_report.json")
    
    print("\n=== Intelligent Agent System Test Results ===")
    print(f"Total functions: {results['total_functions']}")
    print(f"Completed: {len(results['completed'])}")
    print(f"Failed: {len(results['failed'])}")
    if results['total_functions'] > 0:
        print(f"Success rate: {results['summary']['success_rate']*100:.1f}%")
    
    if results['completed']:
        print(f"\n✅ Successfully processed functions: {', '.join(results['completed'])}")
    if results['failed']:
        print(f"\n❌ Failed to process functions: {', '.join(results['failed'])}")

def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="QNX-Linux Intelligent Glue Code Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py -s malloc                    # Generate glue code for single function
  python main.py -f malloc free printf       # Generate glue code for multiple functions
  python main.py --functions-file funcs.txt  # Read function list from file
  python main.py --test                      # Run system test
        """
    )
    
    parser.add_argument(
        "-s", "--single", 
        help="Generate glue code for a single QNX function"
    )
    
    parser.add_argument(
        "-f", "--functions", 
        nargs="+", 
        help="List of QNX functions to generate glue code for"
    )
    
    parser.add_argument(
        "--functions-file",
        help="File containing list of functions (one per line)"
    )
    
    parser.add_argument(
        "-o", "--output",
        help="Output directory or file path"
    )
    
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run intelligent agent system test"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Run appropriate command
    try:
        if args.single:
            # Single function mode
            asyncio.run(generate_single_function_glue_code(args.single, args.output))
        elif args.test:
            # System test
            asyncio.run(test_system())
        elif args.functions:
            # Multiple functions mode
            asyncio.run(generate_glue_code_with_agent(args.functions, args.output))
        elif args.functions_file:
            # Read function list from file
            try:
                with open(args.functions_file, 'r', encoding='utf-8') as f:
                    functions = [line.strip() for line in f if line.strip()]
                if functions:
                    asyncio.run(generate_glue_code_with_agent(functions, args.output))
                else:
                    print("❌ Function file is empty")
                    return 1
            except Exception as e:
                logger.error(f"Failed to read function file: {e}")
                return 1
        else:
            parser.print_help()
            return 1
            
        return 0
        
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        return 1
    except Exception as e:
        logger.error(f"Operation failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())