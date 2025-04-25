"""
MCP SSH Server - A Model Context Protocol server with SSH capabilities
"""

from pydantic import BaseModel, Field

from mcp.server.fastmcp import FastMCP, Context
from mcp_ssh.ssh import get_ssh_client_from_config, execute_ssh_command

# Create MCP server
mcp = FastMCP("MCP SSH Server")

class SSHConfig(BaseModel):
    """SSH configuration model"""
    config_host: str = Field(..., description="Host entry to use from SSH config")

class SSHCommand(BaseModel):
    """SSH command model"""
    command: str = Field(..., description="Command to execute")
    host: str = Field(..., description="Host to execute command on")

@mcp.tool()
def ssh_connect(config: SSHConfig) -> str:
    """Connect to an SSH server using the SSH config host name"""
    client = get_ssh_client_from_config(config.config_host)
    
    if client is None:
        return f"Failed to connect to host '{config.config_host}'. Please check your SSH config."
    
    return f"Successfully connected to {config.config_host}"

@mcp.tool()
def execute_command(cmd: SSHCommand) -> str:
    """Execute a command on the SSH server"""
    client = get_ssh_client_from_config(cmd.host)
    
    if client is None:
        return f"Failed to connect to host '{cmd.host}'. Please check your SSH config."
    
    stdout, stderr = execute_ssh_command(client, cmd.command)
    
    result = []
    if stdout:
        result.append(f"STDOUT:\n{stdout}")
    if stderr:
        result.append(f"STDERR:\n{stderr}")
        
    return "\n".join(result) if result else "Command executed successfully"

@mcp.resource("ssh://hosts")
def list_ssh_hosts() -> str:
    """List all available hosts from SSH config"""
    from mcp_ssh.ssh import parse_ssh_config
    ssh_configs = parse_ssh_config()
    
    if not ssh_configs:
        return "No hosts found in SSH config or config file does not exist."
    
    result = ["Available SSH Hosts:"]
    for host, config in ssh_configs.items():
        host_info = config.get('hostname', host)
        user_info = f" (User: {config.get('user')})" if 'user' in config else ""
        result.append(f"- {host} -> {host_info}{user_info}")
    
    return "\n".join(result)

@mcp.prompt()
def ssh_help() -> str:
    """Get help about using the SSH tools"""
    return """I can help you with SSH operations:

1. List available SSH hosts:
   - Use the 'ssh://hosts' resource to see all configured hosts

2. Connect to an SSH server:
   - Use the 'ssh_connect' tool with your SSH config host name
   - Example: ssh_connect(config_host="your-host")

3. Execute commands:
   - Use the 'execute_command' tool to run commands on remote hosts
   - Specify the host (from SSH config) and command to execute
   - Example: execute_command(host="your-host", command="ls -la")

Example usage:
1. First, check available hosts using the 'ssh://hosts' resource
2. Connect to a host using the 'ssh_connect' tool with the config host name
3. Execute commands using the 'execute_command' tool

Would you like to try any of these operations?"""

def main():
    """Main entry point for the MCP server"""
    mcp.run()

if __name__ == "__main__":
    main() 