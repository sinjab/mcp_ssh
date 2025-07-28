import asyncio
import os
import time
from datetime import datetime

from mcp.server.fastmcp import Context, FastMCP
from pydantic import BaseModel, Field

from mcp_ssh.ssh import get_ssh_client_from_config

from .background import process_manager
from .security import validate_command, get_validator
from .ssh import (
    cleanup_process_files,
    execute_command_background,
    get_output_chunk,
    get_process_output,
    kill_background_process,
)

# Configuration from environment variables
MAX_OUTPUT_SIZE = int(os.getenv("MCP_SSH_MAX_OUTPUT_SIZE", "50000"))  # 50KB default
QUICK_WAIT_TIME = int(os.getenv("MCP_SSH_QUICK_WAIT_TIME", "5"))  # 5 seconds default
CHUNK_SIZE = int(os.getenv("MCP_SSH_CHUNK_SIZE", "10000"))  # 10KB chunks default

# Timeout configuration
SSH_CONNECT_TIMEOUT = int(
    os.getenv("MCP_SSH_CONNECT_TIMEOUT", "30")
)  # 30 seconds default
SSH_COMMAND_TIMEOUT = int(
    os.getenv("MCP_SSH_COMMAND_TIMEOUT", "60")
)  # 60 seconds default
SSH_TRANSFER_TIMEOUT = int(
    os.getenv("MCP_SSH_TRANSFER_TIMEOUT", "300")
)  # 5 minutes default
SSH_READ_TIMEOUT = int(os.getenv("MCP_SSH_READ_TIMEOUT", "30"))  # 30 seconds default

# Connection optimization
SSH_CONNECTION_REUSE = os.getenv("MCP_SSH_CONNECTION_REUSE", "false").lower() == "true"


class SSHCommand(BaseModel):
    """SSH command model"""

    command: str = Field(..., description="Command to execute", min_length=1)
    host: str = Field(..., description="Host to execute command on", min_length=1)


class CommandRequest(BaseModel):
    host: str = Field(..., min_length=1, max_length=253)
    command: str = Field(..., min_length=1, max_length=2000)


class CommandResult(BaseModel):
    success: bool
    process_id: str
    status: str  # 'running', 'completed', 'failed'
    stdout: str = ""
    stderr: str = ""
    exit_code: int | None = None
    execution_time: float = 0.0
    output_size: int = 0
    has_more_output: bool = False
    chunk_start: int = 0
    error_message: str = ""


class GetOutputRequest(BaseModel):
    process_id: str = Field(..., min_length=1, max_length=50)
    start_byte: int = Field(default=0, ge=0)
    chunk_size: int | None = Field(default=None, ge=1, le=100000)


class KillProcessRequest(BaseModel):
    process_id: str = Field(..., min_length=1, max_length=50)
    cleanup_files: bool = Field(
        default=True, description="Whether to cleanup temporary files"
    )


