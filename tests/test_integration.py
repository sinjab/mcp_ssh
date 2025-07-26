"""
Core integration tests for MCP SSH

This module contains essential integration tests that verify
the interaction between MCP server components.
"""

from unittest.mock import MagicMock, patch

import pytest

from mcp_ssh.server import SSHCommand, execute_command


class TestCoreIntegration:
    """Core integration tests for essential functionality"""

    @patch("mcp_ssh.server.get_ssh_client_from_config")
    @patch("mcp_ssh.server.execute_ssh_command")
    def test_end_to_end_command_execution(self, mock_exec, mock_get_client):
        """Test complete end-to-end command execution flow"""
        # Setup the mocks properly
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_exec.return_value = ("integration test successful", "")

        # Execute command through the MCP interface
        cmd = SSHCommand(command="echo 'integration test'", host="integration-host")
        result = execute_command(cmd)

        # Verify the complete chain was called
        mock_get_client.assert_called_once_with("integration-host")
        mock_exec.assert_called_once_with(mock_client, "echo 'integration test'")

        # Verify result
        assert "STDOUT:" in result
        assert "integration test successful" in result

    @patch("mcp_ssh.server.get_ssh_client_from_config")
    @patch("mcp_ssh.server.execute_ssh_command")
    def test_error_recovery_scenario(self, mock_exec, mock_get_client):
        """Test error recovery in realistic scenarios"""
        # First command fails due to connection issue
        mock_get_client.side_effect = [None, MagicMock()]
        mock_exec.return_value = ("recovered", "")

        # First attempt should fail gracefully
        cmd1 = SSHCommand(command="ls", host="failing-host")
        result1 = execute_command(cmd1)
        assert "Failed to connect" in result1

        # Second attempt should succeed
        cmd2 = SSHCommand(command="ls", host="working-host")
        result2 = execute_command(cmd2)
        assert "STDOUT:" in result2
        assert "recovered" in result2


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
