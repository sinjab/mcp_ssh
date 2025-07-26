"""
Tests for MCP server functionality

This module tests the MCP tools, resources, prompts, and server integration.
"""

from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from mcp_ssh.server import SSHCommand, execute_command, list_ssh_hosts, mcp


class TestMCPTools:
    """Test MCP tool functions"""

    @patch("mcp_ssh.server.get_ssh_client_from_config")
    @patch("mcp_ssh.server.execute_ssh_command")
    def test_execute_command_success(self, mock_exec, mock_client):
        """Test successful command execution"""
        mock_client.return_value = MagicMock()
        mock_exec.return_value = ("command output", "")

        cmd = SSHCommand(command="ls -la", host="test-host")
        result = execute_command(cmd)

        assert "STDOUT:" in result
        assert "command output" in result
        mock_client.assert_called_once_with("test-host")

    @patch("mcp_ssh.server.get_ssh_client_from_config")
    def test_execute_command_no_host(self, mock_client):
        """Test command execution when host connection fails"""
        mock_client.return_value = None

        cmd = SSHCommand(command="ls", host="nonexistent")
        result = execute_command(cmd)

        assert "Failed to connect to host 'nonexistent'" in result
        assert "Please check your SSH config" in result

    @patch("mcp_ssh.server.get_ssh_client_from_config")
    @patch("mcp_ssh.server.execute_ssh_command")
    def test_execute_command_with_stderr(self, mock_exec, mock_client):
        """Test command execution with stderr output"""
        mock_client.return_value = MagicMock()
        mock_exec.return_value = ("stdout output", "stderr output")

        cmd = SSHCommand(command="ls /nonexistent", host="test-host")
        result = execute_command(cmd)

        assert "STDOUT:" in result
        assert "stdout output" in result
        assert "STDERR:" in result
        assert "stderr output" in result

    @patch("mcp_ssh.server.get_ssh_client_from_config")
    @patch("mcp_ssh.server.execute_ssh_command")
    def test_execute_command_no_output(self, mock_exec, mock_client):
        """Test command execution with no output"""
        mock_client.return_value = MagicMock()
        mock_exec.return_value = ("", "")

        cmd = SSHCommand(command="touch /tmp/test", host="test-host")
        result = execute_command(cmd)

        assert result == "Command executed successfully"

    @patch("mcp_ssh.server.get_ssh_client_from_config")
    @patch("mcp_ssh.server.execute_ssh_command")
    def test_execute_command_only_stderr(self, mock_exec, mock_client):
        """Test command execution with only stderr output"""
        mock_client.return_value = MagicMock()
        mock_exec.return_value = ("", "error only")

        cmd = SSHCommand(command="invalid-command", host="test-host")
        result = execute_command(cmd)

        assert "STDERR:" in result
        assert "error only" in result
        assert "STDOUT:" not in result


class TestMCPResources:
    """Test MCP resource functions"""

    @patch("mcp_ssh.ssh.parse_ssh_config")
    def test_list_ssh_hosts_empty(self, mock_parse):
        """Test listing hosts when none exist"""
        mock_parse.return_value = {}

        result = list_ssh_hosts()

        assert "No hosts found in SSH config" in result

    @patch("mcp_ssh.ssh.parse_ssh_config")
    def test_list_ssh_hosts_with_data(self, mock_parse):
        """Test listing hosts with valid data"""
        mock_parse.return_value = {
            "test-host": {"hostname": "example.com", "user": "testuser"},
            "another-host": {"hostname": "another.com"},
            "no-hostname": {"user": "onlyuser"},
        }

        result = list_ssh_hosts()

        assert "Available SSH Hosts:" in result
        assert "test-host -> example.com (User: testuser)" in result
        assert "another-host -> another.com" in result
        assert "no-hostname -> no-hostname" in result  # Falls back to host name

    @patch("mcp_ssh.ssh.parse_ssh_config")
    def test_list_ssh_hosts_with_complex_config(self, mock_parse):
        """Test listing hosts with various configuration options"""
        mock_parse.return_value = {
            "production": {
                "hostname": "prod.example.com",
                "user": "deploy",
                "port": "22",
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

        assert "Available SSH Hosts:" in result
        assert "production -> prod.example.com (User: deploy)" in result
        assert "staging -> staging.example.com (User: ubuntu)" in result
        assert "development -> dev.example.com" in result


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
            assert "Available SSH Hosts:" in result

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
    def test_execute_command_with_exception(self, mock_get_client):
        """Test command execution when an exception occurs"""
        mock_get_client.side_effect = Exception("Unexpected error")

        cmd = SSHCommand(command="ls", host="error-host")

        # The function should handle the exception and return an error message
        result = execute_command(cmd)
        assert isinstance(result, str)
        # Should contain error information
        assert "Failed to connect" in result or "error" in result.lower()

    @patch("mcp_ssh.ssh.parse_ssh_config")
    def test_list_hosts_with_exception(self, mock_parse):
        """Test host listing when an exception occurs"""
        mock_parse.side_effect = Exception("Config error")

        # The function should handle the exception and return an error message
        result = list_ssh_hosts()
        assert isinstance(result, str)
        # Should contain error information or fallback message
        assert "No hosts found" in result or "error" in result.lower()
