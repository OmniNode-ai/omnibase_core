"""
Security Utilities for ONEX

Provides security validation and sanitization functions.
"""

import re
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Union

from pydantic import BaseModel


class SecurityError(Exception):
    """Raised when security validation fails."""

    pass


def validate_file_path(
    file_path: str, allowed_dirs: Optional[List[str]] = None
) -> Path:
    """
    Validate and sanitize file path to prevent directory traversal attacks.

    Args:
        file_path: Path to validate
        allowed_dirs: List of allowed directories (relative to project root)

    Returns:
        Validated Path object

    Raises:
        SecurityError: If path is invalid or unsafe
    """
    if not file_path:
        raise SecurityError("Empty file path provided")

    # Convert to Path and resolve to absolute path
    path = Path(file_path).resolve()

    # Get project root (assume we're running from project root)
    project_root = Path.cwd().resolve()

    # Ensure path is within project directory
    try:
        path.relative_to(project_root)
    except ValueError:
        raise SecurityError(f"Path {path} is outside project directory")

    # Check against allowed directories if specified
    if allowed_dirs:
        allowed = False
        for allowed_dir in allowed_dirs:
            allowed_path = (project_root / allowed_dir).resolve()
            try:
                path.relative_to(allowed_path)
                allowed = True
                break
            except ValueError:
                continue

        if not allowed:
            raise SecurityError(
                f"Path {path} not in allowed directories: {allowed_dirs}"
            )

    return path


def validate_file_size(file_path: Path, max_size_mb: float = 10.0) -> None:
    """
    Validate file size to prevent memory exhaustion.

    Args:
        file_path: Path to file
        max_size_mb: Maximum allowed size in MB

    Raises:
        SecurityError: If file is too large
    """
    if not file_path.exists():
        raise SecurityError(f"File does not exist: {file_path}")

    file_size = file_path.stat().st_size
    max_size_bytes = max_size_mb * 1024 * 1024

    if file_size > max_size_bytes:
        raise SecurityError(
            f"File {file_path} is {file_size / 1024 / 1024:.2f}MB, "
            f"exceeds limit of {max_size_mb}MB"
        )


def sanitize_branch_name(branch_name: str) -> str:
    """
    Sanitize branch name to prevent shell injection.

    Args:
        branch_name: Branch name to sanitize

    Returns:
        Sanitized branch name

    Raises:
        SecurityError: If branch name is invalid
    """
    if not branch_name:
        raise SecurityError("Empty branch name provided")

    # Remove dangerous characters
    sanitized = re.sub(r"[^a-zA-Z0-9\-_/]", "", branch_name)

    # Ensure it doesn't start with - or /
    sanitized = sanitized.lstrip("-/")

    if not sanitized:
        raise SecurityError("Branch name contains only invalid characters")

    if len(sanitized) > 100:
        raise SecurityError("Branch name too long (max 100 characters)")

    return sanitized


def safe_read_file(
    file_path: Path, max_size_mb: float = 10.0, encoding: str = "utf-8"
) -> str:
    """
    Safely read file with size and encoding validation.

    Args:
        file_path: Path to file
        max_size_mb: Maximum allowed size in MB
        encoding: Text encoding to use

    Returns:
        File contents as string

    Raises:
        SecurityError: If file is unsafe to read
    """
    validate_file_size(file_path, max_size_mb)

    try:
        return file_path.read_text(encoding=encoding)
    except UnicodeDecodeError as e:
        raise SecurityError(f"Failed to decode file {file_path}: {e}")
    except OSError as e:
        raise SecurityError(f"Failed to read file {file_path}: {e}")


def safe_subprocess_run(
    cmd: List[str], check: bool = True, capture_output: bool = False
) -> subprocess.CompletedProcess[str]:
    """
    Safely execute subprocess with input validation.

    Args:
        cmd: Command and arguments as list
        check: Whether to raise on non-zero exit code
        capture_output: Whether to capture stdout/stderr

    Returns:
        CompletedProcess result

    Raises:
        SecurityError: If command is unsafe
    """
    if not cmd or not isinstance(cmd, list):
        raise SecurityError("Command must be a non-empty list")

    # Validate command name
    command = cmd[0]
    allowed_commands = ["git", "gh"]  # Only allow specific commands

    if command not in allowed_commands:
        raise SecurityError(f"Command '{command}' not allowed")

    # Validate arguments for dangerous patterns
    for arg in cmd[1:]:
        if not isinstance(arg, str):
            raise SecurityError("All arguments must be strings")

        # Check for shell injection patterns
        dangerous_patterns = [";", "&&", "||", "|", ">", "<", "`", "$"]
        if any(pattern in arg for pattern in dangerous_patterns):
            raise SecurityError(f"Dangerous pattern detected in argument: {arg}")

    try:
        return subprocess.run(
            cmd, check=check, capture_output=capture_output, text=True
        )
    except subprocess.CalledProcessError as e:
        raise SecurityError(f"Command failed: {' '.join(cmd)}: {e}")
    except OSError as e:
        raise SecurityError(f"Failed to execute command: {e}")


def validate_scenario_content(content: Dict[str, str]) -> None:
    """
    Validate scenario content to prevent injection attacks.

    Args:
        content: Scenario content dictionary

    Raises:
        SecurityError: If content is unsafe
    """
    if not isinstance(content, dict):
        raise SecurityError("Scenario content must be a dictionary")

    # Check for dangerous patterns in string values
    dangerous_patterns = [
        r"`.*`",  # Backticks (command substitution)
        r"\$\(",  # Command substitution
        r">\s*/",  # Redirection to system paths
        r";\s*rm",  # Dangerous commands
        r"&&\s*rm",
        r"\|\s*sh",
    ]

    def check_string_safety(s: str) -> None:
        for pattern in dangerous_patterns:
            if re.search(pattern, s, re.IGNORECASE):
                raise SecurityError(f"Dangerous pattern detected: {pattern}")

    def check_recursive(obj: Union[str, Dict[str, str], List[str]]) -> None:
        if isinstance(obj, str):
            check_string_safety(obj)
        elif isinstance(obj, dict):
            for value in obj.values():
                check_recursive(value)
        elif isinstance(obj, list):
            for item in obj:
                check_recursive(item)

    check_recursive(content)


def safe_write_file(
    file_path: str,
    content: str,
    allowed_dirs: Optional[List[str]] = None,
    max_size_mb: float = 10.0,
) -> Path:
    """
    Safely write content to a file with security validation.

    Args:
        file_path: Path to write to
        content: Content to write
        allowed_dirs: List of allowed directory names (default: docs, src, tests)
        max_size_mb: Maximum file size in MB

    Returns:
        Path object of written file

    Raises:
        SecurityError: If file path or content is invalid
    """
    if not content:
        raise SecurityError("Cannot write empty content")

    # Validate content size
    content_size_mb = len(content.encode("utf-8")) / (1024 * 1024)
    if content_size_mb > max_size_mb:
        raise SecurityError(
            f"Content too large: {content_size_mb:.2f}MB > {max_size_mb}MB"
        )

    # Validate file path
    validated_path = validate_file_path(file_path, allowed_dirs)

    # Ensure parent directory exists
    validated_path.parent.mkdir(parents=True, exist_ok=True)

    # Write file securely
    try:
        validated_path.write_text(content, encoding="utf-8")
        return validated_path
    except Exception as e:
        raise SecurityError(f"Failed to write file {validated_path}: {e}")
