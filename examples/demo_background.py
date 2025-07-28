#!/usr/bin/env python3
"""
Demo script for MCP SSH Background Execution

This script demonstrates the new background execution capabilities
of the MCP SSH server.
"""

import asyncio
import os

from mcp_ssh.server import (
    CommandRequest,
)

# Set environment variables for demo
os.environ["MCP_SSH_MAX_OUTPUT_SIZE"] = "1000"  # Small limit for demo
os.environ["MCP_SSH_QUICK_WAIT_TIME"] = "1"     # Quick wait for demo
os.environ["MCP_SSH_CHUNK_SIZE"] = "500"        # Small chunks for demo


async def demo_quick_command():
    """Demo a quick command that completes within the wait time."""
    print("=== Demo 1: Quick Command ===")

    # This would normally connect to a real SSH host
    # For demo purposes, we'll show the structure
    request = CommandRequest(host="demo-host", command="ls -la")

    print(f"Starting command: {request.command}")
    print("Command runs in background and waits briefly for completion...")

    # In a real scenario, this would execute the command
    # result = await execute_command(request, mock_context)
    print("Result would include:")
    print("- process_id: for tracking")
    print("- status: 'completed' for quick commands")
    print("- stdout: command output")
    print("- has_more_output: false for small outputs")


async def demo_long_command():
    """Demo a long-running command with chunked output."""
    print("\n=== Demo 2: Long Command with Chunking ===")

    request = CommandRequest(host="demo-host", command="find / -name '*.log' 2>/dev/null")

    print(f"Starting long command: {request.command}")
    print("Command runs in background, returns immediately...")

    # In a real scenario:
    # result = await execute_command(request, mock_context)
    # print(f"Process ID: {result.process_id}")
    # print(f"Status: {result.status}")
    # print(f"Initial output size: {result.output_size}")
    # print(f"Has more output: {result.has_more_output}")

    print("Result would include:")
    print("- process_id: for tracking")
    print("- status: 'running' initially")
    print("- stdout: first chunk of output")
    print("- has_more_output: true for large outputs")

    print("\nLater, check status:")
    # status_request = GetOutputRequest(process_id=result.process_id)
    # status = await get_command_status(status_request, mock_context)
    # print(f"Status: {status.status}")

    print("\nGet more output in chunks:")
    # output_request = GetOutputRequest(
    #     process_id=result.process_id,
    #     start_byte=len(result.stdout),
    #     chunk_size=500
    # )
    # more_output = await get_command_output(output_request, mock_context)
    # print(f"Next chunk: {more_output.stdout}")


async def demo_kill_command():
    """Demo killing a running background command."""
    print("\n=== Demo 3: Kill Command ===")

    request = CommandRequest(host="demo-host", command="sleep 100")

    print(f"Starting long-running command: {request.command}")
    print("Command runs in background, returns immediately...")

    # In a real scenario:
    # result = await execute_command(request, mock_context)
    # print(f"Process ID: {result.process_id}")
    # print(f"Status: {result.status}")

    print("Result would include:")
    print("- process_id: for tracking")
    print("- status: 'running' for long commands")

    print("\nLater, kill the command:")
    # kill_request = KillProcessRequest(
    #     process_id=result.process_id,
    #     cleanup_files=True
    # )
    # kill_result = await kill_command(kill_request, mock_context)
    # print(f"Kill success: {kill_result.success}")
    # print(f"Kill message: {kill_result.message}")

    print("Kill result would include:")
    print("- success: true if killed successfully")
    print("- message: details about termination (graceful/force)")
    print("- cleanup: automatic file cleanup if requested")


async def demo_error_handling():
    """Demo error handling in background execution."""
    print("\n=== Demo 4: Error Handling ===")

    request = CommandRequest(host="nonexistent-host", command="ls -la")

    print(f"Starting command on non-existent host: {request.host}")

    # In a real scenario:
    # result = await execute_command(request, mock_context)
    # print(f"Success: {result.success}")
    # print(f"Error: {result.error_message}")

    print("Result would include:")
    print("- success: false")
    print("- status: 'failed'")
    print("- error_message: connection failure details")


def demo_environment_config():
    """Demo environment variable configuration."""
    print("\n=== Demo 5: Environment Configuration ===")

    print("Configure background execution behavior:")
    print("export MCP_SSH_MAX_OUTPUT_SIZE=50000    # 50KB output limit")
    print("export MCP_SSH_QUICK_WAIT_TIME=5        # 5 second wait for quick commands")
    print("export MCP_SSH_CHUNK_SIZE=10000         # 10KB chunks for large outputs")

    print("\nCurrent demo settings:")
    print(f"MCP_SSH_MAX_OUTPUT_SIZE: {os.environ.get('MCP_SSH_MAX_OUTPUT_SIZE', '50000')}")
    print(f"MCP_SSH_QUICK_WAIT_TIME: {os.environ.get('MCP_SSH_QUICK_WAIT_TIME', '5')}")
    print(f"MCP_SSH_CHUNK_SIZE: {os.environ.get('MCP_SSH_CHUNK_SIZE', '10000')}")


async def main():
    """Run all demos."""
    print("🚀 MCP SSH Background Execution Demo")
    print("=" * 50)

    await demo_quick_command()
    await demo_long_command()
    await demo_kill_command()
    await demo_error_handling()
    demo_environment_config()

    print("\n" + "=" * 50)
    print("✅ Demo completed!")
    print("\nTo use these features:")
    print("1. Set up SSH config with your hosts")
    print("2. Run: uv run mcp dev src/mcp_ssh/server.py")
    print("3. Use the MCP tools in your client application")


if __name__ == "__main__":
    asyncio.run(main())
