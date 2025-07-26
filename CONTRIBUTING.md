# Contributing to MCP SSH

Thank you for contributing! This guide covers everything you need to get started.

## Quick Setup

```bash
# 1. Fork and clone
git clone https://github.com/yourusername/mcp_ssh.git
cd mcp_ssh

# 2. Install dependencies
uv sync --extra dev

# 3. Verify setup
./scripts/make check
```

## Development Workflow

### Making Changes

1. **Create branch**: `git checkout -b feature/your-feature`
2. **Make changes** with tests
3. **Run checks**: `./scripts/make check` 
4. **Commit**: `git commit -m 'feat: add amazing feature'`
5. **Push**: `git push origin feature/your-feature`
6. **Create PR**

### Development Commands

```bash
# Testing
./scripts/make test          # Full test suite (94% coverage)
./scripts/make test-quick    # Fast tests for iteration
uv run python scripts/test.py pattern  # Pattern-based testing

# Code Quality  
./scripts/make format        # Black + isort formatting
./scripts/make lint          # Ruff linting
./scripts/make type-check    # MyPy type checking
./scripts/make check         # All quality checks

# Server Development
uv run mcp dev src/mcp_ssh/server.py    # Development server
uv run mcp_ssh                           # Production server
```

## Code Standards

### Style Guidelines
- **Line Length**: 88 characters (Black default)
- **Type Hints**: Required for all functions
- **Docstrings**: Google-style for public APIs
- **Imports**: Sorted with isort, grouped by type

### Example Code
```python
from typing import Any

from pydantic import BaseModel, Field

from mcp_ssh.ssh import execute_ssh_command


class CommandRequest(BaseModel):
    """Request model for SSH command execution."""
    
    command: str = Field(description="Command to execute", min_length=1)
    host: str = Field(description="Target host", min_length=1)


def execute_remote_command(request: CommandRequest) -> dict[str, Any]:
    """Execute a command on a remote host via SSH.
    
    Args:
        request: Command execution request with validation
        
    Returns:
        Dictionary containing execution results
        
    Raises:
        ConnectionError: When SSH connection fails
    """
    # Implementation here
    pass
```

## Testing Guidelines

### Test Structure
- **Unit Tests**: Test individual functions (`tests/test_*.py`)
- **Integration Tests**: Test component interactions (`tests/test_integration.py`)
- **Fixtures**: Shared test utilities (`tests/conftest.py`)

### Writing Tests
```python
def test_execute_command_success(self, mock_ssh_client):
    """Test successful command execution."""
    # Arrange
    command = SSHCommand(command="ls -la", host="test-host")
    
    # Act  
    result = execute_command(command)
    
    # Assert
    assert "Successfully executed" in result
    mock_ssh_client.exec_command.assert_called_once()
```

### Test Guidelines
- **Descriptive names**: `test_function_scenario_expected_result`
- **Mock externals**: SSH connections, file system, network
- **Test failures**: Not just happy paths
- **Maintain coverage**: Currently 94%

### Running Tests
```bash
# All tests
uv run pytest --cov=src/mcp_ssh --cov-report=html

# Specific modules
uv run pytest tests/test_ssh_config.py -v
uv run pytest tests/test_mcp_server.py::TestMCPTools -v

# Pattern matching
uv run python scripts/test.py ssh_config

# With debugging
uv run pytest -v -s tests/test_mcp_server.py::test_specific
```

## Project Architecture

### Source Code (`src/mcp_ssh/`)
- **`server.py`**: MCP server, tools, resources, prompts
- **`ssh.py`**: SSH client, config parsing, command execution
- **`__init__.py`**: Package exports and public API

### Test Suite (`tests/`)
- **`test_ssh_config.py`**: SSH configuration parsing (8 tests ✅)
- **`test_ssh_client.py`**: SSH client functionality (10 tests)
- **`test_mcp_server.py`**: MCP server components (17 tests)
- **`test_integration.py`**: End-to-end workflows (15 tests)
- **`conftest.py`**: Shared fixtures and utilities

### Development Tools (`scripts/`)
- **`dev.py`**: Python development utility with all checks
- **`test.py`**: Quick test runner with pattern matching
- **`make`**: Bash command runner with colored output

## Pull Request Guidelines

### Before Submitting
- [ ] All tests pass (`./scripts/make test`)
- [ ] Code is formatted (`./scripts/make format`)
- [ ] Linting passes (`./scripts/make lint`)
- [ ] Type checking passes (`./scripts/make type-check`)
- [ ] Documentation updated for user-facing changes

### PR Template
```markdown
## Description
Brief description of changes and motivation.

## Type of Change
- [ ] Bug fix (non-breaking change)
- [ ] New feature (non-breaking change)  
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Tests pass locally
- [ ] Added tests for new functionality
- [ ] Maintained test coverage

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
```

### Commit Messages
Use conventional commit format:
```
feat: add SSH port forwarding support
fix: handle connection timeout gracefully  
docs: update installation instructions
test: add integration test for error handling
```

## Issue Guidelines

### Bug Reports
Include:
- **Environment**: Python version, OS, uv version
- **Steps**: Minimal reproduction example
- **Expected vs Actual**: What should vs does happen
- **Logs**: Error messages and stack traces
- **SSH Config**: Relevant configuration (sanitized)

### Feature Requests  
Include:
- **Use Case**: Problem you're solving
- **Proposed Solution**: How it might work
- **Alternatives**: Other approaches considered
- **Impact**: Who benefits from this feature

## Release Process

### Versioning
We follow [Semantic Versioning](https://semver.org/):
- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

### Release Checklist
1. Update version in `pyproject.toml`
2. Update `CHANGELOG.md`
3. Run full test suite (`./scripts/make check`)
4. Create release tag
5. Publish to PyPI

## Getting Help

- **Questions**: [GitHub Discussions](https://github.com/yourusername/mcp_ssh/discussions)
- **Bugs**: [GitHub Issues](https://github.com/yourusername/mcp_ssh/issues)
- **MCP Protocol**: [Model Context Protocol Docs](https://modelcontextprotocol.io/)
- **FastMCP**: [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)

## Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Focus on what's best for the project
- Help others learn and grow

Thank you for contributing to MCP SSH! 🚀
