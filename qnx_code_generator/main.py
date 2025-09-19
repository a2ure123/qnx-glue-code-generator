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

from core.mcp_client import QNXMCPClient, LinuxMCPClient
from glue_generator.code_generator import GlueCodeGenerator

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def generate_glue_code(functions: List[str], output_file: str = None):
    """Generate glue code for specified functions"""
    try:
        # Initialize components
        logger.info("Initializing QNX-Linux glue code generator...")
        
        qnx_client = QNXMCPClient()
        linux_client = LinuxMCPClient()
        generator = GlueCodeGenerator()
        
        # Connect to MCP servers
        logger.info("Connecting to MCP servers...")
        qnx_connected = await qnx_client.connect()
        linux_connected = await linux_client.connect()
        
        if not qnx_connected:
            logger.warning("QNX MCP server connection failed - limited functionality")
        if not linux_connected:
            logger.warning("Linux MCP server connection failed - limited functionality")
        
        # Generate glue code
        logger.info(f"Generating glue code for {len(functions)} functions...")
        results = await generator.generate_bulk_glue_code(functions)
        
        # Output results
        full_code = results["header_code"] + "\n" + results["function_code"]
        
        if output_file:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(full_code)
            logger.info(f"Generated code written to: {output_path}")
            
            # Also write migration report
            report_path = output_path.with_suffix('.json')
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "migration_plans": {k: {
                        "qnx_function": v.qnx_function,
                        "linux_function": v.linux_function,
                        "strategy": v.strategy.value,
                        "confidence": v.confidence,
                        "notes": v.notes
                    } for k, v in results["migration_plans"].items()},
                    "statistics": results["statistics"]
                }, f, indent=2)
            logger.info(f"Migration report written to: {report_path}")
        else:
            print("=== Generated Glue Code ===")
            print(full_code)
            print("\n=== Migration Statistics ===")
            print(json.dumps(results["statistics"], indent=2))
        
        # Cleanup
        await qnx_client.disconnect()
        await linux_client.disconnect()
        
        return results
        
    except Exception as e:
        logger.error(f"Error generating glue code: {e}")
        raise

async def list_available_functions():
    """List available QNX functions"""
    try:
        qnx_client = QNXMCPClient()
        if await qnx_client.connect():
            # This would query available functions
            logger.info("Available QNX functions: (placeholder - implement MCP call)")
            await qnx_client.disconnect()
        else:
            logger.error("Could not connect to QNX MCP server")
    except Exception as e:
        logger.error(f"Error listing functions: {e}")

async def test_system():
    """Test the system with a few sample functions"""
    test_functions = [
        "malloc", "free", "printf", "sprintf", 
        "pthread_create", "pthread_join",
        "sem_init", "sem_wait", "sem_post"
    ]
    
    logger.info("Running system test...")
    results = await generate_glue_code(test_functions, "output/test_glue_code.c")
    
    print("\n=== System Test Results ===")
    stats = results["statistics"]
    print(f"Total functions processed: {stats['total_functions']}")
    print(f"Successful migrations: {stats['successful_migrations']}")
    print(f"Failed migrations: {stats['failed_migrations']}")
    print(f"Success rate: {stats['successful_migrations']/stats['total_functions']*100:.1f}%")

def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="Generate QNX to Linux glue code",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py -f malloc free printf -o output/glue.c
  python main.py --functions-file functions.txt --output output/
  python main.py --test
  python main.py --list-functions
        """
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
        help="Output file path for generated code"
    )
    
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run system test with sample functions"
    )
    
    parser.add_argument(
        "--list-functions",
        action="store_true", 
        help="List available QNX functions"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Determine function list
    functions = []
    if args.functions:
        functions.extend(args.functions)
    elif args.functions_file:
        try:
            with open(args.functions_file, 'r') as f:
                functions.extend(line.strip() for line in f if line.strip())
        except Exception as e:
            logger.error(f"Error reading functions file: {e}")
            return 1
    
    # Run appropriate command
    try:
        if args.list_functions:
            asyncio.run(list_available_functions())
        elif args.test:
            asyncio.run(test_system())
        elif functions:
            asyncio.run(generate_glue_code(functions, args.output))
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