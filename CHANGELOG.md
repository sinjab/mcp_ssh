# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Comprehensive test infrastructure with modular organization
- 49 tests across 4 modules with 94% coverage
- Development tools and scripts (scripts/dev.py, scripts/make, scripts/test.py)
- CI/CD pipeline with GitHub Actions
- Type checking with MyPy in strict mode
- Code formatting with Black and isort
- Modern linting with Ruff
- Organized project structure with tests/ directory
- Shared test fixtures in conftest.py
- Professional documentation (README.md, CONTRIBUTING.md)

### Changed
- Reorganized project structure for better maintainability
- Enhanced error handling and validation
- Improved documentation with comprehensive usage examples
- Modernized Python type hints (dict instead of Dict, etc.)
- Consolidated documentation from 7 to 3 essential files
- Updated development workflow for organized testing

### Fixed
- Pydantic model validation for SSH commands
- Import organization and unused import removal
- Type annotations for better IDE support
- Test organization and module structure

## [0.1.0] - 2024-07-26

### Added
- Initial MCP SSH server implementation
- SSH client functionality with paramiko
- MCP tools for command execution
- MCP resources for host listing
- MCP prompts for user guidance
- SSH configuration parsing from ~/.ssh/config
- Support for encrypted SSH private keys
- Environment variable configuration
- Comprehensive logging system
- FastMCP-based server architecture

### Features
- **Tools**:
  - `execute_command`: Execute commands on remote SSH hosts
- **Resources**:
  - `ssh://hosts`: List configured SSH hosts
- **Prompts**:
  - `ssh_help`: Interactive help for SSH operations

### Infrastructure
- Python 3.11+ support
- Paramiko for SSH operations
- FastMCP for MCP protocol implementation
- Pydantic for data validation
- Structured logging to files

[Unreleased]: https://github.com/yourusername/mcp_ssh/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/yourusername/mcp_ssh/releases/tag/v0.1.0
