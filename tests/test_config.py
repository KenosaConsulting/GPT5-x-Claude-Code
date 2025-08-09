"""Tests for configuration management."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from aidev.config import AIDevConfig, load_config, create_default_config


def test_default_config():
    """Test default configuration values."""
    config = AIDevConfig()
    
    assert config.models.openai_model == "gpt-4o"
    assert config.models.anthropic_model == "claude-3-5-sonnet-20241022"
    assert config.tools.default_timeout == 90
    assert config.require_confirmation is True
    assert config.auto_detect_tools is True


def test_load_config_from_file():
    """Test loading configuration from YAML file."""
    config_data = {
        "models": {
            "openai_model": "gpt-3.5-turbo",
            "anthropic_model": "claude-3-haiku-20240307"
        },
        "tools": {
            "default_timeout": 60
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config_data, f)
        config_path = Path(f.name)
    
    try:
        with patch('aidev.config.get_config_path', return_value=config_path):
            config = load_config()
        
        assert config.models.openai_model == "gpt-3.5-turbo"
        assert config.models.anthropic_model == "claude-3-haiku-20240307"
        assert config.tools.default_timeout == 60
    finally:
        config_path.unlink()


def test_load_config_with_env_override():
    """Test environment variable overrides."""
    with patch.dict(os.environ, {
        'OPENAI_API_KEY': 'test-openai-key',
        'ANTHROPIC_API_KEY': 'test-anthropic-key',
        'OPENAI_MODEL': 'gpt-4-turbo',
        'AIDEV_REPO': '/test/repo'
    }):
        with patch('aidev.config.get_config_path') as mock_path:
            mock_path.return_value = Path('nonexistent.yaml')
            config = load_config()
    
    assert config.openai_api_key == 'test-openai-key'
    assert config.anthropic_api_key == 'test-anthropic-key'
    assert config.models.openai_model == 'gpt-4-turbo'
    assert config.target_repo == '/test/repo'


def test_create_default_config():
    """Test creating default configuration file."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_path = Path(temp_dir) / 'test_config.yaml'
        
        created_path = create_default_config(config_path)
        
        assert created_path == config_path
        assert config_path.exists()
        
        # Verify content
        with open(config_path, 'r') as f:
            config_data = yaml.safe_load(f)
        
        assert 'models' in config_data
        assert 'tools' in config_data
        assert 'logging' in config_data


def test_config_validation():
    """Test configuration validation."""
    # Test invalid timeout
    with pytest.raises(Exception):
        AIDevConfig(tools={"default_timeout": -1})
    
    # Test empty model names
    config = AIDevConfig(models={"openai_model": "", "anthropic_model": ""})
    assert config.models.openai_model == ""  # Should allow empty for validation elsewhere