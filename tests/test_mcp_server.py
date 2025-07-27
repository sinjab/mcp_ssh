"""
Tests for MCP server functionality

This module tests the MCP tools, resources, prompts, and server integration.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from mcp_ssh.server import (
    CommandRequest,
    CommandResult,
    FileTransferRequest,
    FileTransferResult,
    HostInfo,
    SSHCommand,
    execute_command,
    list_ssh_hosts,
    mcp,
    transfer_file,
)


class TestMCPTools:
    """Test MCP tool functions"""

    @patch("mcp_ssh.server.get_ssh_client_from_config")
    @patch("mcp_ssh.server.execute_command_background")
    @patch("mcp_ssh.server.get_process_output")
    @pytest.mark.asyncio
    async def test_execute_command_success(
        self, mock_get_output, mock_execute_bg, mock_client
    ):
        """Test successful command execution"""
        mock_client.return_value = MagicMock()
        mock_execute_bg.return_value = 12345
        mock_get_output.return_value = ("completed", "command output", "", 0)

        request = CommandRequest(command="ls -la", host="test-host")

        # Mock context with async methods
        mock_ctx = MagicMock()
        mock_ctx.info = AsyncMock()
        mock_ctx.report_progress = AsyncMock()
        mock_ctx.debug = AsyncMock()
        mock_ctx.error = AsyncMock()

        result = await execute_command(request, mock_ctx)

        assert isinstance(result, CommandResult)
        assert result.success is True
        assert result.stdout == "command output"
        assert result.stderr == ""
        assert result.exit_code == 0
        assert result.process_id != ""
        assert result.status == "completed"
        mock_client.assert_called_once_with("test-host")

    @patch("mcp_ssh.server.get_ssh_client_from_config")
    @pytest.mark.asyncio
    async def test_execute_command_no_host(self, mock_client):
        """Test command execution when host connection fails"""
        mock_client.return_value = None

        request = CommandRequest(command="ls", host="nonexistent")

        # Mock context with async methods
        mock_ctx = MagicMock()
        mock_ctx.info = AsyncMock()
        mock_ctx.report_progress = AsyncMock()
        mock_ctx.debug = AsyncMock()
        mock_ctx.error = AsyncMock()

        result = await execute_command(request, mock_ctx)

        assert isinstance(result, CommandResult)
        assert result.success is False
        assert "Failed to establish SSH connection" in result.error_message

    @patch("mcp_ssh.server.get_ssh_client_from_config")
    @patch("mcp_ssh.server.execute_command_background")
    @patch("mcp_ssh.server.get_process_output")
    @pytest.mark.asyncio
    async def test_execute_command_with_stderr(
        self, mock_get_output, mock_execute_bg, mock_client
    ):
        """Test command execution with stderr output"""
        mock_client.return_value = MagicMock()
        mock_execute_bg.return_value = 12345
        mock_get_output.return_value = (
            "completed",
            "stdout output",
            "stderr output",
            0,
        )

        request = CommandRequest(command="ls /nonexistent", host="test-host")

        # Mock context with async methods
        mock_ctx = MagicMock()
        mock_ctx.info = AsyncMock()
        mock_ctx.report_progress = AsyncMock()
        mock_ctx.debug = AsyncMock()
        mock_ctx.error = AsyncMock()

        result = await execute_command(request, mock_ctx)

        assert isinstance(result, CommandResult)
        assert result.success is True
        assert result.stdout == "stdout output"
        assert result.stderr == "stderr output"
        assert result.exit_code == 0

    @patch("mcp_ssh.server.get_ssh_client_from_config")
    @patch("mcp_ssh.server.execute_command_background")
    @patch("mcp_ssh.server.get_process_output")
    @pytest.mark.asyncio
    async def test_execute_command_no_output(
        self, mock_get_output, mock_execute_bg, mock_client
    ):
        """Test command execution with no output"""
        mock_client.return_value = MagicMock()
        mock_execute_bg.return_value = 12345
        mock_get_output.return_value = ("completed", "", "", 0)

        request = CommandRequest(command="touch /tmp/test", host="test-host")

        # Mock context with async methods
        mock_ctx = MagicMock()
        mock_ctx.info = AsyncMock()
        mock_ctx.report_progress = AsyncMock()
        mock_ctx.debug = AsyncMock()
        mock_ctx.error = AsyncMock()

        result = await execute_command(request, mock_ctx)

        assert isinstance(result, CommandResult)
        assert result.success is True
        assert result.stdout == ""
        assert result.stderr == ""
        assert result.exit_code == 0

    @patch("mcp_ssh.server.get_ssh_client_from_config")
    @patch("mcp_ssh.server.execute_command_background")
    @patch("mcp_ssh.server.get_process_output")
    @pytest.mark.asyncio
    async def test_execute_command_only_stderr(
        self, mock_get_output, mock_execute_bg, mock_client
    ):
        """Test command execution with only stderr output"""
        mock_client.return_value = MagicMock()
        mock_execute_bg.return_value = 12345
        mock_get_output.return_value = ("completed", "", "error only", 1)

        request = CommandRequest(command="invalid-command", host="test-host")

        # Mock context with async methods
        mock_ctx = MagicMock()
        mock_ctx.info = AsyncMock()
        mock_ctx.report_progress = AsyncMock()
        mock_ctx.debug = AsyncMock()
        mock_ctx.error = AsyncMock()

        result = await execute_command(request, mock_ctx)

        assert isinstance(result, CommandResult)
        assert result.success is True  # Command executed, just returned error
        assert result.stdout == ""
        assert result.stderr == "error only"
        assert result.exit_code == 1


class TestFileTransfer:
    """Test file transfer functionality"""

    @patch("mcp_ssh.server.get_ssh_client_from_config")
    @patch("mcp_ssh.ssh.transfer_file_scp")
    @pytest.mark.asyncio
    async def test_transfer_file_upload_success(self, mock_transfer, mock_client):
        """Test successful file upload with source validation"""
        mock_client.return_value = MagicMock()
        mock_transfer.return_value = 1024

        request = FileTransferRequest(
            host="test-host",
            local_path="/tmp/test.txt",
            remote_path="/home/user/test.txt",
            direction="upload",
        )

        # Mock context with async methods
        mock_ctx = MagicMock()
        mock_ctx.info = AsyncMock()
        mock_ctx.report_progress = AsyncMock()
        mock_ctx.error = AsyncMock()

        result = await transfer_file(request, mock_ctx)

        assert isinstance(result, FileTransferResult)
        assert result.success is True
        assert result.bytes_transferred == 1024
        assert result.local_path == "/tmp/test.txt"
        assert result.remote_path == "/home/user/test.txt"
        assert result.host == "test-host"
        assert result.error_message == ""

        # Verify transfer was called with correct parameters
        mock_transfer.assert_called_once_with(
            mock_client.return_value, "/tmp/test.txt", "/home/user/test.txt", "upload"
        )

    @patch("mcp_ssh.server.get_ssh_client_from_config")
    @patch("mcp_ssh.ssh.transfer_file_scp")
    @pytest.mark.asyncio
    async def test_transfer_file_upload_source_not_exists(
        self, mock_transfer, mock_client
    ):
        """Test file upload when source file doesn't exist"""
        mock_client.return_value = MagicMock()
        # Simulate FileNotFoundError from transfer_file_scp
        mock_transfer.side_effect = FileNotFoundError(
            "Local file does not exist: /tmp/nonexistent.txt"
        )

        request = FileTransferRequest(
            host="test-host",
            local_path="/tmp/nonexistent.txt",
            remote_path="/home/user/test.txt",
            direction="upload",
        )

        # Mock context with async methods
        mock_ctx = MagicMock()
        mock_ctx.info = AsyncMock()
        mock_ctx.report_progress = AsyncMock()
        mock_ctx.error = AsyncMock()

        result = await transfer_file(request, mock_ctx)

        assert isinstance(result, FileTransferResult)
        assert result.success is False
        assert "Local file does not exist" in result.error_message
        assert result.local_path == "/tmp/nonexistent.txt"
        assert result.remote_path == "/home/user/test.txt"
        assert result.host == "test-host"

        # Verify transfer was attempted
        mock_transfer.assert_called_once()

    @patch("mcp_ssh.server.get_ssh_client_from_config")
    @patch("mcp_ssh.ssh.transfer_file_scp")
    @pytest.mark.asyncio
    async def test_transfer_file_upload_source_not_file(
        self, mock_transfer, mock_client
    ):
        """Test file upload when source path is not a file"""
        mock_client.return_value = MagicMock()
        # Simulate ValueError from transfer_file_scp
        mock_transfer.side_effect = ValueError(
            "Local path is not a file: /tmp/directory"
        )

        request = FileTransferRequest(
            host="test-host",
            local_path="/tmp/directory",
            remote_path="/home/user/test.txt",
            direction="upload",
        )

        # Mock context with async methods
        mock_ctx = MagicMock()
        mock_ctx.info = AsyncMock()
        mock_ctx.report_progress = AsyncMock()
        mock_ctx.error = AsyncMock()

        result = await transfer_file(request, mock_ctx)

        assert isinstance(result, FileTransferResult)
        assert result.success is False
        assert "Local path is not a file" in result.error_message
        assert result.local_path == "/tmp/directory"
        assert result.remote_path == "/home/user/test.txt"
        assert result.host == "test-host"

        # Verify transfer was attempted
        mock_transfer.assert_called_once()

    @patch("mcp_ssh.server.get_ssh_client_from_config")
    @patch("mcp_ssh.ssh.transfer_file_scp")
    @pytest.mark.asyncio
    async def test_transfer_file_download_success(self, mock_transfer, mock_client):
        """Test successful file download with remote source validation"""
        mock_client.return_value = MagicMock()
        mock_transfer.return_value = 2048

        request = FileTransferRequest(
            host="test-host",
            local_path="/tmp/download.txt",
            remote_path="/home/user/remote.txt",
            direction="download",
        )

        # Mock context with async methods
        mock_ctx = MagicMock()
        mock_ctx.info = AsyncMock()
        mock_ctx.report_progress = AsyncMock()
        mock_ctx.error = AsyncMock()

        result = await transfer_file(request, mock_ctx)

        assert isinstance(result, FileTransferResult)
        assert result.success is True
        assert result.bytes_transferred == 2048
        assert result.local_path == "/tmp/download.txt"
        assert result.remote_path == "/home/user/remote.txt"
        assert result.host == "test-host"
        assert result.error_message == ""

    @patch("mcp_ssh.server.get_ssh_client_from_config")
    @patch("mcp_ssh.ssh.transfer_file_scp")
    @pytest.mark.asyncio
    async def test_transfer_file_download_remote_not_exists(
        self, mock_transfer, mock_client
    ):
        """Test file download when remote file doesn't exist"""
        mock_client.return_value = MagicMock()
        # Simulate FileNotFoundError from remote file check
        mock_transfer.side_effect = FileNotFoundError(
            "Remote file does not exist: /home/user/nonexistent.txt"
        )

        request = FileTransferRequest(
            host="test-host",
            local_path="/tmp/download.txt",
            remote_path="/home/user/nonexistent.txt",
            direction="download",
        )

        # Mock context with async methods
        mock_ctx = MagicMock()
        mock_ctx.info = AsyncMock()
        mock_ctx.report_progress = AsyncMock()
        mock_ctx.error = AsyncMock()

        result = await transfer_file(request, mock_ctx)

        assert isinstance(result, FileTransferResult)
        assert result.success is False
        assert "Remote file does not exist" in result.error_message
        assert result.local_path == "/tmp/download.txt"
        assert result.remote_path == "/home/user/nonexistent.txt"
        assert result.host == "test-host"

    @patch("mcp_ssh.server.get_ssh_client_from_config")
    @pytest.mark.asyncio
    async def test_transfer_file_connection_failure(self, mock_client):
        """Test file transfer when SSH connection fails"""
        mock_client.return_value = None

        request = FileTransferRequest(
            host="nonexistent-host",
            local_path="/tmp/test.txt",
            remote_path="/home/user/test.txt",
            direction="upload",
        )

        # Mock context with async methods
        mock_ctx = MagicMock()
        mock_ctx.info = AsyncMock()
        mock_ctx.report_progress = AsyncMock()
        mock_ctx.error = AsyncMock()

        result = await transfer_file(request, mock_ctx)

        assert isinstance(result, FileTransferResult)
        assert result.success is False
        assert "Failed to connect to host 'nonexistent-host'" in result.error_message
        assert result.local_path == "/tmp/test.txt"
        assert result.remote_path == "/home/user/test.txt"
        assert result.host == "nonexistent-host"

    @patch("mcp_ssh.server.get_ssh_client_from_config")
    @patch("mcp_ssh.ssh.transfer_file_scp")
    @patch("os.path.exists")
    @patch("os.path.isfile")
    @pytest.mark.asyncio
    async def test_transfer_file_transfer_exception(
        self, mock_isfile, mock_exists, mock_transfer, mock_client
    ):
        """Test file transfer when transfer operation fails"""
        mock_client.return_value = MagicMock()
        mock_exists.return_value = True
        mock_isfile.return_value = True
        mock_transfer.side_effect = Exception("Transfer failed due to network error")

        request = FileTransferRequest(
            host="test-host",
            local_path="/tmp/test.txt",
            remote_path="/home/user/test.txt",
            direction="upload",
        )

        # Mock context with async methods
        mock_ctx = MagicMock()
        mock_ctx.info = AsyncMock()
        mock_ctx.report_progress = AsyncMock()
        mock_ctx.error = AsyncMock()

        result = await transfer_file(request, mock_ctx)

        assert isinstance(result, FileTransferResult)
        assert result.success is False
        assert "Transfer failed due to network error" in result.error_message
        assert result.local_path == "/tmp/test.txt"
        assert result.remote_path == "/home/user/test.txt"
        assert result.host == "test-host"


