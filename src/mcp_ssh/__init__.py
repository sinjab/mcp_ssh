"""
MCP SSH - A Model Context Protocol server with SSH capabilities
"""

from .server import (
    SSHCommand,
    execute_command,
    list_ssh_hosts,
    main,
    mcp,
)

__version__ = "0.1.0"
__all__ = [
    "mcp",
    "main",
    "execute_command",
    "list_ssh_hosts",
    "SSHCommand",
]
