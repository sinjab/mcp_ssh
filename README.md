# MCP SSH

A production-ready Model Context Protocol (MCP) server with SSH capabilities, featuring enterprise-grade testing infrastructure and development tools.

[![CI](https://github.com/sinjab/mcp_ssh/workflows/CI/badge.svg)](https://github.com/sinjab/mcp_ssh/actions)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![MCP](https://img.shields.io/badge/MCP-Model%20Context%20Protocol-green)](https://modelcontextprotocol.io/)
[![Tests](https://img.shields.io/badge/tests-107%20tests-brightgreen)](#testing)
[![Production Ready](https://img.shields.io/badge/status-production%20ready-success)](#quality-assurance-validation)

## Features

- **MCP Server**: Execute SSH commands, transfer files, list hosts, interactive help
- **SSH Integration**: Config parsing, encrypted keys, connection management, file transfers
- **Structured Output**: Rich JSON schemas for programmatic integration
- **Progress Tracking**: Real-time progress reporting and logging  
- **Production Ready**: 107 tests, comprehensive QA validation
- **Background Execution**: All commands run in background with process tracking
- **Timeout Protection**: Comprehensive timeout handling prevents hanging operations
- **Security Controls**: Configurable command validation with blacklist/whitelist patterns
- **Performance Optimized**: Connection reuse and output management optimizations

## Quick Start

```bash
# Install with uv (recommended)
git clone https://github.com/sinjab/mcp_ssh.git
cd mcp_ssh
uv sync

# Run server
uv run mcp_ssh

# Development mode with hot reload
uv run mcp dev src/mcp_ssh/server.py
```

## MCP Capabilities

| Type | Name | Description |
|------|------|-------------|
| **Tool** | `execute_command` | Execute commands in background on remote SSH hosts with process tracking |
| **Tool** | `get_command_output` | Retrieve output from background commands with chunking support |
| **Tool** | `get_command_status` | Check status of background commands without retrieving output |
| **Tool** | `kill_command` | Kill running background processes with graceful termination and cleanup |
| **Tool** | `transfer_file` | Upload/download files via SCP with progress tracking |
| **Tool** | `get_security_info` | Get current security configuration and validation rules |
| **Resource** | `ssh://hosts` | List all configured SSH hosts with detailed info |
| **Prompt** | `ssh_help` | Interactive guidance for SSH operations |

## Configuration

### Background Execution Settings

Set these environment variables to control background execution behavior:

```bash
# Maximum output size before chunking (default: 50000 bytes = 50KB)
export MCP_SSH_MAX_OUTPUT_SIZE=50000

# Time to wait for quick commands to complete (default: 5 seconds)
export MCP_SSH_QUICK_WAIT_TIME=5

# Default chunk size for get_command_output (default: 10000 bytes = 10KB)
export MCP_SSH_CHUNK_SIZE=10000
```

### Timeout Configuration

Set these environment variables to control timeout behavior and prevent hanging operations:

```bash
# SSH connection timeout in seconds (default: 30)
export MCP_SSH_CONNECT_TIMEOUT=30

# SSH command execution timeout in seconds (default: 60)
export MCP_SSH_COMMAND_TIMEOUT=60

# File transfer timeout in seconds (default: 300 = 5 minutes)
export MCP_SSH_TRANSFER_TIMEOUT=300

# Output reading timeout in seconds (default: 30)
export MCP_SSH_READ_TIMEOUT=30
```

### Connection Optimization

Set these environment variables to optimize performance:

```bash
# Enable connection reuse for better performance (default: true)
export MCP_SSH_CONNECTION_REUSE=true

# Maximum number of cached connections (default: 5)
export MCP_SSH_CONNECTION_POOL_SIZE=5
```

### Security Configuration

Set these environment variables to control command validation and security:

```bash
# Security mode: blacklist, whitelist, or disabled (default: blacklist)
export MCP_SSH_SECURITY_MODE=blacklist

# Semicolon-separated regex patterns for blocked commands
export MCP_SSH_COMMAND_BLACKLIST="rm\s+.*-r.*;sudo\s+.*;shutdown.*"

# Semicolon-separated regex patterns for allowed commands (whitelist mode)
export MCP_SSH_COMMAND_WHITELIST="ls\s+.*;cat\s+.*;ps\s+.*"

# Case-sensitive pattern matching (default: false)
export MCP_SSH_CASE_SENSITIVE=false
```

For detailed security configuration, see [SECURITY.md](SECURITY.md).

### Client Setup (Claude Desktop)
```json
{
  "mcpServers": {
    "mcp_ssh": {
      "command": "uv",
      "args": ["--directory", "/path/to/mcp_ssh", "run", "mcp_ssh"],
      "env": {
        "SSH_KEY_PHRASE": "your-passphrase",
        "SSH_KEY_FILE": "~/.ssh/id_rsa"
      }
    }
  }
}
```

### SSH Configuration
Uses your `~/.ssh/config` file:
```ssh-config
Host production
    HostName prod.example.com
    User deploy
    Port 22
    IdentityFile ~/.ssh/prod_key
```

## Development

### Prerequisites
- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- SSH client and config

### Setup
```bash
# Clone and setup
git clone https://github.com/sinjab/mcp_ssh.git
cd mcp_ssh
uv sync --extra dev
```

### Commands
```bash
# Quick development
./scripts/make test-quick    # Fast tests
./scripts/make test          # Full test suite (87% coverage)  
./scripts/make format        # Code formatting
./scripts/make lint          # Code linting
./scripts/make check         # All quality checks

# Python-based tools
uv run python scripts/dev.py --all
uv run python scripts/test.py pattern
```

### Testing
- **107 tests** across 5 modules with comprehensive coverage
- **Modular structure**: `tests/test_*.py` for each component
- **Shared fixtures**: Common utilities in `tests/conftest.py`
- **CI/CD ready**: GitHub Actions workflow

```bash
# Run specific test modules
uv run pytest tests/test_ssh_config.py -v
uv run pytest tests/test_mcp_server.py::TestMCPTools -v

# Coverage report
uv run pytest --cov=src/mcp_ssh --cov-report=html
open htmlcov/index.html
```

### Project Structure
```
mcp_ssh/
├── src/mcp_ssh/              # Source code
├── tests/                    # Test suite (90 tests, 87% coverage)
├── scripts/                  # Development tools  
├── .github/workflows/        # CI/CD pipeline
└── pyproject.toml            # Project configuration
```

### Quality Assurance Validation

The MCP SSH server has undergone comprehensive manual QA testing with **100% success rate** across all test scenarios:

**✅ Test Results Summary:**
- **9/9 test categories passed** (100% success rate)
- **47 individual MCP tool calls** executed successfully
- **No failures, crashes, or hangs** observed
- **Production-ready stability** demonstrated

**Key Validation Areas:**
- **Basic Connectivity**: All SSH commands execute successfully (~11-12s average)
- **Background Process Management**: Process tracking, concurrent execution, termination
- **Large Output Handling**: 43KB+ outputs processed without performance issues
- **File Transfer Operations**: Upload/download functionality working correctly
- **Error Handling**: Graceful handling of invalid inputs and edge cases
- **Concurrent Operations**: Multiple processes managed without interference
- **Performance Under Load**: No degradation during stress testing

**Production Readiness:**
- ✅ **Rock-solid reliability** with comprehensive error handling
- ✅ **Proper resource management** with cleanup and lifecycle handling
- ✅ **Strong performance characteristics** under load conditions
- ✅ **Production-grade features** including concurrent process management

## Usage Examples

### Background Execution Workflow

```python
# 1. Start command in background
result = await execute_command({
    "host": "server1", 
    "command": "find / -name '*.log'"
})

print(f"Process ID: {result.process_id}")
print(f"Status: {result.status}")
print(f"Output: {result.stdout}")

# 2. Check status later
status = await get_command_status({
    "process_id": result.process_id
})

# 3. Kill command if needed
if status.status == "running":
    kill_result = await kill_command({
        "process_id": result.process_id,
        "cleanup_files": True
    })
    print(f"Kill result: {kill_result.message}")

if status.status == "completed":
    # 4. Get output in chunks if needed
    if result.has_more_output:
        chunk1 = await get_command_output({
            "process_id": result.process_id,
            "start_byte": 0,
            "chunk_size": 10000
        })
        
        if chunk1.has_more_output:
            chunk2 = await get_command_output({
                "process_id": result.process_id,
                "start_byte": 10000,
                "chunk_size": 10000
            })
```

### Programmatic API
```python
from mcp_ssh.ssh import get_ssh_client_from_config, execute_ssh_command

# Connect and execute
client = get_ssh_client_from_config("production")
if client:
    stdout, stderr = execute_ssh_command(client, "uptime")
    print(stdout)
    client.close()
```

### MCP Tool Usage
```python
from mcp_ssh.server import CommandRequest, execute_command

# Execute via MCP (background execution)
request = CommandRequest(command="df -h", host="production")
result = await execute_command(request)
print(result)  # Structured output with process_id and status
```

## Troubleshooting

### Common Issues

**SSH Connection Failures**
```bash
# Test SSH connectivity directly
ssh -F ~/.ssh/config your-host

# Debug with environment variables
SSH_KEY_PHRASE=passphrase uv run mcp_ssh
```

**Permission Denied**
- Check SSH key permissions: `chmod 600 ~/.ssh/your_key`
- Verify SSH config syntax
- Ensure SSH agent is running: `ssh-add -l`

**Import Errors**
```bash
# Reinstall dependencies
uv sync --extra dev
```

### Logging
SSH operations are logged to `logs/ssh.log` with detailed information:
```bash
tail -f logs/ssh.log  # Monitor SSH activity
```

## Contributing

1. **Fork** the repository
2. **Setup**: `uv sync --extra dev`
3. **Develop**: Make changes with tests
4. **Quality**: `./scripts/make check`
5. **Submit**: Create pull request

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

## Performance & Security

- **Efficient**: Connection reuse, minimal memory footprint
- **Secure**: SSH best practices, key management, input validation
- **Robust**: Comprehensive error handling, graceful degradation
- **Scalable**: Thread-safe operations, async-ready architecture

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Links

- **Documentation**: [GitHub Repository](https://github.com/sinjab/mcp_ssh)
- **Issues**: [GitHub Issues](https://github.com/sinjab/mcp_ssh/issues)
- **MCP Specification**: [Model Context Protocol](https://modelcontextprotocol.io/)
- **FastMCP Framework**: [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