class KillProcessResult(BaseModel):
    success: bool
    process_id: str
    message: str = ""
    error_message: str = ""


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
async def execute_command(request: CommandRequest, ctx: Context) -> CommandResult:
    """
    Execute SSH command in background. Always returns immediately with process_id.

    Waits briefly for quick commands to complete, then returns current status.
    Use get_command_output to retrieve more data if needed.
    """
    client = None
    start_time = time.time()

    try:
        await ctx.info(f"Starting command on {request.host}")

        # Validate command security
        is_allowed, reason = validate_command(request.command, request.host)
        if not is_allowed:
            await ctx.error(f"Command blocked by security policy: {reason}")
            return CommandResult(
                success=False,
                process_id="",
                status="failed",
                error_message=f"Security policy violation: {reason}",
            )

        # Get SSH connection
        client = get_ssh_client_from_config(request.host)
        if not client:
            return CommandResult(
                success=False,
                process_id="",
                status="failed",
                error_message="Failed to establish SSH connection",
            )

        # Start background process tracking
        process_id = process_manager.start_process(request.host, request.command)
        process = process_manager.get_process(process_id)

        if not process:
            raise RuntimeError("Failed to create process tracking")

        await ctx.report_progress(0.3)

        # Execute in background
        pid = execute_command_background(
            client, request.command, process.output_file, process.error_file
        )

        # Update process with PID
        process_manager.update_process(process_id, pid=pid)

        await ctx.report_progress(0.6)

        # Wait briefly for quick commands with timeout
        try:
            await asyncio.wait_for(
                asyncio.sleep(QUICK_WAIT_TIME), timeout=QUICK_WAIT_TIME + 5
            )
        except TimeoutError:
            await ctx.warning(
                f"Quick wait timed out after {QUICK_WAIT_TIME + 5} seconds"
            )

        # Check current status
        status, output, errors, exit_code = get_process_output(
            client, process, MAX_OUTPUT_SIZE
        )

        # Update process status
        process_manager.update_process(process_id, status=status, exit_code=exit_code)

        execution_time = time.time() - start_time

        # Determine if output was truncated
        output_size = len(output)
        has_more = output_size >= MAX_OUTPUT_SIZE

        await ctx.report_progress(1.0)

        return CommandResult(
            success=True,
            process_id=process_id,
            status=status,
            stdout=output,
            stderr=errors,
            exit_code=exit_code,
            execution_time=execution_time,
            output_size=output_size,
            has_more_output=has_more,
            chunk_start=0,
        )

    except Exception as e:
        execution_time = time.time() - start_time
        await ctx.error(f"Command execution failed: {str(e)}")
        return CommandResult(
            success=False,
            process_id=process_id if "process_id" in locals() else "",
            status="failed",
            error_message=str(e),
            execution_time=execution_time,
        )
    finally:
        if client and not SSH_CONNECTION_REUSE:
            client.close()


@mcp.tool()
async def get_command_output(request: GetOutputRequest, ctx: Context) -> CommandResult:
    """
    Get output from a background command, with optional chunking.

    If chunk_size not specified, uses environment default.
    Returns specific chunk starting from start_byte.
    """
    client = None

    try:
        process = process_manager.get_process(request.process_id)
        if not process:
            return CommandResult(
                success=False,
                process_id=request.process_id,
                status="failed",
                error_message=f"Process {request.process_id} not found",
            )

        await ctx.info(f"Getting output for process {request.process_id}")

        # Get SSH connection
        client = get_ssh_client_from_config(process.host)
        if not client:
            return CommandResult(
                success=False,
                process_id=request.process_id,
                status="failed",
                error_message="Failed to establish SSH connection",
            )

        chunk_size = request.chunk_size or CHUNK_SIZE

        # Get specific chunk with timeout
        try:
            chunk, has_more = get_output_chunk(
                client, process, request.start_byte, chunk_size
            )
        except Exception as e:
            if "timeout" in str(e).lower():
                await ctx.warning(
                    f"Output retrieval timed out after {SSH_READ_TIMEOUT} seconds"
                )
                return CommandResult(
                    success=False,
                    process_id=request.process_id,
                    status="timeout",
                    error_message=f"Output retrieval timed out: {str(e)}",
                )
            raise

        # Check current status
        status, _, errors, exit_code = get_process_output(
            client, process, 1000
        )  # Small check for status

        # Update process status
        process_manager.update_process(
            process.process_id, status=status, exit_code=exit_code
        )

        return CommandResult(
            success=True,
            process_id=request.process_id,
            status=status,
            stdout=chunk,
            stderr=errors,
            exit_code=exit_code,
            output_size=len(chunk),
            has_more_output=has_more,
            chunk_start=request.start_byte,
        )

    except Exception as e:
        await ctx.error(f"Failed to get output: {str(e)}")
        return CommandResult(
            success=False,
            process_id=request.process_id,
            status="failed",
            error_message=str(e),
        )
    finally:
        if client and not SSH_CONNECTION_REUSE:
            client.close()


