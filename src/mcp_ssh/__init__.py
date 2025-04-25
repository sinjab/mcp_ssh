"""
MCP SSH - A Model Context Protocol server with SSH capabilities
"""

from .server import (
    mcp,
    main,
    ssh_connect,
    execute_command,
    list_ssh_hosts,
    SSHConfig,
    SSHCommand,
)

__version__ = "0.1.0"
__all__ = [
    "mcp",
    "main",
    "ssh_connect",
    "execute_command",
    "list_ssh_hosts",
    "SSHConfig",
    "SSHCommand",
]