class TestMCPResources:
    """Test MCP resource functions"""

    @patch("mcp_ssh.ssh.parse_ssh_config")
    def test_list_ssh_hosts_empty(self, mock_parse):
        """Test listing hosts when none exist"""
        mock_parse.return_value = {}

        result = list_ssh_hosts()

        assert isinstance(result, list)
        assert len(result) == 0

    @patch("mcp_ssh.ssh.parse_ssh_config")
    def test_list_ssh_hosts_with_data(self, mock_parse):
        """Test listing hosts with valid data"""
        mock_parse.return_value = {
            "test-host": {"hostname": "example.com", "user": "testuser"},
            "another-host": {"hostname": "another.com"},
            "no-hostname": {"user": "onlyuser"},
        }

        result = list_ssh_hosts()

        assert isinstance(result, list)
        assert len(result) == 3

        # Check first host
        host1 = result[0]
        assert isinstance(host1, HostInfo)
        assert host1.name == "test-host"
        assert host1.hostname == "example.com"
        assert host1.user == "testuser"
        assert host1.port == 22

    @patch("mcp_ssh.ssh.parse_ssh_config")
    def test_list_ssh_hosts_with_complex_config(self, mock_parse):
        """Test listing hosts with various configuration options"""
        mock_parse.return_value = {
            "production": {
                "hostname": "prod.example.com",
                "user": "deploy",
                "port": "2222",
                "identityfile": "~/.ssh/prod_key",
            },
            "staging": {
                "hostname": "staging.example.com",
                "user": "ubuntu",
                "port": "2222",
            },
            "development": {"hostname": "dev.example.com"},
        }

        result = list_ssh_hosts()

        assert isinstance(result, list)
        assert len(result) == 3

        # Check production host
        prod_host = next(h for h in result if h.name == "production")
        assert prod_host.hostname == "prod.example.com"
        assert prod_host.user == "deploy"
        assert prod_host.port == 2222

        # Check staging host
        staging_host = next(h for h in result if h.name == "staging")
        assert staging_host.hostname == "staging.example.com"
        assert staging_host.user == "ubuntu"
        assert staging_host.port == 2222

        # Check development host
        dev_host = next(h for h in result if h.name == "development")
        assert dev_host.hostname == "dev.example.com"
        assert dev_host.user is None
        assert dev_host.port == 22


