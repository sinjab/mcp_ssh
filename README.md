# MCP SSH

A Model Context Protocol (MCP) server with SSH capabilities, demonstrating core MCP concepts including tools, resources, and prompts.

## Features

- **MCP Server**: A fully functional MCP server with:
  - **Tools**: A simple calculator tool that can add two numbers
  - **Resources**: A greeting resource that provides personalized messages
  - **Prompts**: A help prompt that provides guidance on using the server
- **SSH Integration**: Built-in SSH client capabilities:
  - Connect to SSH servers using local SSH configs
  - Execute commands remotely
  - Interactive shell support
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
from mcp_ssh import ssh_connect, execute_command

# Connect to a host using SSH config
client = ssh_connect(use_config=True, config_host="your-host")

# Execute a command
stdout, stderr = execute_command(client, "ls -la")
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
        "/Users/khs/Documents/projects/mcp_ssh",
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
Host dev1
    HostName 147.135.105.207
    User root
    Port 2299
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
