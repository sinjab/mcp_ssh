"""
Test configuration and fixtures for MCP SSH tests

This module contains shared test configuration, fixtures, and utilities
used across the test suite.
"""

import os
import tempfile
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def temp_ssh_config():
    """Create a temporary SSH config file for testing"""
    config_content = """Host test-fixture
    HostName fixture.example.com
    User fixtureuser
    Port 2222
    IdentityFile ~/.ssh/fixture_key

Host another-fixture
    HostName another.fixture.com
    User admin
"""

    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".config") as f:
        f.write(config_content)
        f.flush()
        yield f.name

    os.unlink(f.name)


@pytest.fixture
def mock_ssh_client():
    """Create a mock SSH client for testing"""
    client = MagicMock()

    # Mock successful connection
    client.connect.return_value = None
    client.close.return_value = None

    # Mock command execution
    mock_stdin = MagicMock()
    mock_stdout = MagicMock()
    mock_stderr = MagicMock()

    mock_stdout.read.return_value = b"command output"
    mock_stderr.read.return_value = b""

    client.exec_command.return_value = (mock_stdin, mock_stdout, mock_stderr)

    return client


@pytest.fixture
def sample_ssh_config():
    """Sample SSH configuration for testing"""
    return {
        "test-host": {
            "hostname": "example.com",
            "user": "testuser",
            "port": "22",
            "identityfile": "~/.ssh/test_key",
        },
        "another-host": {
            "hostname": "another.example.com",
            "user": "admin",
            "port": "2222",
        },
        "minimal-host": {"hostname": "minimal.example.com"},
    }


class TestConstants:
    """Test constants and sample data"""

    SAMPLE_SSH_CONFIG_CONTENT = """# Test SSH Configuration
Host test-host
    HostName example.com
    User testuser
    Port 22
    IdentityFile ~/.ssh/test_key

Host prod-server
    HostName prod.example.com
    User deploy
    Port 22

Host staging
    HostName staging.example.com
    User ubuntu
    Port 2222
    IdentityFile ~/.ssh/staging_key

# Wildcard patterns (should be ignored)
Host *.internal
    User internal

Host development-*
    User dev
"""

    SAMPLE_COMMAND_OUTPUT = "total 24\ndrwxr-xr-x 3 user user 4096 Jul 26 12:00 ."
    SAMPLE_ERROR_OUTPUT = "ls: cannot access '/nonexistent': No such file or directory"
