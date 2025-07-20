"""
Utility helper functions for TermiGenius
"""

import os
import platform
import subprocess
from pathlib import Path
from typing import Dict, List

def get_system_info() -> Dict[str, str]:
    return {
        "os": platform.system(),
        "platform": platform.platform(),
        "shell": os.environ.get("SHELL", "unknown"),
        "pwd": os.getcwd(),
        "user": os.environ.get("USER", "unknown"),
        "home": str(Path.home()),
    }

def get_shell_type() -> str:
    shell = os.environ.get("SHELL", "")
    if "bash" in shell:
        return "bash"
    elif "zsh" in shell:
        return "zsh"
    elif "fish" in shell:
        return "fish"
    elif "powershell" in shell.lower() or "pwsh" in shell.lower():
        return "powershell"
    elif "cmd" in shell.lower():
        return "cmd"
    else:
        return "bash"

def is_command_available(command: str) -> bool:
    try:
        subprocess.run(
            ["which", command] if platform.system() != "Windows" else ["where", command],
            check=True,
            capture_output=True,
            text=True
        )
        return True
    except subprocess.CalledProcessError:
        return False

def get_common_directories() -> List[str]:
    home = Path.home()
    common_dirs = [
        str(home / "Downloads"),
        str(home / "Documents"),
        str(home / "Desktop"),
        str(home / "Pictures"),
        str(home / "Videos"),
        str(home / "Music"),
        "/tmp",
        "/var/log",
        "/usr/local/bin",
        "/etc",
    ]
    return [d for d in common_dirs if Path(d).exists()] 