"""
Tests for SSH configuration parsing functionality

This module tests the SSH configuration file parsing, including
various syntax formats, host filtering, and error handling.
"""

from unittest.mock import mock_open, patch

import pytest

from mcp_ssh.ssh import parse_ssh_config
from tests.conftest import TestConstants


class TestSSHConfig:
    """Test SSH configuration parsing"""

    def test_parse_empty_config_file_not_exists(self):
        """Test parsing when no SSH config exists"""
        with patch("os.path.exists", return_value=False):
            result = parse_ssh_config()
            assert result == {}

    def test_parse_valid_config(self):
        """Test parsing a valid SSH config"""
        with (
            patch("os.path.exists", return_value=True),
            patch(
                "builtins.open",
                mock_open(read_data=TestConstants.SAMPLE_SSH_CONFIG_CONTENT),
            ),
        ):
            result = parse_ssh_config()

            # Should include regular hosts
            assert "test-host" in result
            assert result["test-host"]["hostname"] == "example.com"
            assert result["test-host"]["user"] == "testuser"
            assert result["test-host"]["port"] == "22"
            assert result["test-host"]["identityfile"] == "~/.ssh/test_key"

            assert "prod-server" in result
            assert result["prod-server"]["hostname"] == "prod.example.com"
            assert result["prod-server"]["user"] == "deploy"

            assert "staging" in result
            assert result["staging"]["hostname"] == "staging.example.com"
            assert result["staging"]["user"] == "ubuntu"
            assert result["staging"]["port"] == "2222"

            # Should skip wildcard hosts
            assert "*.internal" not in result
            assert "development-*" not in result

    def test_parse_config_with_equals_syntax(self):
        """Test parsing SSH config with key=value syntax"""
        config_content = """Host equals-host
HostName=equals.example.com
User=equalsuser
Port=3333
"""

        with (
            patch("os.path.exists", return_value=True),
            patch("builtins.open", mock_open(read_data=config_content)),
        ):
            result = parse_ssh_config()

            assert "equals-host" in result
            assert result["equals-host"]["hostname"] == "equals.example.com"
            assert result["equals-host"]["user"] == "equalsuser"
            assert result["equals-host"]["port"] == "3333"

    def test_parse_config_with_comments_and_empty_lines(self):
        """Test parsing config with comments and empty lines"""
        config_content = """# This is a comment

Host clean-host
    # Another comment
    HostName clean.example.com

    User cleanuser
    # Final comment
"""

        with (
            patch("os.path.exists", return_value=True),
            patch("builtins.open", mock_open(read_data=config_content)),
        ):
            result = parse_ssh_config()

            assert "clean-host" in result
            assert result["clean-host"]["hostname"] == "clean.example.com"
            assert result["clean-host"]["user"] == "cleanuser"

    def test_parse_config_file_error(self):
        """Test parsing when file read fails"""
        with (
            patch("os.path.exists", return_value=True),
            patch("builtins.open", side_effect=OSError("Permission denied")),
        ):
            result = parse_ssh_config()
            assert result == {}

    def test_parse_config_with_fixture(self, temp_ssh_config):
        """Test parsing SSH config using fixture"""
        with patch("os.path.expanduser", return_value=temp_ssh_config):
            result = parse_ssh_config()

            assert "test-fixture" in result
            assert result["test-fixture"]["hostname"] == "fixture.example.com"
            assert result["test-fixture"]["user"] == "fixtureuser"
            assert result["test-fixture"]["port"] == "2222"

            assert "another-fixture" in result
            assert result["another-fixture"]["hostname"] == "another.fixture.com"
            assert result["another-fixture"]["user"] == "admin"

    def test_parse_config_host_without_hostname(self):
        """Test parsing config where host has no explicit hostname"""
        config_content = """Host implicit-hostname
    User implicituser
    Port 2222
"""

        with (
            patch("os.path.exists", return_value=True),
            patch("builtins.open", mock_open(read_data=config_content)),
        ):
            result = parse_ssh_config()

            assert "implicit-hostname" in result
            assert result["implicit-hostname"]["user"] == "implicituser"
            assert result["implicit-hostname"]["port"] == "2222"
            # hostname should not be present, defaults to host name when used

    def test_parse_config_malformed_lines(self):
        """Test parsing config with malformed lines"""
        config_content = """Host robust-host
    HostName robust.example.com
    MalformedLine
    User robustuser
    AnotherMalformedLine
    Port 22
"""

        with (
            patch("os.path.exists", return_value=True),
            patch("builtins.open", mock_open(read_data=config_content)),
        ):
            result = parse_ssh_config()

            # Should still parse valid lines
            assert "robust-host" in result
            assert result["robust-host"]["hostname"] == "robust.example.com"
            assert result["robust-host"]["user"] == "robustuser"
            assert result["robust-host"]["port"] == "22"
