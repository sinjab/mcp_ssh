import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Test environment variables
os.environ["MCP_SSH_MAX_OUTPUT_SIZE"] = "1000"
os.environ["MCP_SSH_QUICK_WAIT_TIME"] = "1"
os.environ["MCP_SSH_CHUNK_SIZE"] = "500"

from mcp_ssh.background import BackgroundProcess, BackgroundProcessManager
from mcp_ssh.server import (
    CommandRequest,
    GetOutputRequest,
    KillProcessRequest,
    execute_command,
    get_command_output,
    get_command_status,
    kill_command,
)


@pytest.mark.asyncio
class TestBackgroundExecution:

    @patch("mcp_ssh.server.get_ssh_client_from_config")
    @patch("mcp_ssh.server.execute_command_background")
    @patch("mcp_ssh.server.get_process_output")
    async def test_execute_command_quick_completion(
        self, mock_get_output, mock_execute_bg, mock_get_client
    ):
        """Test command that completes quickly."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_execute_bg.return_value = 12345
        mock_get_output.return_value = ("completed", "file1\nfile2\n", "", 0)

        request = CommandRequest(host="test-host", command="ls -la")
        mock_context = AsyncMock()

        result = await execute_command(request, mock_context)

        assert result.success is True
        assert result.status == "completed"
        assert result.process_id != ""
        assert "file1" in result.stdout
        assert result.exit_code == 0
        assert result.has_more_output is False

        mock_client.close.assert_called_once()

    @patch("mcp_ssh.server.get_ssh_client_from_config")
    @patch("mcp_ssh.server.execute_command_background")
    @patch("mcp_ssh.server.get_process_output")
    async def test_execute_command_large_output(
        self, mock_get_output, mock_execute_bg, mock_get_client
    ):
        """Test command with output larger than limit."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_execute_bg.return_value = 12345

        # Large output that exceeds 1000 byte limit
        large_output = "x" * 1000  # Exactly at limit
        mock_get_output.return_value = ("completed", large_output, "", 0)

        request = CommandRequest(host="test-host", command="cat large_file")
        mock_context = AsyncMock()

        result = await execute_command(request, mock_context)

        assert result.success is True
        assert result.output_size == 1000
        assert result.has_more_output is True  # Assumes truncation

    @patch("mcp_ssh.server.process_manager")
    @patch("mcp_ssh.server.get_ssh_client_from_config")
    @patch("mcp_ssh.server.get_output_chunk")
    @patch("mcp_ssh.server.get_process_output")
    async def test_get_command_output_chunk(
        self, mock_get_output, mock_get_chunk, mock_get_client, mock_manager
    ):
        """Test getting specific output chunk."""
        # Setup mock process
        mock_process = MagicMock()
        mock_process.host = "test-host"
        mock_manager.get_process.return_value = mock_process

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_get_chunk.return_value = ("chunk_data", True)  # Has more data
        mock_get_output.return_value = (
            "completed",
            "",
            "",
            0,
        )  # status, output, errors, exit_code

        request = GetOutputRequest(process_id="test123", start_byte=500, chunk_size=200)
        mock_context = AsyncMock()

        result = await get_command_output(request, mock_context)

        assert result.success is True
        assert result.stdout == "chunk_data"
        assert result.has_more_output is True
        assert result.chunk_start == 500

        mock_get_chunk.assert_called_once_with(mock_client, mock_process, 500, 200)
        mock_client.close.assert_called_once()

    @patch("mcp_ssh.server.process_manager")
    @patch("mcp_ssh.server.get_ssh_client_from_config")
    @patch("mcp_ssh.server.get_process_output")
    async def test_get_command_status(
        self, mock_get_output, mock_get_client, mock_manager
    ):
        """Test getting command status."""
        # Setup mock process
        mock_process = MagicMock()
        mock_process.host = "test-host"
        mock_process.start_time = MagicMock()
        mock_process.start_time.total_seconds.return_value = 10.5
        mock_manager.get_process.return_value = mock_process

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_get_output.return_value = ("running", "", "", None)

        request = GetOutputRequest(process_id="test123")
        mock_context = AsyncMock()

        result = await get_command_status(request, mock_context)

        assert result.success is True
        assert result.status == "running"
        # Don't test exact execution time as it's calculated from current time
        assert result.execution_time > 0

        mock_client.close.assert_called_once()

    @patch("mcp_ssh.server.process_manager")
    async def test_get_command_output_process_not_found(self, mock_manager):
        """Test getting output for non-existent process."""
        mock_manager.get_process.return_value = None

        request = GetOutputRequest(process_id="nonexistent")
        mock_context = AsyncMock()

        result = await get_command_output(request, mock_context)

        assert result.success is False
        assert result.status == "failed"
        assert "not found" in result.error_message

    @patch("mcp_ssh.server.get_ssh_client_from_config")
    async def test_execute_command_connection_failure(self, mock_get_client):
        """Test command execution when SSH connection fails."""
        mock_get_client.return_value = None

        request = CommandRequest(host="test-host", command="ls -la")
        mock_context = AsyncMock()

        result = await execute_command(request, mock_context)

        assert result.success is False
        assert result.status == "failed"
        assert "Failed to establish SSH connection" in result.error_message

    @patch("mcp_ssh.server.process_manager")
    @patch("mcp_ssh.server.get_ssh_client_from_config")
    @patch("mcp_ssh.server.kill_background_process")
    @patch("mcp_ssh.server.cleanup_process_files")
    async def test_kill_command_success(
        self, mock_cleanup, mock_kill, mock_get_client, mock_manager
    ):
        """Test successfully killing a running process."""
        # Setup mock process
        mock_process = MagicMock()
        mock_process.host = "test-host"
        mock_process.status = "running"
        mock_process.pid = 12345
        mock_manager.get_process.return_value = mock_process

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_kill.return_value = (True, "Process 12345 terminated gracefully")
        mock_cleanup.return_value = True

        request = KillProcessRequest(process_id="test123", cleanup_files=True)
        mock_context = AsyncMock()

        result = await kill_command(request, mock_context)

        assert result.success is True
        assert result.process_id == "test123"
        assert "terminated gracefully" in result.message
        assert "cleaned up" in result.message

        mock_kill.assert_called_once_with(mock_client, mock_process)
        mock_cleanup.assert_called_once_with(mock_client, mock_process)
        mock_manager.update_process.assert_called_with("test123", status="killed")
        mock_client.close.assert_called_once()

    @patch("mcp_ssh.server.process_manager")
    async def test_kill_command_not_found(self, mock_manager):
        """Test killing non-existent process."""
        mock_manager.get_process.return_value = None

        request = KillProcessRequest(process_id="nonexistent")
        mock_context = AsyncMock()

        result = await kill_command(request, mock_context)

        assert result.success is False
        assert "not found" in result.error_message

    @patch("mcp_ssh.server.process_manager")
    @patch("mcp_ssh.server.get_ssh_client_from_config")
    @patch("mcp_ssh.server.kill_background_process")
    async def test_kill_command_already_stopped(
        self, mock_kill, mock_get_client, mock_manager
    ):
        """Test killing process that's already stopped."""
        # Setup mock process that's already completed
        mock_process = MagicMock()
        mock_process.host = "test-host"
        mock_process.status = "completed"
        mock_process.pid = 12345
        mock_manager.get_process.return_value = mock_process

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        # Mock the status check to confirm it's stopped
        mock_stdout = MagicMock()
        mock_stdout.read.return_value = b"STOPPED\n"
        mock_client.exec_command.return_value = (None, mock_stdout, None)

        request = KillProcessRequest(process_id="test123")
        mock_context = AsyncMock()

        result = await kill_command(request, mock_context)

        assert result.success is False
        assert "not running" in result.error_message

        # Should not attempt to kill if already stopped
        mock_kill.assert_not_called()
        mock_client.close.assert_called_once()

    @patch("mcp_ssh.server.process_manager")
    @patch("mcp_ssh.server.get_ssh_client_from_config")
    @patch("mcp_ssh.server.kill_background_process")
    async def test_kill_command_failure(self, mock_kill, mock_get_client, mock_manager):
        """Test killing process that fails."""
        # Setup mock process
        mock_process = MagicMock()
        mock_process.host = "test-host"
        mock_process.status = "running"
        mock_process.pid = 12345
        mock_manager.get_process.return_value = mock_process

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_kill.return_value = (False, "Permission denied")

        request = KillProcessRequest(process_id="test123")
        mock_context = AsyncMock()

        result = await kill_command(request, mock_context)

        assert result.success is False
        assert "Permission denied" in result.error_message

        mock_kill.assert_called_once_with(mock_client, mock_process)
        mock_client.close.assert_called_once()

    @patch("mcp_ssh.server.process_manager")
    @patch("mcp_ssh.server.get_ssh_client_from_config")
    @patch("mcp_ssh.server.kill_background_process")
    @patch("mcp_ssh.server.cleanup_process_files")
    async def test_kill_command_no_cleanup(
        self, mock_cleanup, mock_kill, mock_get_client, mock_manager
    ):
        """Test killing process without cleanup."""
        # Setup mock process
        mock_process = MagicMock()
        mock_process.host = "test-host"
        mock_process.status = "running"
        mock_process.pid = 12345
        mock_manager.get_process.return_value = mock_process

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_kill.return_value = (True, "Process 12345 terminated gracefully")

        request = KillProcessRequest(process_id="test123", cleanup_files=False)
        mock_context = AsyncMock()

        result = await kill_command(request, mock_context)

        assert result.success is True
        assert result.process_id == "test123"
        assert "terminated gracefully" in result.message
        assert "cleaned up" not in result.message

        mock_kill.assert_called_once_with(mock_client, mock_process)
        mock_cleanup.assert_not_called()
        mock_manager.update_process.assert_called_with("test123", status="killed")
        mock_client.close.assert_called_once()

    @patch("mcp_ssh.server.process_manager")
    @patch("mcp_ssh.server.get_ssh_client_from_config")
    async def test_kill_command_connection_failure(self, mock_get_client, mock_manager):
        """Test killing process with connection failure."""
        # Setup mock process
        mock_process = MagicMock()
        mock_process.host = "test-host"
        mock_process.status = "running"
        mock_process.pid = 12345
        mock_manager.get_process.return_value = mock_process

        mock_get_client.return_value = None

        request = KillProcessRequest(process_id="test123")
        mock_context = AsyncMock()

        result = await kill_command(request, mock_context)

        assert result.success is False
        assert "Failed to establish SSH connection" in result.error_message

        mock_get_client.assert_called_once_with("test-host")


