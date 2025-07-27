"""
Tests for SSH client functionality

This module tests the SSH client operations including connection management,
command execution, and file transfers.
"""

import os
from unittest.mock import MagicMock, patch

import paramiko
import pytest

from mcp_ssh.ssh import (
    execute_ssh_command,
    get_ssh_client_from_config,
    parse_ssh_config,
    transfer_file_scp,
)
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
        stdout, stderr, exit_code = execute_ssh_command(mock_ssh_client, "ls -la")

        assert stdout == "command output"
        assert stderr == ""
        assert exit_code == 0
        mock_ssh_client.exec_command.assert_called_once_with(
            "ls -la", get_pty=False, timeout=60
        )

    def test_execute_ssh_command_with_stderr(self):
        """Test SSH command execution with stderr output"""
        mock_client = MagicMock()
        mock_stdin = MagicMock()
        mock_stdout = MagicMock()
        mock_stderr = MagicMock()
        mock_channel = MagicMock()

        mock_stdout.read.return_value = b""
        mock_stderr.read.return_value = b"error message"
        mock_channel.recv_exit_status.return_value = 0
        mock_stdout.channel = mock_channel

        mock_client.exec_command.return_value = (mock_stdin, mock_stdout, mock_stderr)

        stdout, stderr, exit_code = execute_ssh_command(mock_client, "ls /nonexistent")

        assert stdout == ""
        assert stderr == "error message"
        assert exit_code == 0

    def test_execute_ssh_command_failure(self):
        """Test SSH command execution failure"""
        mock_client = MagicMock()
        mock_client.exec_command.side_effect = Exception("Execution failed")

        stdout, stderr, exit_code = execute_ssh_command(mock_client, "ls")

        assert stdout is None
        assert stderr == "Execution failed"
        assert exit_code is None

    def test_execute_ssh_command_special_characters(self):
        """Test SSH command execution with special characters"""
        mock_client = MagicMock()
        mock_stdin = MagicMock()
        mock_stdout = MagicMock()
        mock_stderr = MagicMock()
        mock_channel = MagicMock()

        mock_stdout.read.return_value = b"Special chars: !@#$%^&*(){}[]|\\;:'\",<>.?/"
        mock_stderr.read.return_value = b""
        mock_channel.recv_exit_status.return_value = 0
        mock_stdout.channel = mock_channel

        mock_client.exec_command.return_value = (mock_stdin, mock_stdout, mock_stderr)

        # Test the problematic command from the user's example
        command = "echo 'Special chars: !@#$%^&*(){}[]|\\;:'\",<>.?/'"
        stdout, stderr, exit_code = execute_ssh_command(mock_client, command)

        assert stdout == "Special chars: !@#$%^&*(){}[]|\\;:'\",<>.?/"
        assert stderr == ""
        assert exit_code == 0

        # Verify that the command was executed with proper shell handling
        mock_client.exec_command.assert_called_once()
        call_args = mock_client.exec_command.call_args
        assert call_args[1]["get_pty"] is False
        assert call_args[1]["timeout"] == 60


