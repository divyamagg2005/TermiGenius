"""
Advanced Google Gemini AI provider for TermiGenius - Windows PowerShell Exclusive
Enhanced with comprehensive Windows system context and native PowerShell command enforcement
"""

import os
import sys
import json
import time
import hashlib
import threading
import subprocess
import logging
import platform
import tempfile
import locale
import re
import winreg
from pathlib import Path, WindowsPath
from typing import Dict, List, Optional, Any, Union, Tuple
from functools import lru_cache, wraps
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from contextlib import contextmanager

# Ensure we're running on Windows
if os.name != 'nt' or platform.system() != 'Windows':
    raise RuntimeError("This provider is designed exclusively for Windows systems")

try:
    import google.generativeai as genai
    from google.generativeai.types import GenerationConfig, HarmCategory, HarmBlockThreshold
    from google.api_core.exceptions import GoogleAPIError, RetryError
except ImportError:
    raise ImportError("google-generativeai is required. Install with: pip install google-generativeai")

try:
    import psutil
except ImportError:
    psutil = None

try:
    import wmi
except ImportError:
    wmi = None

try:
    from win32api import GetComputerName, GetUserName
    from win32security import GetUserName as GetUserNameEx
    import win32net
    import win32netcon
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False

from .prompts import (
    MASTER_POWERSHELL_COMMAND_PROMPT as COMMAND_GENERATION_PROMPT,
    POWERSHELL_EXPLANATION_PROMPT as EXPLANATION_PROMPT
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class WindowsSystemContext:
    """Comprehensive Windows-specific system context"""
    # Basic system info
    os: str
    version: str
    edition: str
    architecture: str
    build_number: str
    
    # PowerShell specific
    powershell_version: str
    powershell_edition: str
    powershell_profile: str
    execution_policy: str
    available_modules: List[str]
    powershell_providers: List[str]
    
    # User context
    user_account: str
    user_domain: str
    user_sid: str
    computer_name: str
    user_privileges: List[str]
    
    # Directory paths (all absolute)
    current_location: str
    user_home: str
    desktop_path: str
    documents_path: str
    downloads_path: str
    appdata_path: str
    localappdata_path: str
    programfiles_path: str
    programfiles86_path: str
    windows_directory: str
    system32_directory: str
    temp_directory: str
    
    # Storage and network
    available_drives: List[str]
    network_drives: List[str]
    network_interfaces: List[Dict[str, str]]
    
    # System capabilities
    installed_applications: List[str]
    windows_features: List[str]
    registry_access: Dict[str, bool]
    
    # Environment
    culture_info: str
    time_zone: str
    environment_variables: Dict[str, str]
    
    # Hardware summary
    hardware_summary: Dict[str, Any]
    
    def __post_init__(self):
        """Validate Windows system context"""
        if self.os != "Windows":
            raise ValueError("This provider only supports Windows systems")
        if not self.powershell_version:
            raise ValueError("PowerShell information is required")

class WindowsPowerShellValidator:
    """Advanced PowerShell command validation for Windows"""
    
    # Legacy CMD commands that should NEVER be used
    FORBIDDEN_CMD_COMMANDS = {
        'dir', 'copy', 'move', 'del', 'md', 'mkdir', 'rd', 'rmdir', 'cd', 'chdir',
        'type', 'find', 'findstr', 'cls', 'echo', 'set', 'path', 'attrib',
        'xcopy', 'robocopy', 'net', 'sc', 'reg', 'wmic', 'systeminfo'
    }
    
    # PowerShell aliases that should be replaced with full cmdlets
    POWERSHELL_ALIASES = {
        'gci': 'Get-ChildItem',
        'dir': 'Get-ChildItem',
        'ls': 'Get-ChildItem',
        'copy': 'Copy-Item',
        'cp': 'Copy-Item',
        'move': 'Move-Item',
        'mv': 'Move-Item',
        'del': 'Remove-Item',
        'rm': 'Remove-Item',
        'md': 'New-Item -ItemType Directory',
        'mkdir': 'New-Item -ItemType Directory',
        'cd': 'Set-Location',
        'pwd': 'Get-Location',
        'cat': 'Get-Content',
        'type': 'Get-Content',
        'echo': 'Write-Output',
        'cls': 'Clear-Host',
        'ps': 'Get-Process',
        'kill': 'Stop-Process',
        'start': 'Start-Process',
        'svc': 'Get-Service',
        'gsv': 'Get-Service',
        'sasv': 'Start-Service',
        'spsv': 'Stop-Service',
        'gi': 'Get-Item',
        'si': 'Set-Item',
        'ni': 'New-Item',
        'ri': 'Remove-Item'
    }
    
    # Valid PowerShell cmdlets (Verb-Noun pattern)
    VALID_POWERSHELL_VERBS = {
        'Get', 'Set', 'New', 'Remove', 'Add', 'Clear', 'Copy', 'Move', 'Rename',
        'Start', 'Stop', 'Restart', 'Suspend', 'Resume', 'Wait', 'Join', 'Split',
        'Test', 'Invoke', 'Import', 'Export', 'Convert', 'ConvertTo', 'ConvertFrom',
        'Select', 'Where', 'ForEach', 'Sort', 'Group', 'Measure', 'Compare',
        'Write', 'Read', 'Out', 'Format', 'Tee', 'Trace', 'Debug', 'Verbose'
    }
    
    @classmethod
    def validate_powershell_command(cls, command: str) -> Tuple[bool, str, str]:
        """
        Validate PowerShell command for Windows compliance
        Returns: (is_valid, validation_message, corrected_command)
        """
        if not command or not command.strip():
            return False, "Empty command", ""
        
        original_command = command.strip()
        corrected_command = original_command
        issues = []
        
        # Check for forbidden CMD commands
        words = command.lower().split()
        for word in words:
            if word in cls.FORBIDDEN_CMD_COMMANDS:
                issues.append(f"Legacy CMD command '{word}' detected - use PowerShell equivalent")
                return False, "; ".join(issues), corrected_command
        
        # Check for PowerShell aliases and suggest full cmdlets
        for alias, full_cmdlet in cls.POWERSHELL_ALIASES.items():
            if re.search(r'\b' + re.escape(alias) + r'\b', command, re.IGNORECASE):
                corrected_command = re.sub(
                    r'\b' + re.escape(alias) + r'\b', 
                    full_cmdlet, 
                    corrected_command, 
                    flags=re.IGNORECASE
                )
                issues.append(f"Replaced alias '{alias}' with full cmdlet '{full_cmdlet}'")
        
        # Check for relative paths
        relative_patterns = [r'\.\\', r'\.\.\\', r'~\\', r'\$env:', r'%\w+%']
        for pattern in relative_patterns:
            if re.search(pattern, command):
                issues.append(f"Relative path pattern '{pattern}' detected - use absolute paths")
        
        # Validate PowerShell cmdlet structure
        cmdlet_pattern = r'\b([A-Z][a-z]+-[A-Z][a-zA-Z]+)\b'
        cmdlets = re.findall(cmdlet_pattern, command)
        for cmdlet in cmdlets:
            verb = cmdlet.split('-')[0]
            if verb not in cls.VALID_POWERSHELL_VERBS:
                issues.append(f"Unrecognized PowerShell verb '{verb}' in cmdlet '{cmdlet}'")
        
        # Check for proper parameter syntax
        if '-' in command and not re.search(r'-[A-Z][a-zA-Z]+', command):
            issues.append("PowerShell parameters should use full names (e.g., -Path, not -p)")
        
        is_valid = len([i for i in issues if "detected" in i or "Unrecognized" in i]) == 0
        
        return is_valid, "; ".join(issues) if issues else "Valid PowerShell command", corrected_command

class WindowsSystemAnalyzer:
    """Comprehensive Windows system analysis for PowerShell context"""

    def __init__(self):
        if not WIN32_AVAILABLE:
            logger.warning("Win32 extensions not available - some features will be limited")

    # ------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------
    def analyze(self) -> "WindowsSystemContext":
        """Gather a comprehensive snapshot of the local Windows environment.
        This MUST include all attributes required by the WindowsSystemContext
        dataclass so that __post_init__ validation succeeds and the prompt
        builder has every placeholder it needs.  Where rich data is expensive
        or unavailable (e.g. WMI when the import failed) we gracefully fall
        back to safe defaults so that TermiGenius never crashes merely
        because optional Windows APIs are missing.
        """
        # -----------------------------------------------------------------
        # Basic OS information
        # -----------------------------------------------------------------
        version_info = self.get_windows_version()

        # -----------------------------------------------------------------
        # PowerShell information
        # -----------------------------------------------------------------
        ps_info = self.get_powershell_info()
        execution_policy = self.get_powershell_execution_policy()
        available_modules = self.get_powershell_modules()
        powershell_providers = self.get_powershell_providers()

        # -----------------------------------------------------------------
        # User context
        # -----------------------------------------------------------------
        user_ctx = self.get_user_context()

        # -----------------------------------------------------------------
        # Directory paths
        # -----------------------------------------------------------------
        current_location = os.getcwd()
        user_home = str(Path.home())
        desktop_path = str(Path(user_home) / "Desktop")
        documents_path = str(Path(user_home) / "Documents")
        downloads_path = str(Path(user_home) / "Downloads")
        appdata_path = os.getenv("APPDATA", str(Path(user_home) / "AppData" / "Roaming"))
        localappdata_path = os.getenv("LOCALAPPDATA", str(Path(user_home) / "AppData" / "Local"))
        programfiles_path = os.getenv("ProgramFiles", "C:\\Program Files")
        programfiles86_path = os.getenv("ProgramFiles(x86)", "C:\\Program Files (x86)")
        windows_directory = os.getenv("WINDIR", "C:\\Windows")
        system32_directory = str(Path(windows_directory) / "System32")
        temp_directory = tempfile.gettempdir()

        # -----------------------------------------------------------------
        # Storage and network
        # -----------------------------------------------------------------
        available_drives: List[str] = []
        network_drives: List[str] = []
        network_interfaces: List[Dict[str, str]] = []
        try:
            import string
            drives_bitmask = winreg.QueryValueEx(winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Network'), 'Map Network Drive')[0] if WIN32_AVAILABLE else 0
        except Exception:
            drives_bitmask = 0
        try:
            # Quick way to list logical drives on Windows
            import ctypes
            bitmask = ctypes.windll.kernel32.GetLogicalDrives()
            for i, letter in enumerate(string.ascii_uppercase):
                if bitmask & (1 << i):
                    drive = f"{letter}:\\"
                    available_drives.append(drive)
        except Exception:
            pass

        try:
            if psutil:
                for part in psutil.disk_partitions(all=False):
                    if part.fstype == "":  # Likely network drive on Windows
                        network_drives.append(part.device)
                for iface, addrs in psutil.net_if_addrs().items():
                    ip_addrs = [a.address for a in addrs if a.family == getattr(psutil, 'AF_INET', 2)]
                    if ip_addrs:
                        network_interfaces.append({"interface": iface, "addresses": ip_addrs})
        except Exception:
            pass

        # -----------------------------------------------------------------
        # System capabilities & registry access
        # -----------------------------------------------------------------
        installed_applications: List[str] = []
        windows_features: List[str] = []
        registry_access: Dict[str, bool] = {"HKLM": False, "HKCU": False}
        try:
            if WIN32_AVAILABLE:
                for hive_name, hive in [("HKLM", winreg.HKEY_LOCAL_MACHINE), ("HKCU", winreg.HKEY_CURRENT_USER)]:
                    try:
                        winreg.OpenKey(hive, "SOFTWARE")
                        registry_access[hive_name] = True
                    except PermissionError:
                        registry_access[hive_name] = False
        except Exception:
            pass

        # -----------------------------------------------------------------
        # Environment / culture
        # -----------------------------------------------------------------
        culture_info = locale.getdefaultlocale()[0] if locale.getdefaultlocale() else "en-US"
        time_zone = time.tzname[0] if time.tzname else "UTC"
        environment_variables = dict(os.environ)

        # -----------------------------------------------------------------
        # Hardware summary (very high-level)
        # -----------------------------------------------------------------
        hardware_summary: Dict[str, Any] = {}
        try:
            if psutil:
                hardware_summary["cpu_count"] = psutil.cpu_count(logical=True)
                hardware_summary["memory_total"] = psutil.virtual_memory().total
            if wmi:
                c = wmi.WMI()
                for sys in c.Win32_ComputerSystem():
                    hardware_summary["manufacturer"] = sys.Manufacturer
                    hardware_summary["model"] = sys.Model
        except Exception:
            pass

        # -----------------------------------------------------------------
        # Build and return the dataclass instance
        # -----------------------------------------------------------------
        return WindowsSystemContext(
            # Basic system info
            os=version_info.get("os", "Windows"),
            version=version_info.get("version", platform.version()),
            edition=version_info.get("edition", ""),
            architecture=version_info.get("architecture", platform.machine()),
            build_number=version_info.get("build_number", ""),
            # PowerShell specific
            powershell_version=str(ps_info.get("version", "")),
            powershell_edition=str(ps_info.get("edition", "")),
            powershell_profile=str(Path(user_home) / "Documents" / "WindowsPowerShell" / "Microsoft.PowerShell_profile.ps1"),
            execution_policy=execution_policy,
            available_modules=available_modules,
            powershell_providers=powershell_providers,
            # User context
            user_account=user_ctx.get("user_account", "Unknown"),
            user_domain=user_ctx.get("user_domain", "Unknown"),
            user_sid=user_ctx.get("user_sid", "Unknown"),
            computer_name=user_ctx.get("computer_name", platform.node()),
            user_privileges=user_ctx.get("user_privileges", []),
            # Directories
            current_location=current_location,
            user_home=user_home,
            desktop_path=desktop_path,
            documents_path=documents_path,
            downloads_path=downloads_path,
            appdata_path=appdata_path,
            localappdata_path=localappdata_path,
            programfiles_path=programfiles_path,
            programfiles86_path=programfiles86_path,
            windows_directory=windows_directory,
            system32_directory=system32_directory,
            temp_directory=temp_directory,
            # Storage / network
            available_drives=available_drives,
            network_drives=network_drives,
            network_interfaces=network_interfaces,
            # Capabilities
            installed_applications=installed_applications,
            windows_features=windows_features,
            registry_access=registry_access,
            # Environment
            culture_info=culture_info,
            time_zone=time_zone,
            environment_variables=environment_variables,
            # Hardware summary
            hardware_summary=hardware_summary,
        )
    
    @staticmethod
    def get_windows_version() -> Dict[str, str]:
        """Get detailed Windows version information"""
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                               r"SOFTWARE\Microsoft\Windows NT\CurrentVersion")
            
            version_info = {
                'os': 'Windows',
                'version': winreg.QueryValueEx(key, "CurrentVersion")[0],
                'build_number': winreg.QueryValueEx(key, "CurrentBuild")[0],
                'edition': winreg.QueryValueEx(key, "EditionID")[0],
                'architecture': platform.machine()
            }
            
            try:
                version_info['display_version'] = winreg.QueryValueEx(key, "DisplayVersion")[0]
            except FileNotFoundError:
                version_info['display_version'] = version_info['version']
            
            winreg.CloseKey(key)
            return version_info
            
        except Exception as e:
            logger.error(f"Failed to get Windows version: {e}")
            return {
                'os': 'Windows',
                'version': platform.version(),
                'build_number': 'Unknown',
                'edition': 'Unknown',
                'architecture': platform.machine(),
                'display_version': 'Unknown'
            }
    
    @staticmethod
    def get_powershell_info() -> Dict[str, Any]:
        """Get comprehensive PowerShell environment information"""
        try:
            # Get PowerShell version
            ps_command = 'powershell.exe -Command "& {$PSVersionTable | ConvertTo-Json}"'
            result = subprocess.run(ps_command, shell=True, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                ps_info = json.loads(result.stdout)
                
                return {
                    'version': ps_info.get('PSVersion', 'Unknown'),
                    'edition': ps_info.get('PSEdition', 'Desktop'),
                    'build_version': ps_info.get('BuildVersion', 'Unknown'),
                    'clr_version': ps_info.get('CLRVersion', 'Unknown'),
                    'ws_man_stack': ps_info.get('WSManStackVersion', 'Unknown'),
                    'serialization_version': ps_info.get('SerializationVersion', 'Unknown')
                }
            
        except Exception as e:
            logger.error(f"Failed to get PowerShell info: {e}")
        
        return {
            'version': '5.1',  # Default assumption
            'edition': 'Desktop',
            'build_version': 'Unknown',
            'clr_version': 'Unknown',
            'ws_man_stack': 'Unknown',
            'serialization_version': 'Unknown'
        }
    
    @staticmethod
    def get_powershell_execution_policy() -> str:
        """Get current PowerShell execution policy"""
        try:
            ps_command = 'powershell.exe -Command "Get-ExecutionPolicy"'
            result = subprocess.run(ps_command, shell=True, capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                return result.stdout.strip()
                
        except Exception as e:
            logger.error(f"Failed to get execution policy: {e}")
        
        return "Restricted"  # Conservative default
    
    @staticmethod
    def get_powershell_modules() -> List[str]:
        """Get available PowerShell modules"""
        try:
            ps_command = 'powershell.exe -Command "& {Get-Module -ListAvailable | Select-Object -ExpandProperty Name | Sort-Object -Unique | ConvertTo-Json}"'
            result = subprocess.run(ps_command, shell=True, capture_output=True, text=True, timeout=15)
            
            if result.returncode == 0:
                modules = json.loads(result.stdout)
                return modules if isinstance(modules, list) else [modules] if modules else []
                
        except Exception as e:
            logger.error(f"Failed to get PowerShell modules: {e}")
        
        return []
    
    @staticmethod
    def get_powershell_providers() -> List[str]:
        """Get available PowerShell providers"""
        try:
            ps_command = 'powershell.exe -Command "& {Get-PSProvider | Select-Object -ExpandProperty Name | ConvertTo-Json}"'
            result = subprocess.run(ps_command, shell=True, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                providers = json.loads(result.stdout)
                return providers if isinstance(providers, list) else [providers] if providers else []
                
        except Exception as e:
            logger.error(f"Failed to get PowerShell providers: {e}")
        
        return []
    
    @staticmethod
    def get_user_context() -> Dict[str, str]:
        """Get detailed user context information"""
        context = {
            'user_account': os.getenv('USERNAME', 'Unknown'),
            'user_domain': os.getenv('USERDOMAIN', 'Unknown'),
            'computer_name': os.getenv('COMPUTERNAME', 'Unknown'),
            'user_sid': 'Unknown'
        }
        
        if WIN32_AVAILABLE:
            try:
                context['computer_name'] = GetComputerName()
                context['user_account'] = GetUserName()
                
                # Get user SID
                ps_command = 'powershell.exe -Command "New-Object System.Security.Principal.SecurityIdentifier (New-Object System.Security.Principal.NTAccount $env:USERNAME, $env:USERDOMAIN).Translate([System.Security.Principal.SecurityIdentifier]).Value"'
                result = subprocess.run(ps_command, shell=True, capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0:
                    context['user_sid'] = result.stdout.strip()
                else:
                    logger.warning(f"Could not get user SID: {result.stderr}")
                    context['user_sid'] = 'Unknown'
            except Exception as e:
                logger.error(f"Failed to get user context: {e}")
                context['user_sid'] = 'Unknown'
        
        return context

class GeminiProvider:
    """Advanced Google Gemini AI provider for TermiGenius - Windows PowerShell Exclusive
    Enhanced with comprehensive Windows system context and native PowerShell command enforcement
    """
    
    def __init__(self, api_key: str, model_name: str = 'gemini-2.5-flash'):
        self.api_key = api_key
        self.model_name = model_name
        if not WIN32_AVAILABLE:
            logger.warning("Win32 extensions not available - some features will be limited")
    
    def build_prompt(self, system_context: WindowsSystemContext, user_prompt: str) -> str:
        context_dict = asdict(system_context)
        context_dict['user_prompt'] = user_prompt
        # Fill in any missing fields required by the prompt with safe defaults
        required_fields = [
            'os', 'version', 'edition', 'architecture', 'build_number',
            'powershell_version', 'powershell_edition', 'powershell_profile', 'execution_policy',
            'available_modules', 'powershell_providers',
            'user_account', 'user_domain', 'user_sid', 'computer_name', 'user_privileges',
            'current_location', 'user_home', 'desktop_path', 'documents_path', 'downloads_path',
            'appdata_path', 'localappdata_path', 'programfiles_path', 'programfiles86_path',
            'windows_directory', 'system32_directory', 'temp_directory',
            'available_drives', 'network_drives', 'network_interfaces',
            'installed_applications', 'windows_features', 'registry_access',
            'culture_info', 'time_zone', 'environment_variables', 'hardware_summary',
            'user_prompt'
        ]
        for field in required_fields:
            if field not in context_dict:
                context_dict[field] = ''
        return COMMAND_GENERATION_PROMPT.format(**context_dict)

    def _extract_command_from_response(self, response: str) -> str:
        # Remove markdown code blocks and comments, return the first line as the command
        if not response:
            return ""
        code_block_pattern = r'```[\w]*\n?(.*?)\n?```'
        matches = re.findall(code_block_pattern, response, re.DOTALL)
        if matches:
            command = matches[0].strip()
        else:
            lines = response.strip().split('\n')
            command_lines = [line.strip() for line in lines if line.strip() and not line.strip().startswith('#')]
            command = command_lines[0] if command_lines else response.strip()
        return command

    def explain_command(self, command: str) -> str:
        """Return a rich, multi-section explanation of the given PowerShell command."""
        try:
            # Build context dict with all available fields from system analyzer
            try:
                ctx = WindowsSystemAnalyzer().analyze()
                ctx_dict = asdict(ctx)
            except Exception:
                ctx_dict = {}
            ctx_dict.update({
                "command": command,
                "os_version": ctx_dict.get("version", platform.version()),
            })
            # Ensure required keys exist with safe defaults
            required_keys = [
                "powershell_version",
                "powershell_edition",
                "execution_policy",
                "user_account",
                "user_privileges",
                "available_modules",
                "available_drives",
                "network_drives",
            ]
            for k in required_keys:
                ctx_dict.setdefault(k, "")

            genai.configure(api_key=self.api_key)
            model = genai.GenerativeModel(self.model_name)
            prompt = EXPLANATION_PROMPT.format(**ctx_dict)
            response = model.generate_content(prompt)
            if response and hasattr(response, "text") and response.text:
                return response.text
            return "No explanation could be generated."
        except Exception as e:
            logger.error(f"Failed to generate explanation: {e}")
            return f"Error generating explanation: {e}"

    def generate_command(self, user_prompt: str, system_context: WindowsSystemContext) -> str:
        prompt = self.build_prompt(system_context, user_prompt)
        try:
            genai.configure(api_key=self.api_key)
            model = genai.GenerativeModel(self.model_name)
            response = model.generate_content(prompt)
            if not response or not hasattr(response, 'text') or not response.text:
                raise Exception("Empty response from Gemini")
            command = self._extract_command_from_response(response.text)
            is_valid, reason, corrected = WindowsPowerShellValidator.validate_powershell_command(command)
            if not is_valid:
                logger.warning(f"Command validation: {reason}")
                command = corrected
            return command
        except Exception as e:
            logger.error(f"Failed to generate command: {e}")
            raise

    def ask(self, prompt: str) -> str:
        """Send a raw prompt to Gemini and return the response text (no context, no formatting)."""
        import google.generativeai as genai
        genai.configure(api_key=self.api_key)
        model = genai.GenerativeModel(self.model_name)
        response = model.generate_content(prompt)
        if response and hasattr(response, "text") and response.text:
            return response.text
        return "[No response from Gemini]"