@mcp.tool()
async def get_command_status(request: GetOutputRequest, ctx: Context) -> CommandResult:
    """
    Get just the status of a background command without output.

    Lightweight check for process completion and basic info.
    """
    client = None

    try:
        process = process_manager.get_process(request.process_id)
        if not process:
            return CommandResult(
                success=False,
                process_id=request.process_id,
                status="failed",
                error_message=f"Process {request.process_id} not found",
            )

        # Get SSH connection
        client = get_ssh_client_from_config(process.host)
        if not client:
            return CommandResult(
                success=False,
                process_id=request.process_id,
                status="failed",
                error_message="Failed to establish SSH connection",
            )

        # Quick status check only with timeout
        try:
            status, _, _, exit_code = get_process_output(
                client, process, 100
            )  # Minimal output for status
        except Exception as e:
            if "timeout" in str(e).lower():
                await ctx.warning(
                    f"Status check timed out after {SSH_READ_TIMEOUT} seconds"
                )
                return CommandResult(
                    success=False,
                    process_id=request.process_id,
                    status="timeout",
                    error_message=f"Status check timed out: {str(e)}",
                )
            raise

        # Update process status
        process_manager.update_process(
            process.process_id, status=status, exit_code=exit_code
        )

        execution_time = (datetime.now() - process.start_time).total_seconds()

        return CommandResult(
            success=True,
            process_id=request.process_id,
            status=status,
            exit_code=exit_code,
            execution_time=execution_time,
        )

    except Exception as e:
        await ctx.error(f"Failed to get status: {str(e)}")
        return CommandResult(
            success=False,
            process_id=request.process_id,
            status="failed",
            error_message=str(e),
        )
    finally:
        if client and not SSH_CONNECTION_REUSE:
            client.close()


@mcp.tool()
async def kill_command(request: KillProcessRequest, ctx: Context) -> KillProcessResult:
    """
    Kill a running background command.

    Uses escalating signals: SIGTERM (graceful) -> SIGKILL (force).
    Optionally cleans up temporary files.
    """
    client = None

    try:
        process = process_manager.get_process(request.process_id)
        if not process:
            return KillProcessResult(
                success=False,
                process_id=request.process_id,
                error_message=f"Process {request.process_id} not found",
            )

        await ctx.info(f"Killing process {request.process_id}")

        # Check current status first
        if process.status not in ["running"]:
            # Update status by checking if still actually running
            client = get_ssh_client_from_config(process.host)
            if client and process.pid:
                stdin, stdout, stderr = client.exec_command(
                    f"kill -0 {process.pid} 2>/dev/null && echo 'RUNNING' || echo 'STOPPED'"
                )
                status_check = stdout.read().decode().strip()
                if status_check == "STOPPED":
                    process_manager.update_process(
                        request.process_id, status="completed"
                    )
                    return KillProcessResult(
                        success=False,
                        process_id=request.process_id,
                        error_message=f"Process {request.process_id} is not running (status: {process.status})",
                    )

        # Get SSH connection if not already established
        if not client:
            client = get_ssh_client_from_config(process.host)
        if not client:
            return KillProcessResult(
                success=False,
                process_id=request.process_id,
                error_message="Failed to establish SSH connection",
            )

        await ctx.report_progress(0.5)

        # Kill the process with timeout
        try:
            killed, message = kill_background_process(client, process)
        except Exception as e:
            if "timeout" in str(e).lower():
                await ctx.warning(
                    f"Process kill operation timed out after {SSH_COMMAND_TIMEOUT} seconds"
                )
                return KillProcessResult(
                    success=False,
                    process_id=request.process_id,
                    error_message=f"Process kill operation timed out: {str(e)}",
                )
            raise

        if killed:
            # Update process status
            process_manager.update_process(request.process_id, status="killed")

            # Clean up files if requested
            cleanup_message = ""
            if request.cleanup_files:
                await ctx.report_progress(0.8)
                cleaned = cleanup_process_files(client, process)
                if cleaned:
                    cleanup_message = " Files cleaned up."
                else:
                    cleanup_message = " Warning: Failed to clean up some files."

            await ctx.info(f"Process {request.process_id} killed successfully")

            return KillProcessResult(
                success=True,
                process_id=request.process_id,
                message=message + cleanup_message,
            )
        else:
            return KillProcessResult(
                success=False,
                process_id=request.process_id,
                error_message=message,
            )

    except Exception as e:
        await ctx.error(f"Failed to kill process: {str(e)}")
        return KillProcessResult(
            success=False,
            process_id=request.process_id,
            error_message=str(e),
        )
    finally:
        if client and not SSH_CONNECTION_REUSE:
            client.close()


