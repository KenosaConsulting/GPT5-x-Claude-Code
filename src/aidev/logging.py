"""Logging configuration for aidev."""

from __future__ import annotations

import sys
from typing import Any, Dict, Optional

import structlog
from rich.console import Console
from rich.logging import RichHandler

from .config import LoggingConfig


def setup_logging(config: LoggingConfig) -> None:
    """Set up structured logging with rich output."""
    
    # Configure structlog
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
    ]
    
    if config.format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())
    
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(structlog.stdlib.CRITICAL + 1 - 10 * (
                {"DEBUG": 4, "INFO": 3, "WARNING": 2, "ERROR": 1, "CRITICAL": 0}.get(
                    config.level.upper(), 3
                )
            ), "INFO")
        ),
        logger_factory=structlog.WriteLoggerFactory(
            file=open(config.file, 'a', encoding='utf-8') if config.file else sys.stderr
        ),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a structured logger instance."""
    return structlog.get_logger(name)


class TokenTracker:
    """Track token usage and costs."""
    
    def __init__(self) -> None:
        self.openai_input_tokens = 0
        self.openai_output_tokens = 0
        self.anthropic_input_tokens = 0
        self.anthropic_output_tokens = 0
        
        # Approximate pricing (update as needed)
        self.openai_input_cost_per_1k = 0.03  # GPT-4 pricing
        self.openai_output_cost_per_1k = 0.06
        self.anthropic_input_cost_per_1k = 0.003  # Claude 3.5 Sonnet pricing
        self.anthropic_output_cost_per_1k = 0.015
    
    def add_openai_usage(self, input_tokens: int, output_tokens: int) -> None:
        """Add OpenAI token usage."""
        self.openai_input_tokens += input_tokens
        self.openai_output_tokens += output_tokens
    
    def add_anthropic_usage(self, input_tokens: int, output_tokens: int) -> None:
        """Add Anthropic token usage."""
        self.anthropic_input_tokens += input_tokens
        self.anthropic_output_tokens += output_tokens
    
    def get_estimated_cost(self) -> float:
        """Get estimated cost in USD."""
        openai_cost = (
            (self.openai_input_tokens / 1000) * self.openai_input_cost_per_1k +
            (self.openai_output_tokens / 1000) * self.openai_output_cost_per_1k
        )
        anthropic_cost = (
            (self.anthropic_input_tokens / 1000) * self.anthropic_input_cost_per_1k +
            (self.anthropic_output_tokens / 1000) * self.anthropic_output_cost_per_1k
        )
        return openai_cost + anthropic_cost
    
    def get_summary(self) -> Dict[str, Any]:
        """Get usage summary."""
        return {
            "openai": {
                "input_tokens": self.openai_input_tokens,
                "output_tokens": self.openai_output_tokens,
            },
            "anthropic": {
                "input_tokens": self.anthropic_input_tokens,
                "output_tokens": self.anthropic_output_tokens,
            },
            "total_tokens": (
                self.openai_input_tokens + self.openai_output_tokens +
                self.anthropic_input_tokens + self.anthropic_output_tokens
            ),
            "estimated_cost_usd": round(self.get_estimated_cost(), 4),
        }