class TestSSHCommandModel:
    """Test the SSH command Pydantic model"""

    def test_ssh_command_valid(self):
        """Test valid SSH command creation"""
        cmd = SSHCommand(command="ls -la", host="test-host")

        assert cmd.command == "ls -la"
        assert cmd.host == "test-host"

    def test_ssh_command_validation(self):
        """Test SSH command validation"""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            SSHCommand(command="", host="test-host")  # Empty command

        with pytest.raises(ValidationError):
            SSHCommand(command="ls", host="")  # Empty host

    def test_ssh_command_field_descriptions(self):
        """Test that model fields have proper descriptions"""
        schema = SSHCommand.model_json_schema()

        assert "properties" in schema
        assert "command" in schema["properties"]
        assert "host" in schema["properties"]

        # Check field descriptions
        assert schema["properties"]["command"]["description"] == "Command to execute"
        assert (
            schema["properties"]["host"]["description"] == "Host to execute command on"
        )

    def test_ssh_command_required_fields(self):
        """Test that required fields are enforced"""
        schema = SSHCommand.model_json_schema()

        assert "required" in schema
        assert "command" in schema["required"]
        assert "host" in schema["required"]

    def test_ssh_command_serialization(self):
        """Test SSH command serialization"""
        cmd = SSHCommand(command="echo 'test'", host="example-host")

        # Test dict conversion
        cmd_dict = cmd.model_dump()
        assert cmd_dict == {"command": "echo 'test'", "host": "example-host"}

        # Test JSON serialization
        cmd_json = cmd.model_dump_json()
        assert '"command":"echo \'test\'"' in cmd_json
        assert '"host":"example-host"' in cmd_json