class TestCommandHandling:
    """Test command handling and shell preparation"""

    def test_is_simple_command(self):
        """Test detection of simple commands"""
        from mcp_ssh.ssh import _is_simple_command

        # Simple commands
        assert _is_simple_command("ls -la") is True
        assert _is_simple_command("echo hello") is True
        assert _is_simple_command("cat file.txt") is True

        # Commands with shell features
        assert _is_simple_command("ls | grep test") is False
        assert _is_simple_command("echo $HOME") is False
        assert _is_simple_command("ls > output.txt") is False
        assert _is_simple_command("cmd1 && cmd2") is False
        assert _is_simple_command("echo 'test'") is True  # Simple quotes are OK

    def test_prepare_shell_command(self):
        """Test shell command preparation"""
        from mcp_ssh.ssh import _has_complex_quoting, _prepare_shell_command

        # Test with special characters
        command = "echo 'Special chars: !@#$%^&*(){}[]|\\;:'\",<>.?/'"
        safe_command = _prepare_shell_command(command)

        # Should be wrapped in bash -c with proper quoting
        assert safe_command.startswith("bash -c ")
        assert "echo" in safe_command

        # Test with complex quoting (printf command from user's example)
        complex_command = "printf 'Special chars: !@#$%^&*(){}[]|\\\\;:\\'\\\"\\,<>.?/'"
        assert _has_complex_quoting(complex_command) is True
        safe_complex = _prepare_shell_command(complex_command)

        # Should use heredoc approach for complex quoting
        assert safe_complex.startswith("bash << '")
        assert "printf" in safe_complex

        # Test with simple command
        simple_command = "ls -la"
        safe_simple = _prepare_shell_command(simple_command)
        assert safe_simple.startswith("bash -c ")

    def test_has_complex_quoting(self):
        """Test detection of complex quoting patterns"""
        from mcp_ssh.ssh import _has_complex_quoting

        # Commands with complex quoting (escaped quotes)
        assert _has_complex_quoting("echo 'Escaped \\' quote'") is True
        assert _has_complex_quoting('echo "Escaped \\" quote"') is True
        assert (
            _has_complex_quoting(
                "printf 'Special chars: !@#$%^&*(){}[]|\\\\;:\\'\\\"\\,<>.?/'"
            )
            is True
        )

        # Commands without complex quoting
        assert _has_complex_quoting("echo 'Simple quotes'") is False
        assert _has_complex_quoting('echo "Simple quotes"') is False
        assert (
            _has_complex_quoting("echo 'Mixed \"quotes'") is False
        )  # Not detected as complex
        assert (
            _has_complex_quoting('echo "Mixed \'quotes"') is False
        )  # Not detected as complex
        assert _has_complex_quoting("ls -la") is False
        assert _has_complex_quoting("echo $HOME") is False


