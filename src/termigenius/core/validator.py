"""
Command validation and safety checks for TermiGenius
"""

import re
from typing import Optional
from dataclasses import dataclass

@dataclass
class ValidationResult:
    """Result of command validation"""
    is_safe: bool
    reason: Optional[str] = None
    suggestion: Optional[str] = None
    risk_level: str = "low"  # low, medium, high, critical

class CommandValidator:
    """Validate commands for safety and correctness"""
    def __init__(self, config):
        self.config = config
        self.dangerous_patterns = [
            r'rm\s+-rf\s+/',
            r'sudo\s+rm\s+-rf',
            r'rm\s+-rf\s+\*',
            r'del\s+/[sq]',
            r'format\s+c:',
            r'dd\s+if=.*of=/dev/',
        ]
        self.warning_patterns = [
            r'sudo\s+',
            r'rm\s+.*\*',
            r'mv\s+.*\*',
            r'chmod\s+.*\*',
            r'chown\s+.*\*',
            r'find\s+.*-delete',
            r'xargs\s+rm',
        ]
        self.safe_commands = {
            'ls', 'cat', 'head', 'tail', 'grep', 'find', 'locate', 'which',
            'echo', 'printf', 'date', 'cal', 'uptime', 'whoami', 'pwd',
            'history', 'alias', 'type', 'file', 'stat', 'wc', 'sort',
            'uniq', 'cut', 'tr', 'sed', 'awk', 'less', 'more', 'man',
            'info', 'help', 'ps', 'top', 'htop', 'df', 'du', 'free',
            'git', 'python', 'python3', 'pip', 'npm', 'node'
        }

    def validate(self, command: str, strict_mode: bool = False) -> ValidationResult:
        if not command or not command.strip():
            return ValidationResult(is_safe=False, reason="Empty command", risk_level="low")
        command = command.strip()
        for pattern in self.dangerous_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                return ValidationResult(
                    is_safe=False,
                    reason=f"Dangerous pattern detected: {pattern}",
                    suggestion="Please review the command carefully or use a safer alternative",
                    risk_level="critical"
                )
        warning_found = False
        warning_pattern = None
        for pattern in self.warning_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                warning_found = True
                warning_pattern = pattern
                break
        base_command = command.split()[0] if command.split() else ""
        if self.config.safety_level == "high":
            if base_command not in self.safe_commands and not warning_found:
                return ValidationResult(
                    is_safe=False,
                    reason=f"Command '{base_command}' not in safe command list",
                    suggestion="Use --safe-mode=false to bypass this check",
                    risk_level="medium"
                )
        elif self.config.safety_level == "medium":
            if warning_found:
                return ValidationResult(
                    is_safe=True,
                    reason=f"Potentially risky command detected: {warning_pattern}",
                    suggestion="Please review the command carefully",
                    risk_level="medium"
                )
        return ValidationResult(is_safe=True, risk_level="low") 