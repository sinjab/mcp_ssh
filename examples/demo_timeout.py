#!/usr/bin/env python3
"""
Demo script showing MCP SSH timeout functionality

This script demonstrates how the MCP SSH server now has comprehensive
timeout protection to prevent hanging operations.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from mcp_ssh.server import (
    CommandRequest,
    GetOutputRequest,
    KillProcessRequest,
    execute_command,
    get_command_output,
    get_command_status,
    kill_command,
)


class DemoContext:
    """Mock MCP context for demo purposes."""

    async def info(self, message: str):
        print(f"ℹ️  INFO: {message}")

    async def warning(self, message: str):
        print(f"⚠️  WARNING: {message}")

    async def error(self, message: str):
        print(f"❌ ERROR: {message}")

    async def debug(self, message: str):
        print(f"🐛 DEBUG: {message}")

    async def report_progress(self, progress: float, message: str = ""):
        print(f"📊 Progress: {progress:.1f} - {message}")


async def demo_timeout_functionality():
    """Demonstrate timeout functionality."""
    print("🚀 MCP SSH Timeout Demo")
    print("=" * 50)
    
    ctx = DemoContext()
    
    # Set up test environment variables
    os.environ["MCP_SSH_CONNECT_TIMEOUT"] = "10"  # 10 seconds
    os.environ["MCP_SSH_COMMAND_TIMEOUT"] = "15"  # 15 seconds
    os.environ["MCP_SSH_READ_TIMEOUT"] = "10"     # 10 seconds
    os.environ["MCP_SSH_TRANSFER_TIMEOUT"] = "60" # 60 seconds
    
    print("\n📋 Timeout Configuration:")
    print(f"  • Connection timeout: {os.environ.get('MCP_SSH_CONNECT_TIMEOUT', '30')}s")
    print(f"  • Command timeout: {os.environ.get('MCP_SSH_COMMAND_TIMEOUT', '60')}s")
    print(f"  • Read timeout: {os.environ.get('MCP_SSH_READ_TIMEOUT', '30')}s")
    print(f"  • Transfer timeout: {os.environ.get('MCP_SSH_TRANSFER_TIMEOUT', '300')}s")
    
    print("\n🔧 All MCP SSH tools now have timeout protection:")
    print("  • execute_command - Command execution timeout")
    print("  • get_command_output - Output reading timeout")
    print("  • get_command_status - Status check timeout")
    print("  • kill_command - Process termination timeout")
    print("  • transfer_file - File transfer timeout")
    
    print("\n✅ Benefits:")
    print("  • No more hanging operations")
    print("  • Configurable timeouts via environment variables")
    print("  • Graceful error handling with timeout messages")
    print("  • Automatic cleanup on timeout")
    
    print("\n🎯 Example timeout scenarios:")
    print("  • Network connectivity issues")
    print("  • Slow SSH servers")
    print("  • Long-running commands")
    print("  • Large file transfers")
    print("  • Process termination delays")
    
    print("\n💡 Usage:")
    print("  # Set custom timeouts")
    print("  export MCP_SSH_CONNECT_TIMEOUT=30")
    print("  export MCP_SSH_COMMAND_TIMEOUT=120")
    print("  export MCP_SSH_READ_TIMEOUT=60")
    print("  export MCP_SSH_TRANSFER_TIMEOUT=600")
    print("  ")
    print("  # Run MCP server with timeouts")
    print("  uv run mcp_ssh")
    
    print("\n✨ Timeout protection is now enabled by default!")
    print("   All operations will respect the configured timeout limits.")


if __name__ == "__main__":
    asyncio.run(demo_timeout_functionality()) 