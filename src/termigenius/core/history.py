"""
Command history management for TermiGenius
"""

import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path

@dataclass
class HistoryEntry:
    """Single history entry"""
    timestamp: str
    prompt: str
    command: str
    success: bool
    execution_time: float = 0.0
    output_length: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HistoryEntry":
        return cls(**data)

class HistoryManager:
    """Manage command history"""
    def __init__(self, config):
        self.config = config
        self.history_file = config.history_file
        self._ensure_history_file()

    def _ensure_history_file(self):
        if not self.history_file.exists():
            self.history_file.parent.mkdir(parents=True, exist_ok=True)
            self._save_history([])

    def _load_history(self) -> List[HistoryEntry]:
        try:
            with open(self.history_file, 'r') as f:
                data = json.load(f)
                return [HistoryEntry.from_dict(entry) for entry in data]
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def _save_history(self, entries: List[HistoryEntry]):
        try:
            with open(self.history_file, 'w') as f:
                json.dump([entry.to_dict() for entry in entries], f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save history: {e}")

    def add_entry(self, prompt: str, command: str, success: bool, execution_time: float = 0.0, output_length: int = 0):
        if not self.config.history_enabled:
            return
        entry = HistoryEntry(
            timestamp=datetime.now().isoformat(),
            prompt=prompt,
            command=command,
            success=success,
            execution_time=execution_time,
            output_length=output_length
        )
        entries = self._load_history()
        entries.append(entry)
        if len(entries) > self.config.max_history:
            entries = entries[-self.config.max_history:]
        self._save_history(entries)

    def get_recent_entries(self, limit: int = 10) -> List[HistoryEntry]:
        entries = self._load_history()
        return entries[-limit:] if entries else []

    def search_history(self, query: str, limit: int = 10) -> List[HistoryEntry]:
        entries = self._load_history()
        matching_entries = []
        for entry in entries:
            if (query.lower() in entry.prompt.lower() or query.lower() in entry.command.lower()):
                matching_entries.append(entry)
        return matching_entries[-limit:] if matching_entries else []

    def clear_history(self):
        self._save_history([])

    def get_stats(self) -> Dict[str, Any]:
        entries = self._load_history()
        if not entries:
            return {"total_commands": 0}
        total_commands = len(entries)
        successful_commands = sum(1 for entry in entries if entry.success)
        return {
            "total_commands": total_commands,
            "successful_commands": successful_commands,
            "success_rate": successful_commands / total_commands if total_commands > 0 else 0,
            "average_execution_time": sum(entry.execution_time for entry in entries) / total_commands,
            "most_recent": entries[-1].timestamp if entries else None,
        } 