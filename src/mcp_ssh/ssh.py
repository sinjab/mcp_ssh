"""
SSH Client - Core SSH functionality
"""

import logging
import os
import time
from pathlib import Path

import paramiko

from .background import BackgroundProcess

# Timeout configuration from environment variables
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

# Set up logging to file
log_dir = Path(__file__).parent.parent.parent / "logs"
log_dir.mkdir(exist_ok=True)
log_file = log_dir / "ssh.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(),  # Keep console output as well
    ],
)
logger = logging.getLogger(__name__)

# Log environment variables (showing SSH_KEY_PHRASE)
env_vars = {
    k: (
        v
        if k == "SSH_KEY_PHRASE"
        else ("***" if "KEY" in k or "SECRET" in k or "PASS" in k else v)
    )
    for k, v in os.environ.items()
}
logger.debug(f"Environment variables: {env_vars}")


def parse_ssh_config() -> dict[str, dict[str, str]]:
    """Parse the SSH config file (~/.ssh/config) and return host configurations"""
    config_file = os.path.expanduser("~/.ssh/config")
    logger.debug(f"Reading SSH config from: {config_file}")

    if not os.path.exists(config_file):
        logger.error(f"SSH config file not found at: {config_file}")
        return {}

    hosts: dict[str, dict[str, str]] = {}
    current_host = None

    try:
        with open(config_file) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                if line.lower().startswith("host "):
                    host_pattern = line[5:].strip()
                    if "*" in host_pattern or "?" in host_pattern:
                        current_host = None
                        continue
                    current_host = host_pattern
                    hosts[current_host] = {}
                    logger.debug(f"Found host: {current_host}")
                elif current_host and "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip().lower()
                    value = value.strip()
                    hosts[current_host][key] = value
                    logger.debug(f"Added config for {current_host}: {key}={value}")
                elif current_host and " " in line:
                    parts = line.split(" ", 1)
                    key = parts[0].strip().lower()
                    value = parts[1].strip() if len(parts) > 1 else ""
                    hosts[current_host][key] = value
                    logger.debug(f"Added config for {current_host}: {key}={value}")

        logger.debug(f"Parsed hosts: {list(hosts.keys())}")
        return hosts
    except Exception as e:
        logger.error(f"Error parsing SSH config: {str(e)}")
        return {}


def get_ssh_client_from_config(config_host: str) -> paramiko.SSHClient | None:
    """Get an SSH client connected using only the SSH config host name"""
    logger.debug(f"Attempting to connect to host: {config_host}")
    hosts = parse_ssh_config()

    if config_host not in hosts:
        logger.error(f"Host '{config_host}' not found in SSH config")
        return None

    host_config = hosts[config_host]
    logger.debug(f"Found config for {config_host}: {host_config}")

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        # Get the key file path from config or environment
        key_filename = host_config.get(
            "identityfile", os.environ.get("SSH_KEY_FILE", "~/.ssh/id_rsa")
        )
        loaded_key = None

        if key_filename:
            key_filename = os.path.expanduser(key_filename.strip("\"'"))
            logger.debug(f"Using key file: {key_filename}")

            # If key is encrypted, use the passphrase from environment
            if os.path.exists(key_filename):
                try:
                    # Try to load the key without passphrase first
                    logger.debug("Attempting to load key without passphrase")
                    loaded_key = paramiko.RSAKey.from_private_key_file(key_filename)
                    logger.debug("Successfully loaded key without passphrase")
                except paramiko.SSHException as e:
                    logger.debug(f"Key requires passphrase: {str(e)}")
                    # If that fails, try with the passphrase
                    ssh_key_phrase = os.environ.get("SSH_KEY_PHRASE")
                    if ssh_key_phrase:
                        logger.debug(
                            f"SSH_KEY_PHRASE is set in environment: {ssh_key_phrase}"
                        )
                        try:
                            loaded_key = paramiko.RSAKey.from_private_key_file(
                                key_filename, password=ssh_key_phrase
                            )
                            logger.debug("Successfully loaded key with passphrase")

                            # Log key details
                            if loaded_key:
                                # Get the fingerprint
                                fingerprint = loaded_key.get_fingerprint().hex()
                                logger.debug(f"Key fingerprint: {fingerprint}")

                                # Get the public key
                                public_key = loaded_key.get_base64()
                                logger.debug(f"Public key: {public_key}")

                                # Get the key type
                                key_type = loaded_key.get_name()
                                logger.debug(f"Key type: {key_type}")

                                # Get the key size
                                key_size = loaded_key.get_bits()
                                logger.debug(f"Key size: {key_size} bits")
                        except Exception as e:
                            logger.error(
                                f"Failed to load key with passphrase: {str(e)}"
                            )
                            return None
                    else:
                        logger.error(
                            "Private key is encrypted but SSH_KEY_PHRASE is not set in environment"
                        )
                        return None
            else:
                logger.error(f"Key file does not exist: {key_filename}")
                return None
        else:
            logger.debug("No key file specified in SSH config or environment")

        connect_kwargs = {
            "hostname": host_config.get("hostname", config_host),
            "port": int(host_config.get("port", 22)),
            "username": host_config.get("user"),
            "look_for_keys": True,
            "timeout": SSH_CONNECT_TIMEOUT,
        }

        # Add the loaded key if we have one
        if loaded_key:
            connect_kwargs["pkey"] = loaded_key

        # Remove None values
        connect_kwargs = {k: v for k, v in connect_kwargs.items() if v is not None}
        logger.debug(f"Connection parameters: {connect_kwargs}")

        client.connect(**connect_kwargs)
        logger.info(f"Successfully connected to {config_host}")
        return client
    except Exception as e:
        logger.error(f"Failed to connect to {config_host}: {str(e)}")
        return None


