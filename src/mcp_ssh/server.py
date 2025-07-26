from mcp.server.fastmcp import Context, FastMCP
from pydantic import BaseModel, Field

from mcp_ssh.ssh import execute_ssh_command, get_ssh_client_from_config


class SSHCommand(BaseModel):
    """SSH command model"""

    command: str = Field(..., description="Command to execute", min_length=1)
    host: str = Field(..., description="Host to execute command on", min_length=1)


class CommandResult(BaseModel):
    """Structured SSH command result"""

    success: bool = Field(..., description="Whether command executed successfully")
    stdout: str = Field(default="", description="Standard output from command")
    stderr: str = Field(default="", description="Standard error from command")
    exit_code: int | None = Field(default=None, description="Command exit code")
    host: str = Field(..., description="Host where command was executed")
    command: str = Field(..., description="Command that was executed")


class FileTransferRequest(BaseModel):
    """File transfer request model"""

    host: str = Field(..., description="Target SSH host")
    local_path: str = Field(..., description="Local file path")
    remote_path: str = Field(..., description="Remote file path")
    direction: str = Field(
        ..., description="Transfer direction: 'upload' or 'download'"
    )


class FileTransferResult(BaseModel):
    """File transfer result"""

    success: bool = Field(..., description="Whether transfer completed successfully")
    bytes_transferred: int = Field(default=0, description="Number of bytes transferred")
    local_path: str = Field(..., description="Local file path")
    remote_path: str = Field(..., description="Remote file path")
    host: str = Field(..., description="SSH host")
    error_message: str = Field(default="", description="Error message if failed")


class HostInfo(BaseModel):
    """SSH host information"""

    name: str = Field(..., description="Host alias name")
    hostname: str = Field(..., description="Actual hostname or IP")
    user: str | None = Field(default=None, description="SSH user")
    port: int = Field(default=22, description="SSH port")


# Create MCP server
mcp = FastMCP("MCP SSH Server")


@mcp.tool()
async def execute_command(cmd: SSHCommand, ctx: Context) -> CommandResult:
    """Execute a command on the SSH server with structured output and progress tracking"""
    await ctx.info(f"Connecting to host: {cmd.host}")

    try:
        await ctx.report_progress(0.3, message="Establishing SSH connection...")
        client = get_ssh_client_from_config(cmd.host)

        if client is None:
            await ctx.error(f"Failed to connect to host '{cmd.host}'")
            return CommandResult(
                success=False,
                stderr=f"Failed to connect to host '{cmd.host}'. Please check your SSH config.",
                host=cmd.host,
                command=cmd.command,
            )

        await ctx.report_progress(0.7, message="Executing command...")
        await ctx.debug(f"Executing: {cmd.command}")
        stdout, stderr = execute_ssh_command(client, cmd.command)
        client.close()

        await ctx.report_progress(1.0, message="Command completed")
        await ctx.info(f"Command executed successfully on {cmd.host}")

        return CommandResult(
            success=True,
            stdout=stdout or "",
            stderr=stderr or "",
            host=cmd.host,
            command=cmd.command,
        )
    except Exception as e:
        await ctx.error(f"Execution failed: {str(e)}")
        return CommandResult(
            success=False,
            stderr=f"Failed to connect to host '{cmd.host}'. Error: {str(e)}",
            host=cmd.host,
            command=cmd.command,
        )


@mcp.tool()
async def transfer_file(
    request: FileTransferRequest, ctx: Context
) -> FileTransferResult:
    """Transfer files between local and remote hosts via SCP"""
    await ctx.info(f"Starting {request.direction} to/from {request.host}")

    try:
        from mcp_ssh.ssh import transfer_file_scp

        await ctx.report_progress(0.2, message="Establishing connection...")
        client = get_ssh_client_from_config(request.host)

        if client is None:
            return FileTransferResult(
                success=False,
                local_path=request.local_path,
                remote_path=request.remote_path,
                host=request.host,
                error_message=f"Failed to connect to host '{request.host}'",
            )

        await ctx.report_progress(0.5, message="Transferring file...")
        bytes_transferred = transfer_file_scp(
            client, request.local_path, request.remote_path, request.direction
        )
        client.close()

        await ctx.report_progress(1.0, message="Transfer completed")
        await ctx.info(f"Successfully transferred {bytes_transferred} bytes")

        return FileTransferResult(
            success=True,
            bytes_transferred=bytes_transferred,
            local_path=request.local_path,
            remote_path=request.remote_path,
            host=request.host,
        )

    except Exception as e:
        await ctx.error(f"Transfer failed: {str(e)}")
        return FileTransferResult(
            success=False,
            local_path=request.local_path,
            remote_path=request.remote_path,
            host=request.host,
            error_message=str(e),
        )


@mcp.resource("ssh://hosts")
def list_ssh_hosts() -> list[HostInfo]:
    """List all available hosts from SSH config with structured data"""
    try:
        from mcp_ssh.ssh import parse_ssh_config

        ssh_configs = parse_ssh_config()

        if not ssh_configs:
            return []

        hosts = []
        for host, config in ssh_configs.items():
            hosts.append(
                HostInfo(
                    name=host,
                    hostname=config.get("hostname", host),
                    user=config.get("user"),
                    port=int(config.get("port", 22)),
                )
            )

        return hosts
    except Exception:
        return []


@mcp.prompt()
def ssh_help() -> str:
    """Get help about using the SSH tools"""
    return """I can help you with SSH operations:

1. List available SSH hosts:
   - Use the 'ssh://hosts' resource to see all configured hosts

2. Execute commands:
   - Use the 'execute_command' tool to run commands on remote hosts
   - Specify the host (from SSH config) and command to execute
   - Example: execute_command(host="your-host", command="ls -la")

3. Transfer files:
   - Use the 'transfer_file' tool to upload/download files
   - Specify host, local_path, remote_path, and direction ("upload" or "download")
   - Example: transfer_file(host="your-host", local_path="/tmp/file.txt", remote_path="/home/user/file.txt", direction="upload")

Example usage:
1. First, check available hosts using the 'ssh://hosts' resource
2. Execute commands using the 'execute_command' tool
3. Transfer files using the 'transfer_file' tool

All operations provide structured output with detailed progress tracking!

Would you like to try any of these operations?"""


def main() -> None:
    """Main entry point for the MCP server"""
    import sys
    from typing import Literal

    # Support transport selection via command line
    transport: Literal["stdio", "sse", "streamable-http"] = "stdio"  # default
    if len(sys.argv) > 1 and sys.argv[1] in ["stdio", "sse", "streamable-http"]:
        transport = sys.argv[1]  # type: ignore[assignment]

    mcp.run(transport=transport)


if __name__ == "__main__":
    main()
