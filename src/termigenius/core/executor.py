"""
Command execution engine for TermiGenius
"""

import os
import subprocess
import time
import platform
from typing import Optional
from dataclasses import dataclass

@dataclass
class ExecutionResult:
    """Result of command execution"""
    success: bool
    output: str
    error: str
    return_code: int
    execution_time: float

class CommandExecutor:
    """Execute terminal commands safely"""
    def __init__(self, config):
        self.config = config
        self.timeout = 30  # Default timeout in seconds

    def execute(self, command: str, timeout: Optional[int] = None) -> ExecutionResult:
        start_time = time.time()
        timeout = timeout or self.timeout
        try:
            if platform.system() == "Windows":
                # Execute via PowerShell to support cmdlets like Get-ChildItem
                ps_command = [
                    "powershell.exe",
                    "-NoLogo",
                    "-NoProfile",
                    "-Command",
                    command,
                ]
                result = subprocess.run(ps_command, shell=False, capture_output=True, text=True, timeout=timeout, cwd=os.getcwd())
            else:
                result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=timeout, cwd=os.getcwd())
            execution_time = time.time() - start_time
            return ExecutionResult(
                success=result.returncode == 0,
                output=result.stdout,
                error=result.stderr,
                return_code=result.returncode,
                execution_time=execution_time
            )
        except subprocess.TimeoutExpired:
            execution_time = time.time() - start_time
            return ExecutionResult(
                success=False,
                output="",
                error=f"Command timed out after {timeout} seconds",
                return_code=-1,
                execution_time=execution_time
            )
        except Exception as e:
            execution_time = time.time() - start_time
            return ExecutionResult(
                success=False,
                output="",
                error=str(e),
                return_code=-1,
                execution_time=execution_time
            ) 