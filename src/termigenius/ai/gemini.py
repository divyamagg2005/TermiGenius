"""
Google Gemini AI provider for TermiGenius
"""

import os
import google.generativeai as genai
from pathlib import Path
import locale
import platform
import psutil
from ..utils.helpers import get_system_info, get_shell_type
from .prompts import COMMAND_GENERATION_PROMPT, EXPLANATION_PROMPT

class GeminiProvider:
    """Google Gemini AI provider"""
    
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("Gemini API key is required")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        self.system_info = get_system_info()
        self.shell_type = get_shell_type()
        self.desktop_path = str(Path.home() / "Desktop")
        self.home_path = str(Path.home())
        self.python_version = platform.python_version()
        self.locale = locale.getdefaultlocale()[0] if locale.getdefaultlocale() else "unknown"
        if os.name == "nt":
            self.available_drives = [f"{d}:\\" for d in "ABCDEFGHIJKLMNOPQRSTUVWXYZ" if os.path.exists(f"{d}:\\")]
        else:
            self.available_drives = []

    def _get_advanced_context(self):
        # Only include non-sensitive, relevant advanced info
        try:
            hardware = {
                "cpu_count": psutil.cpu_count(logical=True),
                "memory_gb": round(psutil.virtual_memory().total / (1024**3), 2),
                "platform": platform.platform(),
                "machine": platform.machine(),
                "processor": platform.processor(),
            }
            network = {
                "interfaces": list(psutil.net_if_addrs().keys()),
                "connections": len(psutil.net_connections()) if hasattr(psutil, 'net_connections') else 0,
            }
            try:
                import pkg_resources
                packages = [f"{pkg.project_name}=={pkg.version}" for pkg in pkg_resources.working_set][:20]
            except ImportError:
                packages = []
            return {
                "hardware": hardware,
                "network": network,
                "top_packages": packages,
            }
        except Exception as e:
            return {"advanced_context_error": str(e)}

    def generate_command(self, prompt: str, advanced_context: bool = False) -> str:
        context = {
            "os": self.system_info["os"],
            "shell": self.shell_type,
            "pwd": self.system_info["pwd"],
            "user": self.system_info["user"],
            "desktop": self.desktop_path,
            "home": self.home_path,
            "python_version": self.python_version,
            "locale": self.locale,
            "drives": ", ".join(self.available_drives),
            "prompt": prompt
        }
        if advanced_context:
            adv = self._get_advanced_context()
            context["hardware"] = adv.get("hardware", {})
            context["network"] = adv.get("network", {})
            context["top_packages"] = adv.get("top_packages", [])
        full_prompt = COMMAND_GENERATION_PROMPT.format(**context)
        response = self.model.generate_content(full_prompt)
        if not response.text:
            raise Exception("Empty response from Gemini")
        return self._extract_command(response.text)
    
    def explain_command(self, command: str) -> str:
        context = {
            "command": command,
            "os": self.system_info["os"],
            "shell": self.shell_type
        }
        full_prompt = EXPLANATION_PROMPT.format(**context)
        response = self.model.generate_content(full_prompt)
        if not response.text:
            raise Exception("Empty response from Gemini")
        return response.text.strip()
    
    def _extract_command(self, response: str) -> str:
        lines = response.strip().split('\n')
        command_lines = []
        in_code_block = False
        for line in lines:
            if line.strip().startswith('```'):
                in_code_block = not in_code_block
                continue
            if in_code_block or not line.strip().startswith('#'):
                if line.strip():
                    command_lines.append(line.strip())
        if not command_lines:
            cleaned = response.strip()
            if cleaned.startswith('```'):
                cleaned = cleaned.split('\n', 1)[1]
            if cleaned.endswith('```'):
                cleaned = cleaned.rsplit('\n', 1)[0]
            return cleaned.strip()
        return ' && '.join(command_lines) if len(command_lines) > 1 else command_lines[0] 