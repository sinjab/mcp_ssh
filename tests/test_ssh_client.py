"""
Tests for SSH client functionality

This module tests SSH client connection management, command execution,
and error handling scenarios.
"""

import os
from unittest.mock import MagicMock, patch

import paramiko
import pytest

from mcp_ssh.ssh import execute_ssh_command, get_ssh_client_from_config
from tests.conftest import TestConstants


class TestSSHClient:
    """Test SSH client functionality"""

    def test_get_ssh_client_host_not_found(self):
        """Test getting SSH client for non-existent host"""
        with patch("mcp_ssh.ssh.parse_ssh_config", return_value={}):
            result = get_ssh_client_from_config("nonexistent")
            assert result is None

    @patch("mcp_ssh.ssh.parse_ssh_config")
    @patch("paramiko.SSHClient")
    @patch("os.path.exists")
    @patch("paramiko.RSAKey.from_private_key_file")
    def test_get_ssh_client_success_no_passphrase(
        self, mock_key, mock_exists, mock_ssh, mock_config
    ):
        """Test successful SSH client creation without passphrase"""
        # Setup mocks
        mock_config.return_value = {
            "test-host": {
                "hostname": "example.com",
                "user": "testuser",
                "port": "22",
                "identityfile": "~/.ssh/id_rsa",
            }
        }
        mock_exists.return_value = True
        mock_key_instance = MagicMock()
        mock_key.return_value = mock_key_instance
        mock_client = MagicMock()
        mock_ssh.return_value = mock_client

        result = get_ssh_client_from_config("test-host")

        assert result == mock_client
        mock_client.connect.assert_called_once()
        connect_args = mock_client.connect.call_args[1]
        assert connect_args["hostname"] == "example.com"
        assert connect_args["username"] == "testuser"
        assert connect_args["port"] == 22
        assert connect_args["pkey"] == mock_key_instance

    @patch("mcp_ssh.ssh.parse_ssh_config")
    @patch("paramiko.SSHClient")
    @patch("os.path.exists")
    @patch("paramiko.RSAKey.from_private_key_file")
    @patch.dict(os.environ, {"SSH_KEY_PHRASE": "test_passphrase"})
    def test_get_ssh_client_with_passphrase(
        self, mock_key, mock_exists, mock_ssh, mock_config
    ):
        """Test SSH client creation with encrypted key"""
        # Setup mocks
        mock_config.return_value = {
            "test-host": {"hostname": "example.com", "user": "testuser"}
        }
        mock_exists.return_value = True

        # First call (no passphrase) raises exception, second call (with passphrase) succeeds
        mock_key_instance = MagicMock()
        mock_key.side_effect = [paramiko.SSHException("Bad key"), mock_key_instance]

        mock_client = MagicMock()
        mock_ssh.return_value = mock_client

        result = get_ssh_client_from_config("test-host")

        assert result == mock_client
        assert mock_key.call_count == 2
        # Second call should include the passphrase
        mock_key.assert_any_call(
            os.path.expanduser("~/.ssh/id_rsa"), password="test_passphrase"
        )

    @patch("mcp_ssh.ssh.parse_ssh_config")
    @patch("paramiko.SSHClient")
    @patch("os.path.exists")
    @patch("paramiko.RSAKey.from_private_key_file")
    @patch.dict(os.environ, {}, clear=True)  # No SSH_KEY_PHRASE
    def test_get_ssh_client_encrypted_key_no_passphrase(
        self, mock_key, mock_exists, mock_ssh, mock_config
    ):
        """Test SSH client creation with encrypted key but no passphrase in env"""
        mock_config.return_value = {
            "test-host": {"hostname": "example.com", "user": "testuser"}
        }
        mock_exists.return_value = True

        # Key requires passphrase but none provided
        mock_key.side_effect = paramiko.SSHException("Bad key")

        mock_client = MagicMock()
        mock_ssh.return_value = mock_client

        result = get_ssh_client_from_config("test-host")

        assert result is None

    @patch("mcp_ssh.ssh.parse_ssh_config")
    @patch("paramiko.SSHClient")
    @patch("os.path.exists")
    def test_get_ssh_client_key_file_not_exists(
        self, mock_exists, mock_ssh, mock_config
    ):
        """Test SSH client creation when key file doesn't exist"""
        mock_config.return_value = {
            "test-host": {
                "hostname": "example.com",
                "user": "testuser",
                "identityfile": "~/.ssh/nonexistent_key",
            }
        }
        mock_exists.return_value = False

        mock_client = MagicMock()
        mock_ssh.return_value = mock_client

        result = get_ssh_client_from_config("test-host")

        assert result is None

    @patch("mcp_ssh.ssh.parse_ssh_config")
    @patch("paramiko.SSHClient")
    def test_get_ssh_client_connection_failure(self, mock_ssh, mock_config):
        """Test SSH client creation when connection fails"""
        mock_config.return_value = {
            "test-host": {"hostname": "example.com", "user": "testuser"}
        }

        mock_client = MagicMock()
        mock_client.connect.side_effect = Exception("Connection refused")
        mock_ssh.return_value = mock_client

        result = get_ssh_client_from_config("test-host")

        assert result is None

    def test_execute_ssh_command_success(self, mock_ssh_client):
        """Test successful SSH command execution"""
        stdout, stderr = execute_ssh_command(mock_ssh_client, "ls -la")

        assert stdout == "command output"
        assert stderr == ""
        mock_ssh_client.exec_command.assert_called_once_with("ls -la")

    def test_execute_ssh_command_with_stderr(self):
        """Test SSH command execution with stderr output"""
        mock_client = MagicMock()
        mock_stdin = MagicMock()
        mock_stdout = MagicMock()
        mock_stderr = MagicMock()

        mock_stdout.read.return_value = b""
        mock_stderr.read.return_value = b"error message"

        mock_client.exec_command.return_value = (mock_stdin, mock_stdout, mock_stderr)

        stdout, stderr = execute_ssh_command(mock_client, "ls /nonexistent")

        assert stdout == ""
        assert stderr == "error message"

    def test_execute_ssh_command_failure(self):
        """Test SSH command execution failure"""
        mock_client = MagicMock()
        mock_client.exec_command.side_effect = Exception("Execution failed")

        stdout, stderr = execute_ssh_command(mock_client, "ls")

        assert stdout is None
        assert stderr == "Execution failed"
