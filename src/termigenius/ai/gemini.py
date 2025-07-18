"""
Advanced Google Gemini AI provider for TermiGenius
Enhanced with robust error handling, caching, security, and performance optimizations
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
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Tuple
from functools import lru_cache, wraps
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from contextlib import contextmanager
import shutil

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
    from importlib.metadata import distributions
    pkg_resources = True
except ImportError:
    try:
        import pkg_resources
    except ImportError:
        pkg_resources = None

from ..utils.helpers import get_system_info, get_shell_type
from .prompts import MASTER_COMMAND_GENERATION_PROMPT as COMMAND_GENERATION_PROMPT, EXPLANATION_PROMPT

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class SystemContext:
    """Enhanced system context with validation"""
    os: str
    version: str
    architecture: str
    shell: str
    pwd: str
    user: str
    desktop: str
    home: str
    temp: str
    drives: List[str]
    path_separator: str
    locale: str
    python_version: str
    network_status: str
    available_commands: List[str]
    hardware: Dict[str, Any]
    network: Dict[str, Any]
    top_packages: List[str]
    environment_vars: Dict[str, str]
    disk_usage: Dict[str, float]
    
    def __post_init__(self):
        """Validate system context after initialization"""
        if not self.os or not self.shell:
            raise ValueError("OS and shell information are required")
        if not os.path.exists(self.pwd):
            logger.warning(f"Current directory {self.pwd} doesn't exist")

@dataclass
class CacheEntry:
    """Cache entry with expiration and metadata"""
    value: Any
    timestamp: datetime
    ttl: int
    metadata: Dict[str, Any]
    
    def is_expired(self) -> bool:
        return datetime.now() - self.timestamp > timedelta(seconds=self.ttl)

class CommandValidator:
    """Advanced command validation and sanitization"""
    
    DANGEROUS_COMMANDS = {
        'rm -rf /', 'del /f /s /q C:\\*', 'format C:', 'dd if=/dev/zero',
        'mkfs', 'fdisk', 'chmod 777', 'chown -R', 'sudo su',
        'eval', 'exec', 'system', 'os.system', 'subprocess.call'
    }
    
    SUSPICIOUS_PATTERNS = [
        r'rm\s+-rf\s+/',
        r'del\s+/[fqs]\s+.*\*',
        r'format\s+[A-Z]:',
        r'dd\s+if=/dev/zero',
        r'>\s*/dev/sd[a-z]',
        r'curl\s+.*\|\s*bash',
        r'wget\s+.*\|\s*sh',
        r'python\s+-c\s+.*exec',
        r'eval\s*\(',
        r'__import__\s*\(',
    ]
    
    @classmethod
    def validate_command(cls, command: str) -> Tuple[bool, str]:
        """Validate command for safety"""
        if not command or not command.strip():
            return False, "Empty command"
        
        # Check for dangerous commands
        for dangerous in cls.DANGEROUS_COMMANDS:
            if dangerous.lower() in command.lower():
                return False, f"Dangerous command detected: {dangerous}"
        
        # Check for suspicious patterns
        for pattern in cls.SUSPICIOUS_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                return False, f"Suspicious pattern detected: {pattern}"
        
        # Check command length
        if len(command) > 10000:
            return False, "Command too long"
        
        return True, "Valid command"
    
    @classmethod
    def sanitize_command(cls, command: str) -> str:
        """Sanitize command by removing dangerous elements"""
        # Remove potentially dangerous redirections
        command = re.sub(r'>\s*/dev/sd[a-z]', '', command)
        command = re.sub(r'2>&1.*', '', command)
        
        # Remove eval/exec patterns
        command = re.sub(r'eval\s*\([^)]*\)', '', command)
        command = re.sub(r'exec\s*\([^)]*\)', '', command)
        
        return command.strip()

class AdvancedCache:
    """Thread-safe LRU cache with TTL and persistence"""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache: Dict[str, CacheEntry] = {}
        self.lock = threading.RLock()
        self.access_times: Dict[str, datetime] = {}
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        with self.lock:
            if key in self.cache:
                entry = self.cache[key]
                if not entry.is_expired():
                    self.access_times[key] = datetime.now()
                    return entry.value
                else:
                    del self.cache[key]
                    if key in self.access_times:
                        del self.access_times[key]
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache"""
        with self.lock:
            if len(self.cache) >= self.max_size:
                self._evict_lru()
            
            ttl = ttl or self.default_ttl
            self.cache[key] = CacheEntry(
                value=value,
                timestamp=datetime.now(),
                ttl=ttl,
                metadata={}
            )
            self.access_times[key] = datetime.now()
    
    def _evict_lru(self) -> None:
        """Evict least recently used item"""
        if not self.access_times:
            return
        
        lru_key = min(self.access_times, key=self.access_times.get)
        del self.cache[lru_key]
        del self.access_times[lru_key]
    
    def clear(self) -> None:
        """Clear all cache entries"""
        with self.lock:
            self.cache.clear()
            self.access_times.clear()

