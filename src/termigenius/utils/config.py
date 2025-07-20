"""
Configuration management for TermiGenius
"""

import os
import yaml
from pathlib import Path
from typing import Optional
from pydantic import BaseModel

class Config(BaseModel):
    ai_provider: str = "gemini"
    gemini_api_key: Optional[str] = None
    safety_level: str = "high"
    auto_confirm: bool = False
    history_enabled: bool = True
    max_history: int = 100
    preferred_shell: str = "bash"
    use_colors: bool = True
    verbose: bool = False

    @classmethod
    def get_config_dir(cls) -> Path:
        home = Path.home()
        config_dir = home / ".termigenius"
        config_dir.mkdir(exist_ok=True)
        return config_dir

    @classmethod
    def get_config_file(cls) -> Path:
        return cls.get_config_dir() / "config.yaml"

    @classmethod
    def load(cls) -> "Config":
        config_file = cls.get_config_file()
        config_data = {}
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    config_data = yaml.safe_load(f) or {}
            except Exception as e:
                print(f"Warning: Could not load config file: {e}")
        if os.getenv("GEMINI_API_KEY"):
            config_data["gemini_api_key"] = os.getenv("GEMINI_API_KEY")
        if os.getenv("TERMIGENIUS_SAFETY_LEVEL"):
            config_data["safety_level"] = os.getenv("TERMIGENIUS_SAFETY_LEVEL")
        env_file = Path(".env")
        if env_file.exists():
            try:
                from dotenv import load_dotenv
                load_dotenv(env_file)
                if os.getenv("GEMINI_API_KEY"):
                    config_data["gemini_api_key"] = os.getenv("GEMINI_API_KEY")
            except ImportError:
                pass
        return cls(**config_data)

    def save(self):
        config_file = self.get_config_file()
        config_data = self.model_dump()
        try:
            with open(config_file, 'w') as f:
                yaml.dump(config_data, f, default_flow_style=False)
        except Exception as e:
            raise Exception(f"Could not save config file: {e}")

    @property
    def history_file(self) -> Path:
        return self.get_config_dir() / "history.json" 