# MCP SSH

A Model Context Protocol (MCP) server with SSH capabilities, demonstrating core MCP concepts including tools, resources, and prompts.

## Features

- **MCP Server**: A fully functional MCP server with:
  - **Tools**: Execute commands on remote servers via SSH
  - **Resources**: List available SSH hosts from your config
  - **Prompts**: Help prompt that provides guidance on using the server
- **SSH Integration**: Built-in SSH client capabilities:
  - Execute commands remotely using SSH configs
  - Host management from SSH config
  - Support for encrypted private keys

## Installation

### Using pip

```bash
pip install mcp_ssh
```

### From source

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/mcp_ssh.git
   cd mcp_ssh
   ```

2. Install in development mode:
   ```bash
   pip install -e .
   ```

## Usage

### Running the MCP Server

```bash
mcp_ssh
```

### Using the SSH Client

```python
from mcp_ssh import execute_command

# Execute a command on a remote host
stdout, stderr = execute_command(host="your-host", command="ls -la")
```

### Client Configuration

To use this MCP server with a client, add the following configuration to your client's settings:

```json
{
  "mcpServers": {
    "mcp_ssh": {
      "command": "uv",
      "args": [
        "--directory",
        "<your-project-directory>",
        "run",
        "mcp_ssh"
      ],
      "env": {
        "SSH_KEY_PHRASE": "your-key-passphrase",
        "SSH_KEY_FILE": "~/.ssh/id_rsa"
      }
    }
  }
}
```

#### Environment Variables

- `SSH_KEY_PHRASE`: The passphrase for your encrypted private key
- `SSH_KEY_FILE`: The path to your private key file (defaults to `~/.ssh/id_rsa` if not specified)

### SSH Configuration

The server uses your local SSH config file (`~/.ssh/config`) for host configurations. Each host entry can specify:

- `HostName`: The actual hostname or IP address
- `User`: The username to use
- `Port`: The SSH port (defaults to 22)
- `IdentityFile`: The private key file to use (overrides `SSH_KEY_FILE`)

Example SSH config:
```
Host example-host
    HostName example.com
    User username
    Port 22
    IdentityFile ~/.ssh/id_rsa
```

## Development

### Project Structure

```
mcp_ssh/
├── src/
│   └── mcp_ssh/
│       ├── __init__.py
│       ├── server.py
│       └── ssh.py
├── pyproject.toml
└── README.md
```

### Building

```bash
# Install build dependencies
pip install hatch

# Build the package
hatch build
```

## License

[Your chosen license]

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
