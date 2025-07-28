"""
Test cases for the command execution fix.
Tests the fix for shell redirection and quote handling in SSH commands.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from unittest.mock import Mock, patch, MagicMock
from mcp_ssh.ssh import execute_command_background


class TestCommandExecutionFix:
    """Test the command execution bug fix"""

    def setup_method(self):
        """Set up test fixtures"""
        self.mock_client = Mock()
        self.mock_stdin = Mock()
        self.mock_stdout = Mock()
        self.mock_stderr = Mock()
        self.mock_channel = Mock()
        
        # Set up the mock chain
        self.mock_stdout.channel = self.mock_channel
        self.mock_channel.exit_status_ready.return_value = True
        self.mock_stdout.read.return_value = b"12345\n"  # Mock PID
        self.mock_stderr.read.return_value = b""
        
        self.mock_client.exec_command.return_value = (
            self.mock_stdin, self.mock_stdout, self.mock_stderr
        )

    def test_single_quote_escaping(self):
        """Test that single quotes are properly escaped"""
        command = "echo 'Hello World' > test.txt"
        
        pid = execute_command_background(
            self.mock_client, command, "/tmp/out", "/tmp/err"
        )
        
        # Verify the command was called
        self.mock_client.exec_command.assert_called_once()
        call_args = self.mock_client.exec_command.call_args[0][0]
        
        # The escaped command should not break bash -c syntax
        assert "echo '\"'\"'Hello World'\"'\"' > test.txt" in call_args
        assert pid == 12345

    def test_double_quotes_preserved(self):
        """Test that double quotes are preserved correctly"""
        command = 'echo "Hello World" > test.txt'
        
        execute_command_background(
            self.mock_client, command, "/tmp/out", "/tmp/err"
        )
        
        call_args = self.mock_client.exec_command.call_args[0][0]
        
        # Double quotes should be preserved
        assert 'echo "Hello World" > test.txt' in call_args

    def test_mixed_quotes(self):
        """Test commands with mixed single and double quotes"""
        command = """echo 'Single "double" quotes' > test.txt"""
        
        execute_command_background(
            self.mock_client, command, "/tmp/out", "/tmp/err"
        )
        
        call_args = self.mock_client.exec_command.call_args[0][0]
        
        # Should properly escape single quotes while preserving double quotes
        assert """echo '"'"'Single "double" quotes'"'"' > test.txt""" in call_args

    def test_shell_redirection_operators(self):
        """Test various shell redirection operators"""
        test_cases = [
            "echo 'content' > file.txt",
            "echo 'content' >> file.txt", 
            "cat 'input.txt' | grep 'pattern'",
            "echo 'data' | tee 'output.txt'",
            "sort 'file.txt' > 'sorted.txt'",
        ]
        
        for command in test_cases:
            with self.subTest(command=command):
                execute_command_background(
                    self.mock_client, command, "/tmp/out", "/tmp/err"
                )
                
                call_args = self.mock_client.exec_command.call_args[0][0]
                
                # Verify redirection operators are preserved
                for operator in ['>', '>>', '|']:
                    if operator in command:
                        assert operator in call_args

    def test_complex_shell_commands(self):
        """Test complex shell commands with multiple features"""
        command = "echo 'Line 1' > file.txt && echo 'Line 2' >> file.txt"
        
        execute_command_background(
            self.mock_client, command, "/tmp/out", "/tmp/err"
        )
        
        call_args = self.mock_client.exec_command.call_args[0][0]
        
        # Should preserve shell operators
        assert "&&" in call_args
        assert ">" in call_args
        assert ">>" in call_args

    def test_heredoc_commands(self):
        """Test heredoc-style commands"""
        command = """cat > file.txt << 'EOF'
Content line 1
Content line 2
EOF"""
        
        execute_command_background(
            self.mock_client, command, "/tmp/out", "/tmp/err"
        )
        
        call_args = self.mock_client.exec_command.call_args[0][0]
        
        # Should preserve heredoc syntax
        assert "<<" in call_args
        assert "EOF" in call_args

    @patch('mcp_ssh.ssh.logger')
    def test_debug_logging(self, mock_logger):
        """Test that debug logging is working"""
        command = "echo 'test' > file.txt"
        
        execute_command_background(
            self.mock_client, command, "/tmp/out", "/tmp/err"
        )
        
        # Verify debug logging was called
        mock_logger.debug.assert_called()
        
        # Check that original and escaped commands are logged
        debug_calls = [call.args[0] for call in mock_logger.debug.call_args_list]
        assert any("Original command:" in call for call in debug_calls)
        assert any("Escaped command:" in call for call in debug_calls)

    def test_error_handling_with_invalid_pid(self):
        """Test error handling when PID parsing fails"""
        self.mock_stdout.read.return_value = b"not_a_number\n"
        
        try:
            execute_command_background(
                self.mock_client, "echo test", "/tmp/out", "/tmp/err"
            )
            assert False, "Expected RuntimeError"
        except RuntimeError as e:
            assert "Failed to get PID" in str(e)

    def test_background_wrapper_structure(self):
        """Test that the background wrapper has correct structure"""
        command = "echo 'test'"
        
        execute_command_background(
            self.mock_client, command, "/tmp/out", "/tmp/err"
        )
        
        call_args = self.mock_client.exec_command.call_args[0][0]
        
        # Verify background wrapper structure
        assert "nohup bash -c" in call_args
        assert "echo $!" in call_args  # PID output
        assert "/tmp/out" in call_args  # Output redirection
        assert "/tmp/err" in call_args  # Error redirection
        assert ".exit" in call_args     # Exit code file

    def test_no_quotes_command(self):
        """Test commands without quotes work correctly"""
        command = "ls -la > output.txt"
        
        execute_command_background(
            self.mock_client, command, "/tmp/out", "/tmp/err"
        )
        
        call_args = self.mock_client.exec_command.call_args[0][0]
        
        # Should work without modification
        assert "ls -la > output.txt" in call_args


def run_tests():
    """Run all tests manually"""
    test_instance = TestCommandExecutionFix()
    
    test_methods = [
        'test_single_quote_escaping',
        'test_double_quotes_preserved', 
        'test_mixed_quotes',
        'test_shell_redirection_operators',
        'test_complex_shell_commands',
        'test_heredoc_commands',
        'test_debug_logging',
        'test_error_handling_with_invalid_pid',
        'test_background_wrapper_structure',
        'test_no_quotes_command'
    ]
    
    passed = 0
    failed = 0
    
    for method_name in test_methods:
        try:
            print(f"Running {method_name}...")
            test_instance.setup_method()
            method = getattr(test_instance, method_name)
            method()
            print(f"  ✓ PASSED")
            passed += 1
        except Exception as e:
            print(f"  ✗ FAILED: {e}")
            failed += 1
    
    print(f"\nResults: {passed} passed, {failed} failed")
    return failed == 0

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