def execute_ssh_command(
    client: paramiko.SSHClient, command: str
) -> tuple[str | None, str | None, int | None]:
    """Execute a command on the SSH server with proper shell handling"""
    try:
        # For simple commands without shell features, execute directly
        if _is_simple_command(command):
            stdin, stdout, stderr = client.exec_command(
                command, get_pty=False, timeout=SSH_COMMAND_TIMEOUT
            )
        else:
            # For complex commands with shell features, use shell execution
            # but wrap in a way that handles special characters safely
            safe_command = _prepare_shell_command(command)
            stdin, stdout, stderr = client.exec_command(
                safe_command, get_pty=False, timeout=SSH_COMMAND_TIMEOUT
            )

        # Read output with timeout to prevent hanging
        start_time = time.time()
        stdout_str = ""
        stderr_str = ""

        # Read stdout with timeout
        while not stdout.channel.exit_status_ready():
            if time.time() - start_time > SSH_READ_TIMEOUT:
                logger.warning(
                    f"Command execution timed out after {SSH_READ_TIMEOUT} seconds"
                )
                break
            time.sleep(0.1)

        stdout_str = stdout.read().decode("utf-8")
        stderr_str = stderr.read().decode("utf-8")

        # Get exit code
        exit_code = stdout.channel.recv_exit_status()

        logger.debug(f"Command executed with exit code: {exit_code}")
        logger.debug(f"stdout: {stdout_str}")
        logger.debug(f"stderr: {stderr_str}")

        return stdout_str, stderr_str, exit_code
    except Exception as e:
        logger.error(f"SSH command execution failed: {str(e)}")
        return None, str(e), None


def _is_simple_command(command: str) -> bool:
    """Check if command is simple enough to execute without shell"""
    # Commands that need shell: pipes, redirects, variables, etc.
    shell_features = ["|", ">", "<", ">>", "<<", "&&", "||", ";", "$", "`", "$(", "${"]

    # Also check for complex quoting patterns that might cause shell issues
    complex_quoting_patterns = [
        "'\"'",  # Mixed quotes
        "\"'",  # Mixed quotes
        "\\'",  # Escaped single quotes
        '\\"',  # Escaped double quotes
    ]

    for feature in shell_features:
        if feature in command:
            return False

    for pattern in complex_quoting_patterns:
        if pattern in command:
            return False

    return True


def _prepare_shell_command(command: str) -> str:
    """Prepare a command for safe shell execution"""
    import shlex

    try:
        # For commands with complex quoting, try a different approach
        if _has_complex_quoting(command):
            # Use a heredoc approach to avoid shell parsing issues
            safe_command = _prepare_heredoc_command(command)
        else:
            # Use shlex to properly quote the command for shell execution
            quoted_command = shlex.quote(command)
            safe_command = f"bash -c {quoted_command}"

        logger.debug(f"Original command: {command}")
        logger.debug(f"Safe command: {safe_command}")

        return safe_command
    except Exception as e:
        logger.warning(f"Failed to prepare shell command, using as-is: {str(e)}")
        return command


