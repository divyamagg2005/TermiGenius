"""
Core functionality for TermiGenius
"""

from .executor import CommandExecutor, ExecutionResult
from .validator import CommandValidator, ValidationResult
from .history import HistoryManager, HistoryEntry

__all__ = [
    "CommandExecutor", "ExecutionResult",
    "CommandValidator", "ValidationResult", 
    "HistoryManager", "HistoryEntry"
] 