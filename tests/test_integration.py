"""
Core integration tests for MCP SSH

This module contains essential integration tests that verify
the interaction between MCP server components.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_ssh.server import CommandRequest, SSHCommand, execute_command


class TestCoreIntegration:
    """Core integration tests for essential functionality"""

    @patch("mcp_ssh.server.get_ssh_client_from_config")
    @patch("mcp_ssh.server.execute_command_background")
    @patch("mcp_ssh.server.get_process_output")
    @pytest.mark.asyncio
    async def test_end_to_end_command_execution(
        self, mock_get_output, mock_execute_bg, mock_get_client
    ):
        """Test complete end-to-end command execution flow"""
        # Setup the mocks properly
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_execute_bg.return_value = 12345
        mock_get_output.return_value = (
            "completed",
            "integration test successful",
            "",
            0,
        )

        # Mock context with async methods
        mock_ctx = MagicMock()
        mock_ctx.info = AsyncMock()
        mock_ctx.report_progress = AsyncMock()
        mock_ctx.debug = AsyncMock()
        mock_ctx.error = AsyncMock()

        # Execute command through the MCP interface
        request = CommandRequest(
            command="echo 'integration test'", host="integration-host"
        )
        result = await execute_command(request, mock_ctx)

        # Verify the complete chain was called
        mock_get_client.assert_called_once_with("integration-host")

        # Verify result
        assert result.success is True
        assert result.stdout == "integration test successful"
        assert result.stderr == ""
        assert result.exit_code == 0

    @patch("mcp_ssh.server.get_ssh_client_from_config")
    @patch("mcp_ssh.server.execute_command_background")
    @patch("mcp_ssh.server.get_process_output")
    @pytest.mark.asyncio
    async def test_error_recovery_scenario(
        self, mock_get_output, mock_execute_bg, mock_get_client
    ):
        """Test error recovery in realistic scenarios"""
        # First command fails due to connection issue
        mock_get_client.side_effect = [None, MagicMock()]
        mock_execute_bg.return_value = 12345
        mock_get_output.return_value = ("completed", "recovered", "", 0)

        # Mock context with async methods
        mock_ctx = MagicMock()
        mock_ctx.info = AsyncMock()
        mock_ctx.report_progress = AsyncMock()
        mock_ctx.debug = AsyncMock()
        mock_ctx.error = AsyncMock()

        # First attempt should fail gracefully
        request1 = CommandRequest(command="ls", host="failing-host")
        result1 = await execute_command(request1, mock_ctx)
        assert result1.success is False
        assert "Failed to establish SSH connection" in result1.error_message

        # Second attempt should succeed
        request2 = CommandRequest(command="ls", host="working-host")
        result2 = await execute_command(request2, mock_ctx)
        assert result2.success is True
        assert result2.stdout == "recovered"


class TestCommandValidation:
    """Test command validation and edge cases"""

    def test_special_characters_in_commands(self):
        """Test commands with special characters"""
        special_commands = [
            "echo 'Hello \"World\"'",
            "find . -name '*.py' | head -5",
            "ps aux | grep -v grep | grep python",
            "echo $HOME && pwd",
        ]

        for command in special_commands:
            cmd = SSHCommand(command=command, host="test-host")
            assert cmd.command == command

    def test_unicode_in_commands(self):
        """Test commands with Unicode characters"""
        unicode_commands = [
            "echo 'Hello 世界'",
            "ls /home/josé/",
            "echo 'Testing émojis: 🚀🔧'",
        ]

        for command in unicode_commands:
            cmd = SSHCommand(command=command, host="test-host")
            assert cmd.command == command

    def test_very_long_commands(self):
        """Test handling of very long commands"""
        long_command = "echo " + "a" * 1000
        cmd = SSHCommand(command=long_command, host="test-host")
        assert len(cmd.command) == len(long_command)
        assert cmd.command == long_command


class TestSecurityConsiderations:
    """Test security-related aspects"""

    def test_command_validation(self):
        """Test that the system handles various commands safely"""
        # These commands should be validated and passed through as-is
        # The actual safety is handled by SSH permissions and sudo configuration
        commands = [
            "ls -la",
            "sudo apt update",
            "cat /etc/passwd",
            "rm -rf /tmp/test",
        ]

        for command in commands:
            # Should not raise validation errors
            cmd = SSHCommand(command=command, host="test-host")
            assert cmd.command == command

    def test_host_validation(self):
        """Test that host names are properly validated"""
        valid_hosts = [
            "localhost",
            "server.example.com",
            "test-host-1",
            "prod_server_01",
        ]

        for host in valid_hosts:
            cmd = SSHCommand(command="echo test", host=host)
            assert cmd.host == host