def _has_complex_quoting(command: str) -> bool:
    """Check if command has complex quoting that might cause shell issues"""
    complex_patterns = [
        "'\"'",  # Mixed quotes
        "\"'",  # Mixed quotes
        "\\'",  # Escaped single quotes
        '\\"',  # Escaped double quotes
        "\\\\",  # Double backslashes
    ]

    for pattern in complex_patterns:
        if pattern in command:
            return True

    return False


def _prepare_heredoc_command(command: str) -> str:
    """Prepare command using heredoc to avoid shell parsing issues"""
    # Use a heredoc to pass the command without shell interpretation
    heredoc_delimiter = "EOF_CMD"

    # Escape the delimiter if it appears in the command
    while heredoc_delimiter in command:
        heredoc_delimiter = f"EOF_{heredoc_delimiter}"

    heredoc_command = f"""bash << '{heredoc_delimiter}'
{command}
{heredoc_delimiter}"""

    return heredoc_command


def transfer_file_scp(
    client: paramiko.SSHClient, local_path: str, remote_path: str, direction: str
) -> int:
    """Transfer files using SCP protocol"""
    scp = None
    try:
        # Validate source file exists before transfer
        if direction == "upload":
            # Check local file exists for upload
            if not os.path.exists(local_path):
                raise FileNotFoundError(f"Local file does not exist: {local_path}")
            if not os.path.isfile(local_path):
                raise ValueError(f"Local path is not a file: {local_path}")
            logger.info(f"Validated local file exists: {local_path}")
        elif direction == "download":
            # Check remote file exists for download
            sftp = client.open_sftp()
            try:
                sftp.stat(remote_path)
                logger.info(f"Validated remote file exists: {remote_path}")
            except FileNotFoundError:
                raise FileNotFoundError(
                    f"Remote file does not exist: {remote_path}"
                ) from None
            finally:
                sftp.close()
        else:
            raise ValueError(
                f"Invalid direction: {direction}. Use 'upload' or 'download'"
            )

        scp = client.open_sftp()

        # Set timeout for SFTP operations
        scp.get_channel().settimeout(SSH_TRANSFER_TIMEOUT)

        if direction == "upload":
            scp.put(local_path, remote_path)
            # Get file size for bytes transferred
            bytes_transferred = os.path.getsize(local_path)
        elif direction == "download":
            scp.get(remote_path, local_path)
            # Get file size for bytes transferred
            bytes_transferred = os.path.getsize(local_path)
        else:
            raise ValueError(
                f"Invalid direction: {direction}. Use 'upload' or 'download'"
            )

        logger.info(f"Successfully transferred {bytes_transferred} bytes ({direction})")
        return bytes_transferred

    except Exception as e:
        logger.error(f"File transfer failed: {str(e)}")
        raise
    finally:
        if scp:
            scp.close()


def execute_command_background(
    client: paramiko.SSHClient, command: str, output_file: str, error_file: str
) -> int:
    """Execute command in background, return PID."""

    # Simple background wrapper
    bg_command = f"""
    nohup bash -c '
        {command}
        echo $? > {output_file}.exit
    ' > {output_file} 2> {error_file} &
    echo $!
    """

    stdin, stdout, stderr = client.exec_command(bg_command, timeout=SSH_COMMAND_TIMEOUT)

    # Read PID with timeout
    start_time = time.time()
    pid_output = ""

    while not stdout.channel.exit_status_ready():
        if time.time() - start_time > SSH_READ_TIMEOUT:
            logger.warning(
                f"Background command setup timed out after {SSH_READ_TIMEOUT} seconds"
            )
            break
        time.sleep(0.1)

    pid_output = stdout.read().decode().strip()

    try:
        return int(pid_output)
    except ValueError:
        raise RuntimeError(f"Failed to get PID: {pid_output}") from None


