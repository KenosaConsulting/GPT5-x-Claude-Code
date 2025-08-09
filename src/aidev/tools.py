"""Enhanced tool execution with safety and monitoring."""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import AIDevConfig
from .logging import get_logger

logger = get_logger(__name__)


class ToolExecutor:
    """Enhanced tool executor with safety features and monitoring."""
    
    def __init__(self, config: AIDevConfig) -> None:
        self.config = config
        self.repo_root = self._get_repo_root()
        self.allowed_commands = self._build_allowed_commands()
    
    def _get_repo_root(self) -> Path:
        """Get the repository root directory."""
        if self.config.target_repo:
            return Path(self.config.target_repo).resolve()
        return Path.cwd().resolve()
    
    def _build_allowed_commands(self) -> List[str]:
        """Build the list of allowed commands based on config and auto-detection."""
        commands = self.config.tools.allowed_commands.copy()
        
        if self.config.auto_detect_tools:
            # Auto-detect available tools
            package_files = {
                "package.json": ["npm install", "npm test", "npm run", "yarn install", "yarn test"],
                "requirements.txt": ["pip install -r requirements.txt", "python -m pip install"],
                "pyproject.toml": ["pip install -e .", "poetry install", "poetry run"],
                "Cargo.toml": ["cargo build", "cargo test", "cargo run"],
                "go.mod": ["go build", "go test", "go run"],
                "Gemfile": ["bundle install", "bundle exec"],
            }
            
            for file, tools in package_files.items():
                if (self.repo_root / file).exists():
                    commands.extend(tools)
                    logger.info(f"Auto-detected {file}, added tools: {tools}")
        
        return list(set(commands))  # Remove duplicates
    
    def _jail_path(self, path: str) -> Path:
        """Ensure path is within the repository jail."""
        base = self.repo_root
        target = (base / path).resolve()
        
        if not str(target).startswith(str(base)):
            raise ValueError(f"Path '{path}' escapes repository jail")
        
        return target
    
    def _is_command_allowed(self, command: str) -> bool:
        """Check if a command is allowed."""
        command = command.strip()
        return any(command.startswith(allowed) for allowed in self.allowed_commands)
    
    def read_file(self, path: str) -> Dict[str, Any]:
        """Read a file within the repository."""
        try:
            file_path = self._jail_path(path)
            
            if not file_path.exists():
                return {"ok": False, "error": "File not found"}
            
            if file_path.stat().st_size > 1_000_000:  # 1MB limit
                return {"ok": False, "error": "File too large (>1MB)"}
            
            content = file_path.read_text(encoding="utf-8")
            relative_path = str(file_path.relative_to(self.repo_root))
            
            logger.info(f"Read file: {relative_path} ({len(content)} chars)")
            
            return {
                "ok": True,
                "path": relative_path,
                "content": content,
                "size": len(content)
            }
        
        except Exception as e:
            logger.error(f"Error reading file {path}: {e}")
            return {"ok": False, "error": str(e)}
    
    def write_file(self, path: str, content: str) -> Dict[str, Any]:
        """Write a file within the repository."""
        try:
            file_path = self._jail_path(path)
            
            # Create parent directories if needed
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Backup existing file if it exists
            backup_path = None
            if file_path.exists():
                backup_path = file_path.with_suffix(file_path.suffix + ".bak")
                shutil.copy2(file_path, backup_path)
            
            file_path.write_text(content, encoding="utf-8")
            relative_path = str(file_path.relative_to(self.repo_root))
            
            logger.info(f"Wrote file: {relative_path} ({len(content)} chars)")
            
            result = {
                "ok": True,
                "path": relative_path,
                "size": len(content.encode("utf-8"))
            }
            
            if backup_path:
                result["backup"] = str(backup_path.relative_to(self.repo_root))
            
            return result
        
        except Exception as e:
            logger.error(f"Error writing file {path}: {e}")
            return {"ok": False, "error": str(e)}
    
    def bash(self, command: str, timeout: Optional[int] = None) -> Dict[str, Any]:
        """Execute a bash command with safety restrictions."""
        command = command.strip()
        
        if not self._is_command_allowed(command):
            logger.warning(f"Command not allowed: {command}")
            return {
                "ok": False,
                "error": f"Command not allowed: {command}",
                "allowed_prefixes": self.allowed_commands
            }
        
        timeout = timeout or self.config.tools.default_timeout
        timeout = min(timeout, self.config.tools.max_timeout)
        
        logger.info(f"Executing command: {command} (timeout: {timeout}s)")
        
        start_time = time.time()
        
        try:
            proc = subprocess.run(
                command,
                shell=True,
                cwd=str(self.repo_root),
                capture_output=True,
                text=True,
                timeout=timeout,
                env={**os.environ, "PYTHONPATH": str(self.repo_root)}
            )
            
            duration = time.time() - start_time
            
            # Truncate long output
            stdout = proc.stdout[-8000:] if proc.stdout else ""
            stderr = proc.stderr[-8000:] if proc.stderr else ""
            
            result = {
                "ok": proc.returncode == 0,
                "returncode": proc.returncode,
                "stdout": stdout,
                "stderr": stderr,
                "duration": round(duration, 2)
            }
            
            if proc.returncode != 0:
                logger.warning(f"Command failed with exit code {proc.returncode}: {command}")
            else:
                logger.info(f"Command completed successfully in {duration:.2f}s: {command}")
            
            return result
        
        except subprocess.TimeoutExpired:
            logger.error(f"Command timed out after {timeout}s: {command}")
            return {"ok": False, "error": f"Command timed out after {timeout}s"}
        
        except Exception as e:
            logger.error(f"Error executing command '{command}': {e}")
            return {"ok": False, "error": str(e)}
    
    def git_diff(self, staged: bool = False) -> Dict[str, Any]:
        """Get git diff of the working tree or staged changes."""
        try:
            cmd = "git diff --cached" if staged else "git diff"
            
            proc = subprocess.run(
                cmd,
                shell=True,
                cwd=str(self.repo_root),
                capture_output=True,
                text=True,
                timeout=20
            )
            
            if proc.returncode != 0:
                return {"ok": False, "error": proc.stderr}
            
            diff_text = proc.stdout
            
            # Count additions/deletions
            lines = diff_text.split('\n')
            additions = sum(1 for line in lines if line.startswith('+') and not line.startswith('+++'))
            deletions = sum(1 for line in lines if line.startswith('-') and not line.startswith('---'))
            
            logger.info(f"Git diff: +{additions}/-{deletions} lines")
            
            return {
                "ok": True,
                "diff": diff_text,
                "stats": {"additions": additions, "deletions": deletions},
                "staged": staged
            }
        
        except Exception as e:
            logger.error(f"Error getting git diff: {e}")
            return {"ok": False, "error": str(e)}
    
    def git_apply(self, patch: str, staged: bool = True) -> Dict[str, Any]:
        """Apply a git patch."""
        try:
            cmd = "git apply --cached -" if staged else "git apply -"
            
            proc = subprocess.run(
                cmd,
                input=patch,
                shell=True,
                cwd=str(self.repo_root),
                capture_output=True,
                text=True,
                timeout=20
            )
            
            if proc.returncode != 0:
                return {"ok": False, "error": proc.stderr}
            
            logger.info("Git patch applied successfully")
            
            return {
                "ok": True,
                "message": "Patch applied successfully" + (" (staged)" if staged else "")
            }
        
        except Exception as e:
            logger.error(f"Error applying git patch: {e}")
            return {"ok": False, "error": str(e)}
    
    def list_files(self, pattern: str = "*", max_files: int = 100) -> Dict[str, Any]:
        """List files in the repository matching a pattern."""
        try:
            files = list(self.repo_root.glob(pattern))[:max_files]
            file_info = []
            
            for file in files:
                if file.is_file():
                    relative_path = str(file.relative_to(self.repo_root))
                    file_info.append({
                        "path": relative_path,
                        "size": file.stat().st_size,
                        "modified": file.stat().st_mtime
                    })
            
            logger.info(f"Listed {len(file_info)} files matching '{pattern}'")
            
            return {"ok": True, "files": file_info}
        
        except Exception as e:
            logger.error(f"Error listing files with pattern '{pattern}': {e}")
            return {"ok": False, "error": str(e)}