class RetryManager:
    """Advanced retry mechanism with exponential backoff"""
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
    
    def retry_with_backoff(self, func, *args, **kwargs):
        """Execute function with exponential backoff retry"""
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < self.max_retries:
                    delay = self.base_delay * (2 ** attempt)
                    logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
                    time.sleep(delay)
                else:
                    logger.error(f"All {self.max_retries + 1} attempts failed")
        
        raise last_exception

class GeminiProvider:
    """Advanced Google Gemini AI provider with robust error handling and optimization"""
    
    def __init__(self, api_key: str, model_name: str = 'gemini-2.5-flash', 
                 enable_caching: bool = True, cache_ttl: int = 3600,
                 max_retries: int = 3, timeout: int = 30):
        """
        Initialize the advanced Gemini provider
        
        Args:
            api_key: Gemini API key
            model_name: Model to use
            enable_caching: Whether to enable response caching
            cache_ttl: Cache time-to-live in seconds
            max_retries: Maximum number of retry attempts
            timeout: Request timeout in seconds
        """
        self._validate_initialization(api_key, model_name)
        
        # Core configuration
        self.api_key = api_key
        self.model_name = model_name
        self.timeout = timeout
        
        # Initialize components
        self.cache = AdvancedCache(default_ttl=cache_ttl) if enable_caching else None
        self.retry_manager = RetryManager(max_retries=max_retries)
        self.validator = CommandValidator()
        
        # Configure Gemini
        self._configure_gemini()
        
        # System context
        self.system_context = self._build_system_context()
        
        # Performance metrics
        self.metrics = {
            'requests_count': 0,
            'cache_hits': 0,
            'errors': 0,
            'avg_response_time': 0.0
        }
        
        logger.info(f"GeminiProvider initialized with model: {model_name}")
    
    def _validate_initialization(self, api_key: str, model_name: str) -> None:
        """Validate initialization parameters"""
        if not api_key or not isinstance(api_key, str):
            raise ValueError("Valid Gemini API key is required")
        
        if not model_name or not isinstance(model_name, str):
            raise ValueError("Valid model name is required")
        
        if not api_key.startswith('AIza'):
            logger.warning("API key format appears invalid")
    
    def _configure_gemini(self) -> None:
        """Configure Gemini with advanced settings"""
        try:
            genai.configure(api_key=self.api_key)
            
            # Advanced generation configuration
            self.generation_config = GenerationConfig(
                temperature=0.1,
                top_p=0.8,
                top_k=40,
                max_output_tokens=8192,
                response_mime_type="text/plain",
            )
            
            # Safety settings
            self.safety_settings = {
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            }
            
            self.model = genai.GenerativeModel(
                model_name=self.model_name,
                generation_config=self.generation_config,
                safety_settings=self.safety_settings
            )
            
        except Exception as e:
            logger.error(f"Failed to configure Gemini: {e}")
            raise
    
    @lru_cache(maxsize=1)
    def _build_system_context(self) -> SystemContext:
        """Build comprehensive system context with caching"""
        try:
            system_info = get_system_info()
            shell_type = get_shell_type()
            
            # Basic system info
            context_data = {
                'os': system_info.get('os', platform.system()),
                'version': platform.version(),
                'architecture': platform.machine(),
                'shell': shell_type,
                'pwd': system_info.get('pwd', os.getcwd()),
                'user': system_info.get('user', os.getenv('USER', 'unknown')),
                'desktop': str(Path.home() / "Desktop"),
                'home': str(Path.home()),
                'temp': str(Path(tempfile.gettempdir())),
                'drives': self._get_available_drives(),
                'path_separator': os.sep,
                'locale': locale.getdefaultlocale()[0] if locale.getdefaultlocale() else "unknown",
                'python_version': platform.python_version(),
                'network_status': self._get_network_status(),
                'available_commands': self._get_available_commands(),
                'hardware': self._get_hardware_info(),
                'network': self._get_network_info(),
                'top_packages': self._get_installed_packages(),
                'environment_vars': self._get_safe_env_vars(),
                'disk_usage': self._get_disk_usage(),
            }
            
            return SystemContext(**context_data)
            
        except Exception as e:
            logger.error(f"Failed to build system context: {e}")
            raise
    
    def _get_available_drives(self) -> List[str]:
        """Get available drives (Windows) or mount points (Unix)"""
        try:
            if os.name == "nt":
                return [f"{d}:\\" for d in "ABCDEFGHIJKLMNOPQRSTUVWXYZ" 
                       if os.path.exists(f"{d}:\\")]
            else:
                # Unix-like systems
                with open('/proc/mounts', 'r') as f:
                    mounts = [line.split()[1] for line in f.readlines()]
                return [m for m in mounts if os.path.exists(m)][:10]
        except Exception:
            return []
    
    def _get_hardware_info(self) -> Dict[str, Any]:
        """Get detailed hardware information"""
        try:
            if not psutil:
                return {}
            
            return {
                "cpu_count": psutil.cpu_count(logical=True),
                "cpu_freq": psutil.cpu_freq()._asdict() if psutil.cpu_freq() else {},
                "memory_gb": round(psutil.virtual_memory().total / (1024**3), 2),
                "swap_gb": round(psutil.swap_memory().total / (1024**3), 2),
                "platform": platform.platform(),
                "machine": platform.machine(),
                "processor": platform.processor(),
                "boot_time": datetime.fromtimestamp(psutil.boot_time()).isoformat(),
            }
        except Exception as e:
            logger.warning(f"Failed to get hardware info: {e}")
            return {}
    
    def _get_network_info(self) -> Dict[str, Any]:
        """Get network interface information"""
        try:
            if not psutil:
                return {}
            
            interfaces = {}
            for name, addrs in psutil.net_if_addrs().items():
                interfaces[name] = [addr.address for addr in addrs]
            
            return {
                "interfaces": interfaces,
                "stats": {name: stats._asdict() for name, stats in psutil.net_if_stats().items()},
                "connections": len(psutil.net_connections()),
            }
        except Exception as e:
            logger.warning(f"Failed to get network info: {e}")
            return {}
    
    def _get_network_status(self) -> str:
        """Get simple network status"""
        try:
            if not psutil:
                return "Unknown"
            
            stats = psutil.net_if_stats()
            up_interfaces = [iface for iface, s in stats.items() if s.isup]
            return f"Active: {', '.join(up_interfaces)}" if up_interfaces else "No active interfaces"
        except Exception:
            return "Unknown"
    
    def _get_available_commands(self) -> List[str]:
        """Get available system commands"""
        try:
            paths = os.environ.get("PATH", "").split(os.pathsep)
            commands = set()
            
            for path in paths:
                if os.path.isdir(path):
                    try:
                        for file in os.listdir(path):
                            if os.path.isfile(os.path.join(path, file)):
                                commands.add(file.lower())
                    except (PermissionError, OSError):
                        continue
            
            # Add common commands that might not be in PATH
            common_commands = ['cd', 'ls', 'dir', 'mkdir', 'rmdir', 'copy', 'move', 'del', 'rm']
            commands.update(common_commands)
            
            return sorted(list(commands))[:50]  # Limit for prompt efficiency
        except Exception:
            return []
    
    def _get_installed_packages(self) -> List[str]:
        """Get installed Python packages"""
        try:
            packages = []
            
            # Try modern importlib.metadata first
            try:
                from importlib.metadata import distributions
                for dist in distributions():
                    packages.append(f"{dist.metadata['Name']}=={dist.version}")
                    if len(packages) >= 30:  # Limit for prompt efficiency
                        break
                return packages
            except ImportError:
                pass
            
            # Fallback to pkg_resources
            if pkg_resources:
                for pkg in pkg_resources.working_set:
                    packages.append(f"{pkg.project_name}=={pkg.version}")
                    if len(packages) >= 30:  # Limit for prompt efficiency
                        break
                return packages
            
            return []
        except Exception:
            return []
    
    def _get_safe_env_vars(self) -> Dict[str, str]:
        """Get safe environment variables (excluding sensitive ones)"""
        sensitive_vars = {
            'API_KEY', 'SECRET', 'PASSWORD', 'TOKEN', 'PRIVATE_KEY',
            'AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY'
        }
        
        safe_vars = {}
        for key, value in os.environ.items():
            if not any(sensitive in key.upper() for sensitive in sensitive_vars):
                # Ensure the value is safe for string formatting
                safe_value = str(value).replace('{', '{{').replace('}', '}}')
                safe_vars[key] = safe_value
        
        return safe_vars
    
    def _get_disk_usage(self) -> Dict[str, float]:
        """Get disk usage information"""
        try:
            if not psutil:
                return {}
            
            disk_usage = {}
            for partition in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    disk_usage[partition.mountpoint] = {
                        'total_gb': round(usage.total / (1024**3), 2),
                        'used_gb': round(usage.used / (1024**3), 2),
                        'free_gb': round(usage.free / (1024**3), 2),
                        'percent': round((usage.used / usage.total) * 100, 2)
                    }
                except (PermissionError, OSError):
                    continue
            
            return disk_usage
        except Exception:
            return {}
    
    def _create_cache_key(self, prompt: str, context_hash: str) -> str:
        """Create a cache key for the request"""
        # Escape any problematic characters in the prompt
        safe_prompt = prompt.replace('\\', '\\\\').replace('\n', '\\n').replace('\r', '\\r')
        content = f"{safe_prompt}:{context_hash}"
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def _fix_path_separators(self, command: str) -> str:
        if os.name == "nt":
            # Windows: replace forward slashes with backslashes, but avoid URLs
            command = re.sub(r"(?<!http:)(?<!https:)(?<!ftp:)(?<!ftps:)/", r"\\", command)
            desktop = self.system_context.desktop.replace("\\", "\\\\")
            # Use a function to safely replace Desktop/ or Desktop\ with the absolute path
            def desktop_replacer(match):
                start = match.start()
                # Only replace if at the start or after a space (not after a drive letter)
                if start == 0 or (command[start-1] == ' '):
                    return f"{desktop}\\\\"
                return match.group(0)
            command = re.sub(r"Desktop[\\/]+", desktop_replacer, command)
            command = re.sub(r"mkdir\s+-p\s+", "mkdir ", command)
            command = command.replace("'", '"')
        else:
            command = command.replace("\\\\", "/")
        return command
    
    def _extract_command_from_response(self, response: str) -> str:
        """Extract command from AI response with improved parsing"""
        if not response:
            return ""
        
        # Remove markdown code blocks
        code_block_pattern = r'```[\w]*\n?(.*?)\n?```'
        matches = re.findall(code_block_pattern, response, re.DOTALL)
        
        if matches:
            # Use the first code block
            command = matches[0].strip()
        else:
            # No code blocks found, use the entire response
            lines = response.strip().split('\n')
            command_lines = []
            
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#') and not line.startswith('//'):
                    command_lines.append(line)
            
            command = ' && '.join(command_lines) if len(command_lines) > 1 else (command_lines[0] if command_lines else response.strip())
        
        # Clean up the command
        command = command.strip()
        command = re.sub(r'\s+', ' ', command)  # Normalize whitespace
        
        return command
    
    @contextmanager
    def _measure_time(self):
        """Context manager to measure execution time"""
        start_time = time.time()
        yield
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Update metrics
        self.metrics['requests_count'] += 1
        old_avg = self.metrics['avg_response_time']
        count = self.metrics['requests_count']
        self.metrics['avg_response_time'] = (old_avg * (count - 1) + execution_time) / count
    
    def generate_command(self, prompt: str, advanced_context: bool = False, 
                        validate_command: bool = True) -> str:
        """
        Generate command with advanced features
        
        Args:
            prompt: User's natural language prompt
            advanced_context: Whether to include advanced system context
            validate_command: Whether to validate the generated command
            
        Returns:
            Generated command string
        """
        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty")
        
        # Create context hash for caching
        context_data = asdict(self.system_context)
        if not advanced_context:
            # Remove advanced context for basic requests
            context_data.pop('hardware', None)
            context_data.pop('network', None)
            context_data.pop('top_packages', None)
        
        context_hash = hashlib.md5(json.dumps(context_data, sort_keys=True).encode()).hexdigest()
        cache_key = self._create_cache_key(prompt, context_hash)
        
        # Check cache first
        if self.cache:
            cached_result = self.cache.get(cache_key)
            if cached_result:
                self.metrics['cache_hits'] += 1
                logger.debug("Cache hit for command generation")
                return cached_result
        
        try:
            with self._measure_time():
                # Prepare context
                context = context_data.copy()
                context['prompt'] = prompt
                
                # Generate full prompt - ensure safe string formatting
                try:
                    full_prompt = COMMAND_GENERATION_PROMPT.format(**context)
                except (KeyError, ValueError) as e:
                    logger.error(f"Prompt formatting error: {e}")
                    # Fallback: create a simpler prompt
                    full_prompt = f"Generate a command for: {prompt}\nOS: {context.get('os', 'unknown')}\nShell: {context.get('shell', 'unknown')}"
                
                # Generate command with retry logic
                response = self.retry_manager.retry_with_backoff(
                    self._generate_with_timeout, full_prompt
                )
                
                if not response or not response.text:
                    raise Exception("Empty response from Gemini")
                
                # Extract and process command
                command = self._extract_command_from_response(response.text)
                command = self._fix_path_separators(command)
                
                # Validate command if requested
                if validate_command:
                    is_valid, validation_message = self.validator.validate_command(command)
                    if not is_valid:
                        logger.warning(f"Command validation failed: {validation_message}")
                        command = self.validator.sanitize_command(command)
                
                # Cache the result
                if self.cache:
                    self.cache.set(cache_key, command)
                
                logger.info(f"Generated command: {command[:100]}...")
                return command
                
        except Exception as e:
            self.metrics['errors'] += 1
            logger.error(f"Command generation failed: {e}")
            raise
    
    def _generate_with_timeout(self, prompt: str) -> Any:
        """Generate response with timeout"""
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(self.model.generate_content, prompt)
            try:
                return future.result(timeout=self.timeout)
            except TimeoutError:
                logger.error(f"Generation timed out after {self.timeout} seconds")
                raise
    
    def explain_command(self, command: str) -> str:
        """
        Explain a command with enhanced context
        
        Args:
            command: Command to explain
            
        Returns:
            Detailed explanation of the command
        """
        if not command or not command.strip():
            raise ValueError("Command cannot be empty")
        
        # Create cache key
        cache_key = self._create_cache_key(f"explain:{command}", "explanation")
        
        # Check cache
        if self.cache:
            cached_result = self.cache.get(cache_key)
            if cached_result:
                self.metrics['cache_hits'] += 1
                return cached_result
        
        try:
            with self._measure_time():
                context = {
                    'command': command,
                    'os': self.system_context.os,
                    'shell': self.system_context.shell,
                    'available_commands': ', '.join(self.system_context.available_commands[:20])
                }
                
                try:
                    full_prompt = EXPLANATION_PROMPT.format(**context)
                except (KeyError, ValueError) as e:
                    logger.error(f"Explanation prompt formatting error: {e}")
                    # Fallback: create a simpler prompt
                    full_prompt = f"Explain this command: {command}\nOS: {context.get('os', 'unknown')}\nShell: {context.get('shell', 'unknown')}"
                
                response = self.retry_manager.retry_with_backoff(
                    self._generate_with_timeout, full_prompt
                )
                
                if not response or not response.text:
                    raise Exception("Empty response from Gemini")
                
                explanation = response.text.strip()
                
                # Cache the result
                if self.cache:
                    self.cache.set(cache_key, explanation)
                
                return explanation
                
        except Exception as e:
            self.metrics['errors'] += 1
            logger.error(f"Command explanation failed: {e}")
            raise
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        return self.metrics.copy()
    
    def clear_cache(self) -> None:
        """Clear the cache"""
        if self.cache:
            self.cache.clear()
            logger.info("Cache cleared")
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check"""
        try:
            # Test basic functionality
            test_response = self.model.generate_content("Say 'OK' if you can hear me")
            
            return {
                'status': 'healthy',
                'model': self.model_name,
                'cache_enabled': self.cache is not None,
                'metrics': self.get_metrics(),
                'test_response': test_response.text if test_response else None
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'metrics': self.get_metrics()
            }
    
    def __del__(self):
        """Cleanup resources"""
        if hasattr(self, 'cache'):
            self.cache.clear()
        logger.info("GeminiProvider cleaned up") 