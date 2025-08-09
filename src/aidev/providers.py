"""Enhanced AI provider interfaces with retry logic and monitoring."""

from __future__ import annotations

import json
import time
from typing import Any, Dict, Optional

import anthropic
import openai
from openai import OpenAI

from .config import AIDevConfig
from .logging import TokenTracker, get_logger

logger = get_logger(__name__)


class RetryableError(Exception):
    """Exception for retryable errors."""
    pass


def with_retry(max_retries: int = 3, backoff_factor: float = 2.0):
    """Decorator for retrying API calls with exponential backoff."""
    
    def decorator(func):
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except (
                    openai.RateLimitError,
                    openai.APITimeoutError,
                    openai.InternalServerError,
                    anthropic.RateLimitError,
                    anthropic.InternalServerError,
                ) as e:
                    last_exception = e
                    if attempt < max_retries:
                        sleep_time = backoff_factor ** attempt
                        logger.warning(f"API call failed (attempt {attempt + 1}), retrying in {sleep_time}s: {e}")
                        time.sleep(sleep_time)
                    else:
                        logger.error(f"API call failed after {max_retries + 1} attempts: {e}")
                        break
                except Exception as e:
                    logger.error(f"Non-retryable error in API call: {e}")
                    raise
            
            raise last_exception or Exception("Max retries exceeded")
        
        return wrapper
    return decorator


class OpenAIProvider:
    """Enhanced OpenAI provider with monitoring and retry logic."""
    
    def __init__(self, config: AIDevConfig, token_tracker: TokenTracker) -> None:
        self.config = config
        self.token_tracker = token_tracker
        
        if not config.openai_api_key:
            raise ValueError("OpenAI API key not provided")
        
        self.client = OpenAI(api_key=config.openai_api_key)
        self.model = config.models.openai_model
        self.temperature = config.models.openai_temperature
        
        logger.info(f"Initialized OpenAI provider with model: {self.model}")
    
    @with_retry(max_retries=3)
    def generate_spec(self, prompt: str, system_prompt: str) -> Dict[str, Any]:
        """Generate a specification from a prompt."""
        logger.info("Generating spec with OpenAI")
        
        start_time = time.time()
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=self.temperature,
            )
            
            duration = time.time() - start_time
            
            # Track token usage
            usage = response.usage
            if usage:
                self.token_tracker.add_openai_usage(
                    usage.prompt_tokens,
                    usage.completion_tokens
                )
            
            content = response.choices[0].message.content
            if not content:
                raise ValueError("Empty response from OpenAI")
            
            spec = json.loads(content)
            
            logger.info(f"Generated spec in {duration:.2f}s (tokens: {usage.total_tokens if usage else 'unknown'})")
            
            return spec
        
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse OpenAI JSON response: {e}")
            raise ValueError(f"Invalid JSON response: {e}")
        except Exception as e:
            logger.error(f"Error generating spec: {e}")
            raise
    
    @with_retry(max_retries=3)
    def review_code(self, diff_text: str, spec: Dict[str, Any], system_prompt: str) -> Dict[str, Any]:
        """Review code changes against a specification."""
        logger.info("Reviewing code with OpenAI")
        
        start_time = time.time()
        
        try:
            review_prompt = (
                f"SPECIFICATION:\n```json\n{json.dumps(spec, indent=2)}\n```\n\n"
                f"DIFF:\n```diff\n{diff_text}\n```"
            )
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": review_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=self.temperature,
            )
            
            duration = time.time() - start_time
            
            # Track token usage
            usage = response.usage
            if usage:
                self.token_tracker.add_openai_usage(
                    usage.prompt_tokens,
                    usage.completion_tokens
                )
            
            content = response.choices[0].message.content
            if not content:
                raise ValueError("Empty response from OpenAI")
            
            review = json.loads(content)
            
            logger.info(f"Completed review in {duration:.2f}s (tokens: {usage.total_tokens if usage else 'unknown'})")
            
            return review
        
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse OpenAI JSON response: {e}")
            raise ValueError(f"Invalid JSON response: {e}")
        except Exception as e:
            logger.error(f"Error reviewing code: {e}")
            raise


