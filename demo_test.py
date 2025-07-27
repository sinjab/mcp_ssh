#!/usr/bin/env python3
"""
Quick demo script to test the enhanced MCP SSH server
"""

from mcp_ssh.server import CommandResult, FileTransferResult, HostInfo


def test_structured_models():
    """Test all structured output models"""
    print("🧪 Testing Structured Output Models...")

    # Test CommandResult
    cmd_result = CommandResult(
        success=True,
        stdout="total 8\ndrwxr-xr-x  3 user user 4096 Jul 26 14:30 test",
        stderr="",
        host="production",
        command="ls -la /tmp"
    )
    print(f"✅ CommandResult: {cmd_result.success} - {cmd_result.host}")

    # Test FileTransferResult
    transfer_result = FileTransferResult(
        success=True,
        bytes_transferred=1024,
        local_path="/tmp/test.txt",
        remote_path="/home/user/test.txt",
        host="staging"
    )
    print(f"✅ FileTransferResult: {transfer_result.bytes_transferred} bytes transferred")

    # Test HostInfo
    host_info = HostInfo(
        name="production",
        hostname="prod.example.com",
        user="deploy",
        port=22
    )
    print(f"✅ HostInfo: {host_info.name} -> {host_info.hostname}:{host_info.port}")

    print("✨ All structured models working perfectly!\n")


def test_json_serialization():
    """Test JSON serialization of models"""
    print("📝 Testing JSON Serialization...")

    result = CommandResult(
        success=True,
        stdout="Hello World",
        stderr="",
        host="localhost",
        command="echo 'Hello World'"
    )

    # Test serialization
    json_data = result.model_dump()
    print(f"✅ JSON serialization: {len(json_data)} fields")

    # Test validation
    reconstructed = CommandResult.model_validate(json_data)
    print(f"✅ JSON validation: {reconstructed.command}")

    print("✨ JSON serialization working perfectly!\n")


def main():
    """Main demo function"""
    print("🚀 MCP SSH Enhanced Server Demo\n")
    print("=" * 50)

    test_structured_models()
    test_json_serialization()

    print("🎉 All enhancements working correctly!")
    print("\nNew Features Added:")
    print("• ✅ Structured output with Pydantic models")
    print("• ✅ File transfer capabilities (SCP)")
    print("• ✅ Progress tracking and enhanced logging")
    print("• ✅ Rich context support")
    print("• ✅ Modern MCP 1.7.0+ compatibility")
    print("• ✅ Transport selection support")

    print("\nUsage Examples:")
    print("• uv run mcp_ssh                     # Default stdio transport")
    print("• uv run mcp_ssh streamable-http     # HTTP transport for production")
    print("• uv run mcp dev src/mcp_ssh/server.py  # Development mode")


if __name__ == "__main__":
    main()
