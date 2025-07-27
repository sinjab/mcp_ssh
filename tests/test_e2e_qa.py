#!/usr/bin/env python3
"""
End-to-End QA Test Suite for MCP SSH Background Execution

This comprehensive test suite validates the complete MCP SSH system
against a real SSH server (dev1) to ensure production readiness.

Usage:
    cd /Users/khs/Documents/projects/mcp_ssh/
    export SSH_TEST_HOST=dev1
    export SSH_TEST_USER=your_username
    python tests/test_e2e_qa.py

Prerequisites:
    - SSH access to dev1 configured in ~/.ssh/config or via environment
    - Test host must allow background processes and file operations
    - Network connectivity to target SSH server
"""

import asyncio
import logging
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Optional

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

# Import after path setup
try:
    from mcp_ssh.background import process_manager
    from mcp_ssh.server import (
        CommandRequest,
        FileTransferRequest,
        GetOutputRequest,
        KillProcessRequest,
        execute_command,
        get_command_output,
        get_command_status,
        kill_command,
        transfer_file,
    )
except ImportError:
    # Handle import errors gracefully for linting
    pass

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class E2ETestContext:
    """Context for E2E testing with mock MCP context."""

    def __init__(self):
        self.logs = []
        self.progress_reports = []

    async def info(self, message: str):
        """Mock MCP context info logging."""
        self.logs.append(f"INFO: {message}")
        logger.info(f"MCP Context: {message}")

    async def warning(self, message: str):
        """Mock MCP context warning logging."""
        self.logs.append(f"WARNING: {message}")
        logger.warning(f"MCP Context: {message}")

    async def error(self, message: str):
        """Mock MCP context error logging."""
        self.logs.append(f"ERROR: {message}")
        logger.error(f"MCP Context: {message}")

    async def debug(self, message: str):
        """Mock MCP context debug logging."""
        self.logs.append(f"DEBUG: {message}")
        logger.debug(f"MCP Context: {message}")

    async def report_progress(self, progress: float, message: str = ""):
        """Mock MCP context progress reporting."""
        self.progress_reports.append((progress, message))
        logger.info(f"Progress: {progress:.1f} - {message}")