class TestBackgroundProcessManager:
    """Test the background process manager."""

    def test_start_process(self):
        """Test starting a new process."""
        manager = BackgroundProcessManager()

        process_id = manager.start_process("test-host", "ls -la")

        assert len(process_id) == 8
        assert process_id in manager.processes

        process = manager.processes[process_id]
        assert process.host == "test-host"
        assert process.command == "ls -la"
        assert process.status == "running"
        assert process.pid is None

    def test_get_process(self):
        """Test getting a process by ID."""
        manager = BackgroundProcessManager()

        # Get non-existent process
        process = manager.get_process("nonexistent")
        assert process is None

        # Start and get process
        process_id = manager.start_process("test-host", "ls -la")
        process = manager.get_process(process_id)

        assert process is not None
        assert process.host == "test-host"

    def test_update_process(self):
        """Test updating process information."""
        manager = BackgroundProcessManager()
        process_id = manager.start_process("test-host", "ls -la")

        # Update PID
        manager.update_process(process_id, pid=12345)
        process = manager.get_process(process_id)
        assert process.pid == 12345

        # Update status
        manager.update_process(process_id, status="completed")
        process = manager.get_process(process_id)
        assert process.status == "completed"

        # Update exit code
        manager.update_process(process_id, exit_code=0)
        process = manager.get_process(process_id)
        assert process.exit_code == 0


class TestBackgroundProcess:
    """Test the background process dataclass."""

    def test_background_process_creation(self):
        """Test creating a background process."""
        from datetime import datetime

        process = BackgroundProcess(
            process_id="test123",
            host="test-host",
            command="ls -la",
            pid=12345,
            start_time=datetime.now(),
            status="running",
            output_file="/tmp/test.out",
            error_file="/tmp/test.err",
        )

        assert process.process_id == "test123"
        assert process.host == "test-host"
        assert process.command == "ls -la"
        assert process.pid == 12345
        assert process.status == "running"
        assert process.output_file == "/tmp/test.out"
        assert process.error_file == "/tmp/test.err"
        assert process.exit_code is None
