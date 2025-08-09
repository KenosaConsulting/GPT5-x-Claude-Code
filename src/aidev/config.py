"""Configuration management for aidev."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field


class ToolConfig(BaseModel):
    """Configuration for tool restrictions and timeouts."""
    
    allowed_commands: List[str] = Field(default_factory=lambda: [
        "pytest", "python -m pytest", "pip install", "npm install", "npm test",
        "ruff", "black", "mypy", "cargo test", "cargo build", "go test", "go build"
    ])
    default_timeout: int = 90
    max_timeout: int = 300


class ModelConfig(BaseModel):
    """Configuration for AI models."""
    
    openai_model: str = "gpt-4o"  # Default to available model
    anthropic_model: str = "claude-3-5-sonnet-20241022"
    openai_temperature: float = 0.2
    anthropic_max_tokens: int = 2000


class LoggingConfig(BaseModel):
    """Configuration for logging."""
    
    level: str = "INFO"
    format: str = "json"
    file: Optional[str] = None


class AIDevConfig(BaseModel):
    """Main configuration for aidev."""
    
    tools: ToolConfig = Field(default_factory=ToolConfig)
    models: ModelConfig = Field(default_factory=ModelConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    
    # API Keys
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    
    # Repository settings
    target_repo: Optional[str] = None
    auto_detect_tools: bool = True
    
    # Safety settings
    require_confirmation: bool = True
    max_iterations: int = 50


def get_config_path() -> Path:
    """Get the configuration file path."""
    # Check for config in current directory first
    local_config = Path("aidev.yaml")
    if local_config.exists():
        return local_config
    
    # Check home directory
    home_config = Path.home() / ".config" / "aidev" / "config.yaml"
    return home_config


def load_config() -> AIDevConfig:
    """Load configuration from file and environment."""
    load_dotenv()
    
    config_data = {}
    config_path = get_config_path()
    
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f) or {}
    
    # Override with environment variables
    if api_key := os.getenv("OPENAI_API_KEY"):
        config_data["openai_api_key"] = api_key
    if api_key := os.getenv("ANTHROPIC_API_KEY"):
        config_data["anthropic_api_key"] = api_key
    if model := os.getenv("OPENAI_MODEL"):
        config_data.setdefault("models", {})["openai_model"] = model
    if model := os.getenv("ANTHROPIC_MODEL"):
        config_data.setdefault("models", {})["anthropic_model"] = model
    if repo := os.getenv("AIDEV_REPO"):
        config_data["target_repo"] = repo
    
    return AIDevConfig(**config_data)


def create_default_config(path: Optional[Path] = None) -> Path:
    """Create a default configuration file."""
    if path is None:
        path = get_config_path()
    
    path.parent.mkdir(parents=True, exist_ok=True)
    
    default_config = AIDevConfig()
    config_dict = default_config.model_dump(exclude_none=True)
    
    with open(path, 'w', encoding='utf-8') as f:
        yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)
    
    return path