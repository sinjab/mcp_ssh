"""
MCP SSH - A Model Context Protocol server with SSH capabilities
"""

from .server import (
    mcp,
    main,
    execute_command,
    list_ssh_hosts,
    SSHCommand,
)

__version__ = "0.1.0"
__all__ = [
    "mcp",
    "main",
    "execute_command",
    "list_ssh_hosts",
    "SSHCommand",
]
