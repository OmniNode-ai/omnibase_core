import re
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator

# Import the existing enum from enums module
from omnibase_core.enums.enum_validation_severity import EnumValidationSeverity

"""
Individual validation issue with proper typing.

Represents a specific issue found during validation with
comprehensive metadata and suggestions.
"""


class ModelValidationIssue(BaseModel):
    """
    Individual validation issue with proper typing.

    Represents a specific issue found during validation with
    comprehensive metadata and suggestions.
    """

    severity: EnumValidationSeverity = Field(
        ...,
        description="Severity level of the issue",
    )
    message: str = Field(..., description="Human-readable issue description")
    code: str | None = Field(
        None,
        description="Machine-readable error code for programmatic handling",
    )
    file_path: Path | None = Field(
        None,
        description="Path to file where issue was found (always Path object, never string)",
    )
    line_number: int | None = Field(
        None,
        description="Line number where issue was found",
    )
    column_number: int | None = Field(
        None,
        description="Column number where issue was found",
    )
    rule_name: str | None = Field(
        None,
        description="Name of validation rule that triggered this issue",
    )
    suggestion: str | None = Field(None, description="Suggested fix for the issue")
    context: dict[str, str] | None = Field(
        None,
        description="Additional string context data for the issue (no Any types)",
    )

    @field_validator("context")
    @classmethod
    def sanitize_context(cls, v: dict[str, str] | None) -> dict[str, str] | None:
        """
        Sanitize context data to prevent sensitive information exposure.

        Removes or masks potentially sensitive data patterns like:
        - API keys, tokens, passwords
        - Email addresses
        - URLs with query parameters
        - File paths containing usernames
        """
        if v is None:
            return v

        sanitized = {}

        # Patterns to detect sensitive data
        sensitive_patterns = [
            (
                r"(?i)(api[_-]?key|token|password|secret|auth)",
                r"[REDACTED]",
            ),  # API keys, passwords
            (
                r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
                r"[EMAIL_REDACTED]",
            ),  # Email addresses
            (
                r"https?://[^\s]*\?[^\s]*",
                r"[URL_WITH_PARAMS_REDACTED]",
            ),  # URLs with query params
            (r"/Users/[^/\s]+", r"/Users/[USERNAME]"),  # User paths on macOS
            (r"C:\\Users\\[^\\]+", r"C:\\Users\\[USERNAME]"),  # User paths on Windows
        ]

        for key, value in v.items():
            if not isinstance(value, str):
                # Skip non-string values
                sanitized[key] = str(value)[:100]  # Truncate to prevent DoS
                continue

            sanitized_value = value

            # Apply sanitization patterns
            for pattern, replacement in sensitive_patterns:
                sanitized_value = re.sub(pattern, replacement, sanitized_value)

            # Truncate very long values to prevent DoS
            if len(sanitized_value) > 500:
                sanitized_value = sanitized_value[:497] + "..."

            sanitized[key] = sanitized_value

        return sanitized