class TestFileTransfer:
    """Test file transfer functionality"""

    @patch("os.path.exists")
    @patch("os.path.isfile")
    def test_transfer_file_upload_success(self, mock_isfile, mock_exists):
        """Test successful file upload with source validation"""
        mock_client = MagicMock()
        mock_exists.return_value = True
        mock_isfile.return_value = True

        # Mock SCP operations
        mock_scp = MagicMock()
        mock_client.open_sftp.return_value = mock_scp

        # Mock file size calculation
        with patch("os.path.getsize", return_value=1024):
            bytes_transferred = transfer_file_scp(
                mock_client, "/tmp/test.txt", "/home/user/test.txt", "upload"
            )

        assert bytes_transferred == 1024
        mock_exists.assert_called_once_with("/tmp/test.txt")
        mock_isfile.assert_called_once_with("/tmp/test.txt")
        mock_scp.put.assert_called_once_with("/tmp/test.txt", "/home/user/test.txt")
        mock_scp.close.assert_called_once()

    @patch("os.path.exists")
    def test_transfer_file_upload_source_not_exists(self, mock_exists):
        """Test file upload when source file doesn't exist"""
        mock_client = MagicMock()
        mock_exists.return_value = False

        with pytest.raises(
            FileNotFoundError, match="Local file does not exist: /tmp/nonexistent.txt"
        ):
            transfer_file_scp(
                mock_client, "/tmp/nonexistent.txt", "/home/user/test.txt", "upload"
            )

        mock_exists.assert_called_once_with("/tmp/nonexistent.txt")

    @patch("os.path.exists")
    @patch("os.path.isfile")
    def test_transfer_file_upload_source_not_file(self, mock_isfile, mock_exists):
        """Test file upload when source path is not a file"""
        mock_client = MagicMock()
        mock_exists.return_value = True
        mock_isfile.return_value = False

        with pytest.raises(
            ValueError, match="Local path is not a file: /tmp/directory"
        ):
            transfer_file_scp(
                mock_client, "/tmp/directory", "/home/user/test.txt", "upload"
            )

        mock_exists.assert_called_once_with("/tmp/directory")
        mock_isfile.assert_called_once_with("/tmp/directory")

    def test_transfer_file_download_success(self):
        """Test successful file download with remote source validation"""
        mock_client = MagicMock()

        # Mock SFTP for remote file check and SCP operations
        mock_sftp = MagicMock()
        mock_client.open_sftp.return_value = mock_sftp

        # Mock file size calculation
        with patch("os.path.getsize", return_value=2048):
            bytes_transferred = transfer_file_scp(
                mock_client, "/tmp/download.txt", "/home/user/remote.txt", "download"
            )

        assert bytes_transferred == 2048
        # Verify remote file was checked
        mock_sftp.stat.assert_called_once_with("/home/user/remote.txt")
        # Should be called twice: once for stat check, once for transfer
        assert mock_sftp.close.call_count == 2
        mock_sftp.get.assert_called_once_with(
            "/home/user/remote.txt", "/tmp/download.txt"
        )
        # Should be called twice: once for stat check, once for transfer
        assert mock_client.open_sftp.call_count == 2

    def test_transfer_file_download_remote_not_exists(self):
        """Test file download when remote file doesn't exist"""
        mock_client = MagicMock()

        # Mock SFTP for remote file check - simulate FileNotFoundError
        mock_sftp = MagicMock()
        mock_sftp.stat.side_effect = FileNotFoundError("File not found")
        mock_client.open_sftp.return_value = mock_sftp

        with pytest.raises(
            FileNotFoundError,
            match="Remote file does not exist: /home/user/nonexistent.txt",
        ):
            transfer_file_scp(
                mock_client,
                "/tmp/download.txt",
                "/home/user/nonexistent.txt",
                "download",
            )

        mock_sftp.stat.assert_called_once_with("/home/user/nonexistent.txt")
        mock_sftp.close.assert_called_once()
        # Should only be called once for the stat check
        mock_client.open_sftp.assert_called_once()

    def test_transfer_file_invalid_direction(self):
        """Test file transfer with invalid direction"""
        mock_client = MagicMock()

        with pytest.raises(
            ValueError, match="Invalid direction: invalid. Use 'upload' or 'download'"
        ):
            transfer_file_scp(
                mock_client, "/tmp/test.txt", "/home/user/test.txt", "invalid"
            )

    @patch("os.path.exists")
    @patch("os.path.isfile")
    def test_transfer_file_upload_exception_handling(self, mock_isfile, mock_exists):
        """Test file upload exception handling"""
        mock_client = MagicMock()
        mock_exists.return_value = True
        mock_isfile.return_value = True

        # Mock SCP operations to raise exception
        mock_scp = MagicMock()
        mock_scp.put.side_effect = Exception("Network error")
        mock_client.open_sftp.return_value = mock_scp

        with pytest.raises(Exception, match="Network error"):
            transfer_file_scp(
                mock_client, "/tmp/test.txt", "/home/user/test.txt", "upload"
            )

        mock_scp.put.assert_called_once_with("/tmp/test.txt", "/home/user/test.txt")
        # close() should be called even when exception occurs
        mock_scp.close.assert_called_once()

    def test_transfer_file_download_exception_handling(self):
        """Test file download exception handling"""
        mock_client = MagicMock()

        # Mock SFTP for remote file check
        mock_sftp = MagicMock()
        # Mock SCP operations to raise exception
        mock_scp = MagicMock()
        mock_scp.get.side_effect = Exception("Network error")

        # Return different mocks for each call
        mock_client.open_sftp.side_effect = [mock_sftp, mock_scp]

        with pytest.raises(Exception, match="Network error"):
            transfer_file_scp(
                mock_client, "/tmp/download.txt", "/home/user/remote.txt", "download"
            )

        # Should be called once for stat check
        mock_sftp.stat.assert_called_once_with("/home/user/remote.txt")
        mock_sftp.close.assert_called_once()
        # Should be called once for transfer attempt
        mock_scp.get.assert_called_once_with(
            "/home/user/remote.txt", "/tmp/download.txt"
        )
        mock_scp.close.assert_called_once()