def get_process_output(
    client: paramiko.SSHClient, process: BackgroundProcess, max_size: int
) -> tuple[str, str, str, int | None]:
    """Get current output from process files."""

    # Check if process is still running
    if process.pid:
        stdin, stdout, stderr = client.exec_command(
            f"kill -0 {process.pid} 2>/dev/null && echo 'RUNNING' || echo 'STOPPED'",
            timeout=SSH_COMMAND_TIMEOUT,
        )
        status_check = stdout.read().decode().strip()
        status = "running" if status_check == "RUNNING" else "completed"
    else:
        status = "completed"

    # Get exit code if completed
    exit_code = None
    if status == "completed":
        stdin, stdout, stderr = client.exec_command(
            f"cat {process.output_file}.exit 2>/dev/null || echo ''",
            timeout=SSH_COMMAND_TIMEOUT,
        )
        exit_output = stdout.read().decode().strip()
        if exit_output.isdigit():
            exit_code = int(exit_output)

    # Get output with size limit
    stdin, stdout, stderr = client.exec_command(
        f"head -c {max_size} {process.output_file} 2>/dev/null || echo ''",
        timeout=SSH_COMMAND_TIMEOUT,
    )
    output = stdout.read().decode()

    # Get errors with size limit
    stdin, stdout, stderr = client.exec_command(
        f"head -c {max_size//2} {process.error_file} 2>/dev/null || echo ''",
        timeout=SSH_COMMAND_TIMEOUT,
    )
    errors = stdout.read().decode()

    return status, output, errors, exit_code


def get_output_chunk(
    client: paramiko.SSHClient,
    process: BackgroundProcess,
    start_byte: int,
    chunk_size: int,
) -> tuple[str, bool]:
    """Get specific chunk of output."""

    # Get chunk from specific byte position
    stdin, stdout, stderr = client.exec_command(
        f"tail -c +{start_byte + 1} {process.output_file} 2>/dev/null | head -c {chunk_size}",
        timeout=SSH_COMMAND_TIMEOUT,
    )
    chunk = stdout.read().decode()

    # Check if there's more data
    stdin, stdout, stderr = client.exec_command(
        f"tail -c +{start_byte + chunk_size + 1} {process.output_file} 2>/dev/null | head -c 1",
        timeout=SSH_COMMAND_TIMEOUT,
    )
    has_more = bool(stdout.read().decode().strip())

    return chunk, has_more


def kill_background_process(
    client: paramiko.SSHClient, process: BackgroundProcess
) -> tuple[bool, str]:
    """
    Kill a background process.

    Returns (success, message) tuple.
    Uses escalating kill signals: TERM -> KILL
    """
    if not process.pid:
        return False, "No PID available for process"

    try:
        # First try graceful termination (SIGTERM)
        stdin, stdout, stderr = client.exec_command(
            f"kill {process.pid} 2>&1", timeout=SSH_COMMAND_TIMEOUT
        )
        stdout.read().decode().strip()  # Read but don't store result

        # Wait a moment for graceful shutdown
        time.sleep(2)

        # Check if process is still running
        stdin, stdout, stderr = client.exec_command(
            f"kill -0 {process.pid} 2>/dev/null && echo 'RUNNING' || echo 'STOPPED'",
            timeout=SSH_COMMAND_TIMEOUT,
        )
        status_check = stdout.read().decode().strip()

        if status_check == "STOPPED":
            # Process terminated gracefully
            return True, f"Process {process.pid} terminated gracefully"

        # Process still running, use force (SIGKILL)
        stdin, stdout, stderr = client.exec_command(
            f"kill -9 {process.pid} 2>&1", timeout=SSH_COMMAND_TIMEOUT
        )
        kill_result = stdout.read().decode().strip()

        # Final check
        stdin, stdout, stderr = client.exec_command(
            f"kill -0 {process.pid} 2>/dev/null && echo 'RUNNING' || echo 'STOPPED'",
            timeout=SSH_COMMAND_TIMEOUT,
        )
        final_status = stdout.read().decode().strip()

        if final_status == "STOPPED":
            return True, f"Process {process.pid} force killed"
        else:
            return False, f"Failed to kill process {process.pid}: {kill_result}"

    except Exception as e:
        return False, f"Error killing process: {str(e)}"


def cleanup_process_files(
    client: paramiko.SSHClient, process: BackgroundProcess
) -> bool:
    """Clean up temporary files for a process."""
    try:
        # Remove output, error, and exit files
        cleanup_cmd = f"rm -f {process.output_file} {process.error_file} {process.output_file}.exit 2>/dev/null"
        stdin, stdout, stderr = client.exec_command(
            cleanup_cmd, timeout=SSH_COMMAND_TIMEOUT
        )
        return True
    except Exception:
        return False
