"""
Security module for command validation and filtering
"""

import logging
import os
import re

logger = logging.getLogger(__name__)

# Environment variable names
COMMAND_BLACKLIST_ENV_VAR = "MCP_SSH_COMMAND_BLACKLIST"
COMMAND_WHITELIST_ENV_VAR = "MCP_SSH_COMMAND_WHITELIST"
SECURITY_MODE_ENV_VAR = "MCP_SSH_SECURITY_MODE"
CASE_SENSITIVE_ENV_VAR = "MCP_SSH_CASE_SENSITIVE"

# Default dangerous command patterns (used if no blacklist is provided)
DEFAULT_BLACKLIST_PATTERNS = [
    r"rm\s+.*-r.*",  # Recursive deletions
    r"rm\s+.*-f.*",  # Force deletions
    r"dd\s+.*",  # Disk operations
    r"mkfs[.\s].*",  # Format filesystem (mkfs.ext4, mkfs /dev/sda1)
    r"fdisk\s+.*",  # Disk partitioning
    r"parted\s+.*",  # Disk partitioning
    r"sudo\s+.*",  # Privilege escalation
    r"su\s+.*",  # Switch user
    r"passwd\s+.*",  # Password changes
    r"iptables\s+.*",  # Firewall rules
    r"ufw\s+.*",  # Ubuntu firewall
    r"systemctl\s+(stop|disable|mask).*",  # System service control
    r"service\s+(stop|disable).*",  # Service control
    r"killall\s+.*",  # Kill all processes
    r"pkill\s+.*",  # Kill processes by name
    r"shutdown\s+.*",  # System shutdown
    r"reboot\s+.*",  # System reboot
    r"halt\s+.*",  # System halt
    r"init\s+[06]",  # System shutdown/reboot
    r"mount\s+.*",  # Mount filesystems
    r"umount\s+.*",  # Unmount filesystems
    r"chmod\s+.*777.*",  # Dangerous permissions
    r"chown\s+.*root.*",  # Change ownership to root
    r".*>\s*/dev/sd[a-z].*",  # Write to disk devices
    r".*>\s*/dev/nvme.*",  # Write to NVMe devices
    r"crontab\s+-r",  # Remove crontab
    r"history\s+-c",  # Clear command history
    r".*\|\s*sh\s*$",  # Pipe to shell
    r".*\|\s*bash\s*$",  # Pipe to bash
    r"curl\s+.*\|\s*(sh|bash)",  # Download and execute
    r"wget\s+.*\|\s*(sh|bash)",  # Download and execute
]


class CommandValidator:
    """Validates commands against blacklist/whitelist patterns"""

    def __init__(self) -> None:
        # Read environment variables at initialization time
        self.security_mode = os.getenv(SECURITY_MODE_ENV_VAR, "blacklist").lower()
        self.case_sensitive = (
            os.getenv(CASE_SENSITIVE_ENV_VAR, "false").lower() == "true"
        )

        command_blacklist_env = os.getenv(COMMAND_BLACKLIST_ENV_VAR, "")
        command_whitelist_env = os.getenv(COMMAND_WHITELIST_ENV_VAR, "")

        self.blacklist_patterns = self._load_patterns(
            command_blacklist_env, DEFAULT_BLACKLIST_PATTERNS
        )
        self.whitelist_patterns = self._load_patterns(command_whitelist_env, [])

        logger.info(f"Security mode: {self.security_mode}")
        logger.info(f"Blacklist patterns: {len(self.blacklist_patterns)}")
        logger.info(f"Whitelist patterns: {len(self.whitelist_patterns)}")
        logger.info(f"Case sensitive: {self.case_sensitive}")

    def _load_patterns(self, env_var: str, defaults: list[str]) -> list[re.Pattern]:
        """Load regex patterns from environment variable or use defaults"""
        patterns = []

        if env_var:
            # Split by semicolon or newline
            pattern_strings = [
                p.strip() for p in re.split(r"[;\n]", env_var) if p.strip()
            ]
        else:
            pattern_strings = defaults

        for pattern_str in pattern_strings:
            try:
                flags = 0 if self.case_sensitive else re.IGNORECASE
                pattern = re.compile(pattern_str, flags)
                patterns.append(pattern)
                logger.debug(f"Loaded pattern: {pattern_str}")
            except re.error as e:
                logger.error(f"Invalid regex pattern '{pattern_str}': {e}")

        return patterns

    def validate_command(
        self, command: str, host: str = "", user: str = ""
    ) -> tuple[bool, str]:
        """
        Validate a command against security policies

        Args:
            command: The command to validate
            host: SSH host (for context-aware validation)
            user: SSH user (for context-aware validation)

        Returns:
            Tuple of (is_allowed, reason)
        """
        if self.security_mode == "disabled":
            return True, "Security validation disabled"

        command = command.strip()
        if not command:
            return False, "Empty command not allowed"

        # Log the validation attempt
        logger.info(f"Validating command on {host}: {command[:100]}...")

        if self.security_mode == "whitelist":
            return self._validate_whitelist(command, host, user)
        elif self.security_mode == "blacklist":
            return self._validate_blacklist(command, host, user)
        else:
            logger.error(f"Unknown security mode: {self.security_mode}")
            return False, f"Unknown security mode: {self.security_mode}"

    def _validate_whitelist(
        self, command: str, host: str, user: str
    ) -> tuple[bool, str]:
        """Validate command against whitelist (only allowed patterns pass)"""
        if not self.whitelist_patterns:
            return False, "No whitelist patterns configured - all commands blocked"

        for pattern in self.whitelist_patterns:
            if pattern.search(command):
                logger.info(f"Command allowed by whitelist pattern: {pattern.pattern}")
                return True, f"Command matches whitelist pattern: {pattern.pattern}"

        logger.warning(f"Command blocked - not in whitelist: {command}")
        return False, "Command not found in whitelist patterns"

    def _validate_blacklist(
        self, command: str, host: str, user: str
    ) -> tuple[bool, str]:
        """Validate command against blacklist (blocked patterns fail)"""
        for pattern in self.blacklist_patterns:
            if pattern.search(command):
                logger.warning(
                    f"Command blocked by blacklist pattern: {pattern.pattern}"
                )
                return False, f"Command blocked by security policy: {pattern.pattern}"

        logger.info("Command passed blacklist validation")
        return True, "Command passed security validation"

    def get_security_info(self) -> dict:
        """Get current security configuration info"""
        return {
            "security_mode": self.security_mode,
            "case_sensitive": self.case_sensitive,
            "blacklist_patterns_count": len(self.blacklist_patterns),
            "whitelist_patterns_count": len(self.whitelist_patterns),
            "blacklist_patterns": [p.pattern for p in self.blacklist_patterns],
            "whitelist_patterns": [p.pattern for p in self.whitelist_patterns],
        }


# Global validator instance
_validator = None


def get_validator() -> CommandValidator:
    """Get the global command validator instance"""
    global _validator
    if _validator is None:
        _validator = CommandValidator()
    return _validator


def validate_command(command: str, host: str = "", user: str = "") -> tuple[bool, str]:
    """
    Convenience function to validate a command

    Args:
        command: The command to validate
        host: SSH host (optional, for context)
        user: SSH user (optional, for context)

    Returns:
        Tuple of (is_allowed, reason)
    """
    return get_validator().validate_command(command, host, user)