class TestMCPIntegration:
    """Test MCP server integration"""

    def test_mcp_server_creation(self):
        """Test that MCP server is created correctly"""
        assert mcp is not None
        assert mcp.name == "MCP SSH Server"

    def test_tools_registration(self):
        """Test that tools are registered with MCP server"""
        # This would require accessing internal MCP server state
        # For now, we test indirectly by calling the functions
        cmd = SSHCommand(command="echo test", host="localhost")

        # Should not raise an exception for model validation
        assert cmd.command == "echo test"
        assert cmd.host == "localhost"

    def test_resource_function(self):
        """Test resource function directly"""
        with patch("mcp_ssh.ssh.parse_ssh_config", return_value={"host1": {}}):
            result = list_ssh_hosts()
            assert isinstance(result, list)
            assert len(result) == 1
            assert result[0].name == "host1"
            assert result[0].hostname == "host1"

    def test_mcp_server_tools_exist(self):
        """Test that the server has the expected tools"""
        # This is a structural test to ensure tools are properly defined
        # In a real implementation, you might introspect the server

        # Test that the execute_command function exists and is callable
        assert callable(execute_command)

        # Test that the list_ssh_hosts function exists and is callable
        assert callable(list_ssh_hosts)

        # Test that SSHCommand model is properly defined
        assert hasattr(SSHCommand, "model_validate")
        assert hasattr(SSHCommand, "model_dump")


class TestErrorHandling:
    """Test error handling scenarios"""

    @patch("mcp_ssh.server.get_ssh_client_from_config")
    @pytest.mark.asyncio
    async def test_execute_command_with_exception(self, mock_get_client):
        """Test command execution when an exception occurs"""
        mock_get_client.side_effect = Exception("Unexpected error")

        request = CommandRequest(command="ls", host="error-host")

        # Mock context with async methods
        mock_ctx = MagicMock()
        mock_ctx.info = AsyncMock()
        mock_ctx.report_progress = AsyncMock()
        mock_ctx.debug = AsyncMock()
        mock_ctx.error = AsyncMock()

        # The function should handle the exception and return a CommandResult
        result = await execute_command(request, mock_ctx)
        assert isinstance(result, CommandResult)
        assert result.success is False
        assert "Unexpected error" in result.error_message

    @patch("mcp_ssh.ssh.parse_ssh_config")
    def test_list_hosts_with_exception(self, mock_parse):
        """Test host listing when an exception occurs"""
        mock_parse.side_effect = Exception("Config error")

        # The function should handle the exception and return an empty list
        result = list_ssh_hosts()
        assert isinstance(result, list)
        assert len(result) == 0