class TestBackgroundExecution:
    """Test background execution functionality"""

    def test_execute_command_background_success(self):
        """Test successful background command execution"""
        from mcp_ssh.ssh import execute_command_background

        mock_client = MagicMock()
        mock_stdin = MagicMock()
        mock_stdout = MagicMock()
        mock_stderr = MagicMock()

        mock_stdout.read.return_value = b"12345\n"
        mock_client.exec_command.return_value = (mock_stdin, mock_stdout, mock_stderr)

        pid = execute_command_background(
            mock_client, "ls -la", "/tmp/test.out", "/tmp/test.err"
        )

        assert pid == 12345
        mock_client.exec_command.assert_called_once()
        call_args = mock_client.exec_command.call_args[0][0]
        # Check that timeout was passed
        assert mock_client.exec_command.call_args[1]["timeout"] == 60
        assert "nohup bash -c" in call_args
        assert "ls -la" in call_args
        assert "/tmp/test.out" in call_args
        assert "/tmp/test.err" in call_args
        assert "echo $!" in call_args

    def test_execute_command_background_invalid_pid(self):
        """Test background command execution with invalid PID response"""
        from mcp_ssh.ssh import execute_command_background

        mock_client = MagicMock()
        mock_stdin = MagicMock()
        mock_stdout = MagicMock()
        mock_stderr = MagicMock()

        mock_stdout.read.return_value = b"invalid\n"
        mock_client.exec_command.return_value = (mock_stdin, mock_stdout, mock_stderr)

        with pytest.raises(RuntimeError, match="Failed to get PID"):
            execute_command_background(
                mock_client, "ls -la", "/tmp/test.out", "/tmp/test.err"
            )

    def test_get_process_output_running(self):
        """Test getting output from running process"""
        from mcp_ssh.background import BackgroundProcess
        from mcp_ssh.ssh import get_process_output

        mock_client = MagicMock()
        mock_stdin = MagicMock()
        mock_stdout = MagicMock()
        mock_stderr = MagicMock()

        # Mock status check - process is running
        mock_stdout.read.side_effect = [b"RUNNING\n", b"output data", b"error data"]
        mock_client.exec_command.return_value = (mock_stdin, mock_stdout, mock_stderr)

        process = BackgroundProcess(
            process_id="test123",
            host="test-host",
            command="ls -la",
            pid=12345,
            start_time=None,
            status="running",
            output_file="/tmp/test.out",
            error_file="/tmp/test.err",
        )

        status, output, errors, exit_code = get_process_output(
            mock_client, process, 1000
        )

        assert status == "running"
        assert output == "output data"
        assert errors == "error data"
        assert exit_code is None

        # Verify the commands executed
        calls = mock_client.exec_command.call_args_list
        assert len(calls) == 3
        assert "kill -0 12345" in calls[0][0][0]
        assert "head -c 1000 /tmp/test.out" in calls[1][0][0]
        assert "head -c 500 /tmp/test.err" in calls[2][0][0]

    def test_get_process_output_completed(self):
        """Test getting output from completed process"""
        from mcp_ssh.background import BackgroundProcess
        from mcp_ssh.ssh import get_process_output

        mock_client = MagicMock()
        mock_stdin = MagicMock()
        mock_stdout = MagicMock()
        mock_stderr = MagicMock()

        # Mock status check - process is stopped, exit code 0
        mock_stdout.read.side_effect = [
            b"STOPPED\n",
            b"0\n",
            b"output data",
            b"error data",
        ]
        mock_client.exec_command.return_value = (mock_stdin, mock_stdout, mock_stderr)

        process = BackgroundProcess(
            process_id="test123",
            host="test-host",
            command="ls -la",
            pid=12345,
            start_time=None,
            status="running",
            output_file="/tmp/test.out",
            error_file="/tmp/test.err",
        )

        status, output, errors, exit_code = get_process_output(
            mock_client, process, 1000
        )

        assert status == "completed"
        assert output == "output data"
        assert errors == "error data"
        assert exit_code == 0

    def test_get_output_chunk_success(self):
        """Test getting specific chunk of output"""
        from mcp_ssh.background import BackgroundProcess
        from mcp_ssh.ssh import get_output_chunk

        mock_client = MagicMock()
        mock_stdin = MagicMock()
        mock_stdout = MagicMock()
        mock_stderr = MagicMock()

        # Mock chunk retrieval - has more data
        mock_stdout.read.side_effect = [b"chunk data", b"x"]
        mock_client.exec_command.return_value = (mock_stdin, mock_stdout, mock_stderr)

        process = BackgroundProcess(
            process_id="test123",
            host="test-host",
            command="ls -la",
            pid=12345,
            start_time=None,
            status="running",
            output_file="/tmp/test.out",
            error_file="/tmp/test.err",
        )

        chunk, has_more = get_output_chunk(mock_client, process, 100, 50)

        assert chunk == "chunk data"
        assert has_more is True

        # Verify the commands executed
        calls = mock_client.exec_command.call_args_list
        assert len(calls) == 2
        assert "tail -c +101 /tmp/test.out" in calls[0][0][0]
        assert "head -c 50" in calls[0][0][0]
        assert "tail -c +151 /tmp/test.out" in calls[1][0][0]

    def test_get_output_chunk_no_more_data(self):
        """Test getting chunk when no more data available"""
        from mcp_ssh.background import BackgroundProcess
        from mcp_ssh.ssh import get_output_chunk

        mock_client = MagicMock()
        mock_stdin = MagicMock()
        mock_stdout = MagicMock()
        mock_stderr = MagicMock()

        # Mock chunk retrieval - no more data
        mock_stdout.read.side_effect = [b"chunk data", b""]
        mock_client.exec_command.return_value = (mock_stdin, mock_stdout, mock_stderr)

        process = BackgroundProcess(
            process_id="test123",
            host="test-host",
            command="ls -la",
            pid=12345,
            start_time=None,
            status="running",
            output_file="/tmp/test.out",
            error_file="/tmp/test.err",
        )

        chunk, has_more = get_output_chunk(mock_client, process, 100, 50)

        assert chunk == "chunk data"
        assert has_more is False

    def test_kill_background_process_success_graceful(self):
        """Test successful graceful process termination"""
        from mcp_ssh.background import BackgroundProcess
        from mcp_ssh.ssh import kill_background_process

        mock_client = MagicMock()
        mock_stdin = MagicMock()
        mock_stdout = MagicMock()
        mock_stderr = MagicMock()

        # Mock graceful termination
        mock_stdout.read.side_effect = [b"", b"STOPPED\n"]
        mock_client.exec_command.return_value = (mock_stdin, mock_stdout, mock_stderr)

        process = BackgroundProcess(
            process_id="test123",
            host="test-host",
            command="sleep 100",
            pid=12345,
            start_time=None,
            status="running",
            output_file="/tmp/test.out",
            error_file="/tmp/test.err",
        )

        success, message = kill_background_process(mock_client, process)

        assert success is True
        assert "terminated gracefully" in message

        # Verify the commands executed
        calls = mock_client.exec_command.call_args_list
        assert len(calls) == 2
        assert "kill 12345" in calls[0][0][0]
        assert "kill -0 12345" in calls[1][0][0]

    def test_kill_background_process_success_force(self):
        """Test successful force process termination"""
        from mcp_ssh.background import BackgroundProcess
        from mcp_ssh.ssh import kill_background_process

        mock_client = MagicMock()
        mock_stdin = MagicMock()
        mock_stdout = MagicMock()
        mock_stderr = MagicMock()

        # Mock force termination (graceful fails, force succeeds)
        mock_stdout.read.side_effect = [b"", b"RUNNING\n", b"", b"STOPPED\n"]
        mock_client.exec_command.return_value = (mock_stdin, mock_stdout, mock_stderr)

        process = BackgroundProcess(
            process_id="test123",
            host="test-host",
            command="sleep 100",
            pid=12345,
            start_time=None,
            status="running",
            output_file="/tmp/test.out",
            error_file="/tmp/test.err",
        )

        success, message = kill_background_process(mock_client, process)

        assert success is True
        assert "force killed" in message

        # Verify the commands executed
        calls = mock_client.exec_command.call_args_list
        assert len(calls) == 4
        assert "kill 12345" in calls[0][0][0]
        assert "kill -0 12345" in calls[1][0][0]
        assert "kill -9 12345" in calls[2][0][0]
        assert "kill -0 12345" in calls[3][0][0]

    def test_kill_background_process_failure(self):
        """Test failed process termination"""
        from mcp_ssh.background import BackgroundProcess
        from mcp_ssh.ssh import kill_background_process

        mock_client = MagicMock()
        mock_stdin = MagicMock()
        mock_stdout = MagicMock()
        mock_stderr = MagicMock()

        # Mock failed termination
        mock_stdout.read.side_effect = [
            b"",
            b"RUNNING\n",
            b"Permission denied\n",
            b"RUNNING\n",
        ]
        mock_client.exec_command.return_value = (mock_stdin, mock_stdout, mock_stderr)

        process = BackgroundProcess(
            process_id="test123",
            host="test-host",
            command="sleep 100",
            pid=12345,
            start_time=None,
            status="running",
            output_file="/tmp/test.out",
            error_file="/tmp/test.err",
        )

        success, message = kill_background_process(mock_client, process)

        assert success is False
        assert "Permission denied" in message

    def test_kill_background_process_no_pid(self):
        """Test killing process with no PID"""
        from mcp_ssh.background import BackgroundProcess
        from mcp_ssh.ssh import kill_background_process

        mock_client = MagicMock()

        process = BackgroundProcess(
            process_id="test123",
            host="test-host",
            command="ls -la",
            pid=None,
            start_time=None,
            status="running",
            output_file="/tmp/test.out",
            error_file="/tmp/test.err",
        )

        success, message = kill_background_process(mock_client, process)

        assert success is False
        assert "No PID available" in message

    def test_cleanup_process_files_success(self):
        """Test successful cleanup of process files"""
        from mcp_ssh.background import BackgroundProcess
        from mcp_ssh.ssh import cleanup_process_files

        mock_client = MagicMock()
        mock_stdin = MagicMock()
        mock_stdout = MagicMock()
        mock_stderr = MagicMock()

        mock_client.exec_command.return_value = (mock_stdin, mock_stdout, mock_stderr)

        process = BackgroundProcess(
            process_id="test123",
            host="test-host",
            command="ls -la",
            pid=12345,
            start_time=None,
            status="running",
            output_file="/tmp/test.out",
            error_file="/tmp/test.err",
        )

        result = cleanup_process_files(mock_client, process)

        assert result is True
        mock_client.exec_command.assert_called_once()
        call_args = mock_client.exec_command.call_args[0][0]
        # Check that timeout was passed
        assert mock_client.exec_command.call_args[1]["timeout"] == 60
        assert "rm -f /tmp/test.out /tmp/test.err /tmp/test.out.exit" in call_args

    def test_cleanup_process_files_failure(self):
        """Test failed cleanup of process files"""
        from mcp_ssh.background import BackgroundProcess
        from mcp_ssh.ssh import cleanup_process_files

        mock_client = MagicMock()
        mock_client.exec_command.side_effect = Exception("Connection lost")

        process = BackgroundProcess(
            process_id="test123",
            host="test-host",
            command="ls -la",
            pid=12345,
            start_time=None,
            status="running",
            output_file="/tmp/test.out",
            error_file="/tmp/test.err",
        )

        result = cleanup_process_files(mock_client, process)

        assert result is False