@mcp.tool()
async def transfer_file(
    request: FileTransferRequest, ctx: Context
) -> FileTransferResult:
    """Transfer files between local and remote hosts via SCP"""
    await ctx.info(f"Starting {request.direction} to/from {request.host}")

    try:
        from mcp_ssh.ssh import transfer_file_scp

        await ctx.report_progress(0.2)
        client = get_ssh_client_from_config(request.host)

        if client is None:
            return FileTransferResult(
                success=False,
                local_path=request.local_path,
                remote_path=request.remote_path,
                host=request.host,
                error_message=f"Failed to connect to host '{request.host}'",
            )

        await ctx.report_progress(0.5)
        try:
            bytes_transferred = transfer_file_scp(
                client, request.local_path, request.remote_path, request.direction
            )
        except Exception as e:
            if "timeout" in str(e).lower():
                await ctx.warning(
                    f"File transfer timed out after {SSH_TRANSFER_TIMEOUT} seconds"
                )
                return FileTransferResult(
                    success=False,
                    local_path=request.local_path,
                    remote_path=request.remote_path,
                    host=request.host,
                    error_message=f"File transfer timed out: {str(e)}",
                )
            raise
        finally:
            if not SSH_CONNECTION_REUSE:
                client.close()

        await ctx.report_progress(1.0)
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

2. Execute commands (Background Execution):
   - Use the 'execute_command' tool to run commands in background
   - All commands run in background and return immediately with process_id
   - Waits briefly for quick commands to complete
   - Example: execute_command(host="your-host", command="ls -la")

3. Get command output:
   - Use 'get_command_output' to retrieve output from background commands
   - Supports chunking for large outputs
   - Example: get_command_output(process_id="abc123", start_byte=0, chunk_size=10000)

4. Check command status:
   - Use 'get_command_status' to check if a command is still running
   - Lightweight check without retrieving output
   - Example: get_command_status(process_id="abc123")

5. Kill running commands:
   - Use 'kill_command' to terminate running background processes
   - Uses graceful termination (SIGTERM) then force kill (SIGKILL)
   - Optionally cleans up temporary files
   - Example: kill_command(process_id="abc123", cleanup_files=true)

6. Transfer files:
   - Use 'transfer_file' to upload/download files via SCP
   - Example: transfer_file(host="your-host", local_path="/local/file", remote_path="/remote/file", direction="upload")

Background Execution Features:
- All commands run in background with process tracking
- Configurable output size limits and chunking
- Process IDs for tracking and management
- Automatic cleanup of temporary files
- Escalating kill signals for reliable termination

Performance Features:
- Connection reuse for faster subsequent operations
- Configurable connection pooling
- Comprehensive timeout protection
- Optimized output reading with retry logic

Environment Configuration:
- MCP_SSH_MAX_OUTPUT_SIZE: Maximum output size before chunking (default: 50KB)
- MCP_SSH_QUICK_WAIT_TIME: Wait time for quick commands (default: 5 seconds)
- MCP_SSH_CHUNK_SIZE: Default chunk size for output retrieval (default: 10KB)
- MCP_SSH_CONNECT_TIMEOUT: SSH connection timeout in seconds (default: 30)
- MCP_SSH_COMMAND_TIMEOUT: SSH command execution timeout in seconds (default: 60)
- MCP_SSH_TRANSFER_TIMEOUT: File transfer timeout in seconds (default: 300)
- MCP_SSH_READ_TIMEOUT: Output reading timeout in seconds (default: 30)

Security Configuration:
- MCP_SSH_SECURITY_MODE: Security mode - 'blacklist', 'whitelist', or 'disabled' (default: blacklist)
- MCP_SSH_COMMAND_BLACKLIST: Semicolon-separated regex patterns for blocked commands
- MCP_SSH_COMMAND_WHITELIST: Semicolon-separated regex patterns for allowed commands
- MCP_SSH_CASE_SENSITIVE: Whether pattern matching is case sensitive (default: false)
"""


@mcp.tool()
async def get_security_info() -> dict:
    """Get current security configuration and validation rules"""
    validator = get_validator()
    return validator.get_security_info()


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
