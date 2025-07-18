"""
User interface components for TermiGenius
"""

from typing import List, Dict, Any
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.prompt import Confirm
from rich.status import Status
from rich.syntax import Syntax
from rich.markdown import Markdown
from contextlib import contextmanager

class TermiGeniusUI:
    def __init__(self):
        self.console = Console()

    def info(self, message: str):
        self.console.print(f"ℹ️  {message}", style="blue")

    def success(self, message: str):
        self.console.print(f"✅ {message}", style="green")

    def error(self, message: str):
        self.console.print(f"❌ {message}", style="red")

    def warning(self, message: str):
        self.console.print(f"⚠️  {message}", style="yellow")

    def show_command(self, command: str, prompt: str):
        panel = Panel(
            Syntax(command, "bash", theme="monokai", line_numbers=False),
            title=f"💡 Generated Command for: '{prompt}'",
            border_style="blue"
        )
        self.console.print(panel)

    def show_explanation(self, explanation: str):
        panel = Panel(
            Markdown(explanation),
            title="📚 Command Explanation",
            border_style="green"
        )
        self.console.print(panel)

    def confirm(self, message: str) -> bool:
        return Confirm.ask(f"❓ {message}")

    @contextmanager
    def status(self, message: str):
        with self.console.status(message, spinner="dots"):
            yield

    def show_history(self, entries: List[Dict[str, Any]]):
        table = Table(title="📝 Command History")
        table.add_column("Date", style="cyan")
        table.add_column("Prompt", style="yellow")
        table.add_column("Command", style="green")
        table.add_column("Status", style="magenta")
        for entry in entries:
            status = "✅" if entry.get("success", False) else "❌"
            table.add_row(
                entry.get("timestamp", "Unknown"),
                entry.get("prompt", ""),
                entry.get("command", ""),
                status
            )
        self.console.print(table)

    def show_welcome(self):
        welcome_text = """
        🚀 Welcome to TermiGenius!
        
        Transform natural language into terminal commands with AI power.
        
        Examples:
        • "delete all PDF files from Downloads older than 7 days"
        • "find all Python files containing 'import requests'"
        • "compress the logs folder"
        """
        panel = Panel(
            Text(welcome_text, style="bold blue"),
            title="🤖 TermiGenius",
            border_style="blue"
        )
        self.console.print(panel) 