class AnthropicProvider:
    """Enhanced Anthropic provider with monitoring and tool execution."""
    
    def __init__(self, config: AIDevConfig, token_tracker: TokenTracker) -> None:
        self.config = config
        self.token_tracker = token_tracker
        
        if not config.anthropic_api_key:
            raise ValueError("Anthropic API key not provided")
        
        self.client = anthropic.Anthropic(api_key=config.anthropic_api_key)
        self.model = config.models.anthropic_model
        self.max_tokens = config.models.anthropic_max_tokens
        
        logger.info(f"Initialized Anthropic provider with model: {self.model}")
    
    def get_tool_schema(self) -> list:
        """Get the tool schema for Claude."""
        return [
            {
                "name": "read_file",
                "description": "Read a file within the repository",
                "input_schema": {
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"]
                }
            },
            {
                "name": "write_file",
                "description": "Write a file within the repository",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "content": {"type": "string"}
                    },
                    "required": ["path", "content"]
                }
            },
            {
                "name": "bash",
                "description": "Execute allowed shell commands with timeout",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "command": {"type": "string"},
                        "timeout": {"type": "number"}
                    },
                    "required": ["command"]
                }
            },
            {
                "name": "git_diff",
                "description": "Show git diff of working tree or staged changes",
                "input_schema": {
                    "type": "object",
                    "properties": {"staged": {"type": "boolean"}},
                    "required": []
                }
            },
            {
                "name": "git_apply",
                "description": "Apply a unified diff patch",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "patch": {"type": "string"},
                        "staged": {"type": "boolean"}
                    },
                    "required": ["patch"]
                }
            },
            {
                "name": "list_files",
                "description": "List files in the repository matching a pattern",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "pattern": {"type": "string"},
                        "max_files": {"type": "number"}
                    },
                    "required": []
                }
            }
        ]
    
    @with_retry(max_retries=3)
    def implement_spec(
        self,
        spec: Dict[str, Any],
        system_prompt: str,
        tool_executor,
        max_iterations: Optional[int] = None
    ) -> Dict[str, Any]:
        """Implement a specification using Claude with tools."""
        logger.info("Starting implementation with Claude")
        
        max_iterations = max_iterations or self.config.max_iterations
        
        # Prepare initial message
        spec_json = json.dumps(spec, indent=2)
        initial_prompt = (
            f"Please implement the following specification using the available tools:\n\n"
            f"```json\n{spec_json}\n```\n\n"
            f"Work systematically through the tasks, test your changes, and ensure all "
            f"done_criteria are met. When finished, provide a git diff and summary."
        )
        
        messages = [{"role": "user", "content": initial_prompt}]
        
        total_input_tokens = 0
        total_output_tokens = 0
        
        for iteration in range(max_iterations):
            logger.info(f"Implementation iteration {iteration + 1}/{max_iterations}")
            
            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    system=system_prompt,
                    messages=messages,
                    tools=self.get_tool_schema()
                )
                
                # Track token usage
                if hasattr(response, 'usage'):
                    total_input_tokens += response.usage.input_tokens
                    total_output_tokens += response.usage.output_tokens
                
                # Process response
                tool_results = []
                text_content = []
                
                for content_block in response.content:
                    if content_block.type == "text":
                        text_content.append(content_block.text)
                    elif content_block.type == "tool_use":
                        # Execute tool
                        tool_name = content_block.name
                        tool_input = content_block.input
                        
                        logger.info(f"Executing tool: {tool_name}")
                        
                        result = self._execute_tool(tool_executor, tool_name, tool_input)
                        
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": content_block.id,
                            "content": json.dumps(result)
                        })
                
                # Add assistant's response to conversation
                messages.append({
                    "role": "assistant",
                    "content": response.content
                })
                
                # If there were tool calls, add results and continue
                if tool_results:
                    messages.append({
                        "role": "user",
                        "content": tool_results
                    })
                    continue
                
                # No tool calls, implementation is complete
                final_text = "\n".join(text_content)
                
                # Track final token usage
                self.token_tracker.add_anthropic_usage(total_input_tokens, total_output_tokens)
                
                logger.info(
                    f"Implementation completed in {iteration + 1} iterations "
                    f"(tokens: {total_input_tokens + total_output_tokens})"
                )
                
                return {
                    "ok": True,
                    "iterations": iteration + 1,
                    "response": final_text,
                    "token_usage": {
                        "input_tokens": total_input_tokens,
                        "output_tokens": total_output_tokens
                    }
                }
            
            except Exception as e:
                logger.error(f"Error in implementation iteration {iteration + 1}: {e}")
                if iteration == max_iterations - 1:  # Last iteration
                    return {
                        "ok": False,
                        "error": str(e),
                        "iterations": iteration + 1
                    }
                continue
        
        return {
            "ok": False,
            "error": f"Maximum iterations ({max_iterations}) reached",
            "iterations": max_iterations
        }
    
    def _execute_tool(self, tool_executor, tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool and return the result."""
        try:
            if tool_name == "read_file":
                return tool_executor.read_file(tool_input["path"])
            elif tool_name == "write_file":
                return tool_executor.write_file(tool_input["path"], tool_input["content"])
            elif tool_name == "bash":
                return tool_executor.bash(tool_input["command"], tool_input.get("timeout"))
            elif tool_name == "git_diff":
                return tool_executor.git_diff(tool_input.get("staged", False))
            elif tool_name == "git_apply":
                return tool_executor.git_apply(tool_input["patch"], tool_input.get("staged", True))
            elif tool_name == "list_files":
                return tool_executor.list_files(
                    tool_input.get("pattern", "*"),
                    tool_input.get("max_files", 100)
                )
            else:
                return {"ok": False, "error": f"Unknown tool: {tool_name}"}
        
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            return {"ok": False, "error": str(e)}