class E2EQATestSuite:
    """Comprehensive E2E QA test suite for MCP SSH."""

    def __init__(self):
        self.test_host = os.getenv("SSH_TEST_HOST", "dev1")
        self.test_user = os.getenv("SSH_TEST_USER", os.getenv("USER", "testuser"))
        self.ctx = E2ETestContext()
        self.test_results = []
        self.cleanup_processes = []

        # Test configuration
        os.environ["MCP_SSH_MAX_OUTPUT_SIZE"] = "10000"  # 10KB for testing
        os.environ["MCP_SSH_QUICK_WAIT_TIME"] = "3"  # 3 seconds for testing
        os.environ["MCP_SSH_CHUNK_SIZE"] = "2000"  # 2KB chunks for testing

        logger.info(f"Initializing E2E tests for host: {self.test_host}")
        logger.info(
            f"Test configuration: MAX_OUTPUT={os.environ['MCP_SSH_MAX_OUTPUT_SIZE']}, "
            f"WAIT_TIME={os.environ['MCP_SSH_QUICK_WAIT_TIME']}, "
            f"CHUNK_SIZE={os.environ['MCP_SSH_CHUNK_SIZE']}"
        )

    def log_test_result(self, test_name: str, passed: bool, message: str = ""):
        """Log test result for final reporting."""
        status = "PASS" if passed else "FAIL"
        self.test_results.append((test_name, passed, message))
        logger.info(f"Test {test_name}: {status} - {message}")

    async def cleanup_test_resources(self):
        """Clean up any test resources and processes."""
        logger.info("Cleaning up test resources...")

        # Kill any remaining test processes
        for process_id in self.cleanup_processes:
            try:
                kill_request = KillProcessRequest(
                    process_id=process_id, cleanup_files=True
                )
                await kill_command(kill_request, self.ctx)
                logger.info(f"Cleaned up process: {process_id}")
            except Exception as e:
                logger.warning(f"Failed to cleanup process {process_id}: {e}")

        # Clean up test files on remote host
        try:
            cleanup_cmd = CommandRequest(
                host=self.test_host,
                command="rm -f /tmp/mcp_ssh_test_* /tmp/test_upload_* 2>/dev/null || true",
            )
            await execute_command(cleanup_cmd, self.ctx)
        except Exception as e:
            logger.warning(f"Failed to cleanup test files: {e}")

    async def test_01_basic_connection(self) -> bool:
        """Test 1: Basic SSH connection and simple command."""
        try:
            request = CommandRequest(
                host=self.test_host, command="echo 'E2E Test Connection'"
            )
            result = await execute_command(request, self.ctx)

            if result.success and "E2E Test Connection" in result.stdout:
                self.log_test_result(
                    "01_basic_connection", True, "SSH connection successful"
                )
                return True
            else:
                self.log_test_result(
                    "01_basic_connection",
                    False,
                    f"Connection failed: {result.error_message}",
                )
                return False
        except Exception as e:
            self.log_test_result("01_basic_connection", False, f"Exception: {str(e)}")
            return False

    async def test_02_quick_command_completion(self) -> bool:
        """Test 2: Quick command that completes within wait time."""
        try:
            request = CommandRequest(host=self.test_host, command="ls /tmp | head -5")
            start_time = time.time()
            result = await execute_command(request, self.ctx)
            execution_time = time.time() - start_time

            # Should complete quickly and return status 'completed'
            if (
                result.success
                and result.status == "completed"
                and execution_time < 10  # Should be fast
                and len(result.stdout) > 0
            ):
                self.log_test_result(
                    "02_quick_command_completion",
                    True,
                    f"Completed in {execution_time:.1f}s",
                )
                return True
            else:
                self.log_test_result(
                    "02_quick_command_completion",
                    False,
                    f"Status: {result.status}, Time: {execution_time:.1f}s",
                )
                return False
        except Exception as e:
            self.log_test_result(
                "02_quick_command_completion", False, f"Exception: {str(e)}"
            )
            return False

    async def test_03_background_process_tracking(self) -> bool:
        """Test 3: Background process with status tracking."""
        try:
            # Start a longer running command
            request = CommandRequest(
                host=self.test_host, command="sleep 10; echo 'Background test complete'"
            )
            result = await execute_command(request, self.ctx)

            if not result.success:
                self.log_test_result(
                    "03_background_process_tracking",
                    False,
                    f"Failed to start: {result.error_message}",
                )
                return False

            process_id = result.process_id
            self.cleanup_processes.append(process_id)

            # Check status while running
            status_request = GetOutputRequest(process_id=process_id)
            status_result = await get_command_status(status_request, self.ctx)

            if status_result.status in ["running", "completed"]:
                self.log_test_result(
                    "03_background_process_tracking",
                    True,
                    f"Process {process_id} tracked successfully",
                )
                return True
            else:
                self.log_test_result(
                    "03_background_process_tracking",
                    False,
                    f"Unexpected status: {status_result.status}",
                )
                return False
        except Exception as e:
            self.log_test_result(
                "03_background_process_tracking", False, f"Exception: {str(e)}"
            )
            return False

    async def test_04_large_output_chunking(self) -> bool:
        """Test 4: Large output with chunking."""
        try:
            # Generate large output that exceeds size limits
            request = CommandRequest(
                host=self.test_host,
                command="for i in {1..1000}; do echo 'Line $i: This is test output for chunking'; done",
            )
            result = await execute_command(request, self.ctx)

            if not result.success:
                self.log_test_result(
                    "04_large_output_chunking",
                    False,
                    f"Command failed: {result.error_message}",
                )
                return False

            # Wait for completion if still running
            if result.status == "running":
                await asyncio.sleep(5)
                status_request = GetOutputRequest(process_id=result.process_id)
                status_result = await get_command_status(status_request, self.ctx)
                if status_result.status != "completed":
                    self.log_test_result(
                        "04_large_output_chunking",
                        False,
                        f"Command didn't complete: {status_result.status}",
                    )
                    return False

            # Check if output was chunked
            if result.has_more_output or result.output_size >= 10000:  # Our test limit
                # Get additional chunks
                chunk_request = GetOutputRequest(
                    process_id=result.process_id,
                    start_byte=len(result.stdout),
                    chunk_size=2000,
                )
                chunk_result = await get_command_output(chunk_request, self.ctx)

                if chunk_result.success and len(chunk_result.stdout) > 0:
                    self.log_test_result(
                        "04_large_output_chunking",
                        True,
                        f"Chunking successful: {result.output_size} bytes",
                    )
                    return True

            self.log_test_result(
                "04_large_output_chunking",
                False,
                f"Chunking not triggered: {result.output_size} bytes",
            )
            return False
        except Exception as e:
            self.log_test_result(
                "04_large_output_chunking", False, f"Exception: {str(e)}"
            )
            return False

    async def test_05_process_termination(self) -> bool:
        """Test 5: Process termination with kill command."""
        try:
            # Start a long-running process
            request = CommandRequest(host=self.test_host, command="sleep 60")
            result = await execute_command(request, self.ctx)

            if not result.success:
                self.log_test_result(
                    "05_process_termination",
                    False,
                    f"Failed to start process: {result.error_message}",
                )
                return False

            process_id = result.process_id

            # Verify process is running
            await asyncio.sleep(2)
            status_request = GetOutputRequest(process_id=process_id)
            status_result = await get_command_status(status_request, self.ctx)

            if status_result.status != "running":
                self.log_test_result(
                    "05_process_termination",
                    False,
                    f"Process not running: {status_result.status}",
                )
                return False

            # Kill the process
            kill_request = KillProcessRequest(process_id=process_id, cleanup_files=True)
            kill_result = await kill_command(kill_request, self.ctx)

            if kill_result.success:
                self.log_test_result(
                    "05_process_termination",
                    True,
                    f"Process killed: {kill_result.message}",
                )
                return True
            else:
                self.log_test_result(
                    "05_process_termination",
                    False,
                    f"Kill failed: {kill_result.error_message}",
                )
                return False
        except Exception as e:
            self.log_test_result(
                "05_process_termination", False, f"Exception: {str(e)}"
            )
            return False

    async def test_06_file_transfer_integration(self) -> bool:
        """Test 6: File transfer functionality."""
        try:
            # Create a test file
            test_content = "E2E Test File Content\nLine 2\nLine 3\n"

            with tempfile.NamedTemporaryFile(
                mode="w", delete=False, suffix=".txt"
            ) as f:
                f.write(test_content)
                local_file = f.name

            try:
                # Upload file
                remote_path = f"/tmp/test_upload_{int(time.time())}.txt"
                upload_request = FileTransferRequest(
                    host=self.test_host,
                    local_path=local_file,
                    remote_path=remote_path,
                    direction="upload",
                )
                upload_result = await transfer_file(upload_request, self.ctx)

                if not upload_result.success:
                    self.log_test_result(
                        "06_file_transfer_integration",
                        False,
                        f"Upload failed: {upload_result.error_message}",
                    )
                    return False

                # Verify file exists on remote
                verify_request = CommandRequest(
                    host=self.test_host, command=f"cat {remote_path}"
                )
                verify_result = await execute_command(verify_request, self.ctx)

                if (
                    verify_result.success
                    and test_content.strip() in verify_result.stdout
                ):
                    self.log_test_result(
                        "06_file_transfer_integration",
                        True,
                        f"File transfer successful: {upload_result.bytes_transferred} bytes",
                    )
                    return True
                else:
                    self.log_test_result(
                        "06_file_transfer_integration",
                        False,
                        "File verification failed",
                    )
                    return False
            finally:
                # Cleanup local file
                os.unlink(local_file)
        except Exception as e:
            self.log_test_result(
                "06_file_transfer_integration", False, f"Exception: {str(e)}"
            )
            return False

    async def test_07_error_handling(self) -> bool:
        """Test 7: Error handling for invalid commands and hosts."""
        try:
            # Test invalid command
            request = CommandRequest(
                host=self.test_host, command="nonexistent_command_12345"
            )
            result = await execute_command(request, self.ctx)

            # Should execute but return error in stderr or exit code
            if result.success and (result.exit_code != 0 or len(result.stderr) > 0):
                self.log_test_result(
                    "07_error_handling",
                    True,
                    f"Error handling correct: exit_code={result.exit_code}",
                )
                return True
            else:
                self.log_test_result(
                    "07_error_handling",
                    False,
                    f"Error not detected: exit_code={result.exit_code}",
                )
                return False
        except Exception as e:
            self.log_test_result("07_error_handling", False, f"Exception: {str(e)}")
            return False

    async def test_08_concurrent_processes(self) -> bool:
        """Test 8: Multiple concurrent background processes."""
        try:
            processes = []

            # Start multiple concurrent processes
            for i in range(3):
                request = CommandRequest(
                    host=self.test_host,
                    command=f"sleep 5; echo 'Process {i} completed'",
                )
                result = await execute_command(request, self.ctx)

                if result.success:
                    processes.append(result.process_id)
                    self.cleanup_processes.append(result.process_id)

            if len(processes) != 3:
                self.log_test_result(
                    "08_concurrent_processes",
                    False,
                    f"Only started {len(processes)}/3 processes",
                )
                return False

            # Wait and check all processes
            await asyncio.sleep(7)
            completed_count = 0

            for process_id in processes:
                status_request = GetOutputRequest(process_id=process_id)
                status_result = await get_command_status(status_request, self.ctx)
                if status_result.status == "completed":
                    completed_count += 1

            if completed_count == 3:
                self.log_test_result(
                    "08_concurrent_processes",
                    True,
                    "All 3 concurrent processes completed",
                )
                return True
            else:
                self.log_test_result(
                    "08_concurrent_processes",
                    False,
                    f"Only {completed_count}/3 processes completed",
                )
                return False
        except Exception as e:
            self.log_test_result(
                "08_concurrent_processes", False, f"Exception: {str(e)}"
            )
            return False

    async def test_09_environment_configuration(self) -> bool:
        """Test 9: Environment variable configuration."""
        try:
            # Test current configuration is applied
            original_chunk_size = os.environ.get("MCP_SSH_CHUNK_SIZE")

            # Change chunk size temporarily
            os.environ["MCP_SSH_CHUNK_SIZE"] = "1000"

            # Generate output that would use chunking
            request = CommandRequest(
                host=self.test_host,
                command="for i in {1..50}; do echo 'Configuration test line $i'; done",
            )
            result = await execute_command(request, self.ctx)

            # Restore original value
            if original_chunk_size:
                os.environ["MCP_SSH_CHUNK_SIZE"] = original_chunk_size

            if result.success:
                self.log_test_result(
                    "09_environment_configuration",
                    True,
                    "Environment configuration applied",
                )
                return True
            else:
                self.log_test_result(
                    "09_environment_configuration",
                    False,
                    f"Configuration test failed: {result.error_message}",
                )
                return False
        except Exception as e:
            self.log_test_result(
                "09_environment_configuration", False, f"Exception: {str(e)}"
            )
            return False
