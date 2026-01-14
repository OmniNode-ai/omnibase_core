import re
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Import canonical severity enum
from omnibase_core.enums import EnumSeverity

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

    # from_attributes=True: Required for pytest-xdist parallel execution where
    # model classes may be imported in separate workers with different class identity.
    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        from_attributes=True,
    )

    severity: EnumSeverity = Field(
        default=...,
        description="Severity level of the issue",
    )
    message: str = Field(default=..., description="Human-readable issue description")
    code: str | None = Field(
        default=None,
        description="Machine-readable error code for programmatic handling",
    )
    file_path: Path | None = Field(
        default=None,
        description="Path to file where issue was found (always Path object, never string)",
    )
    line_number: int | None = Field(
        default=None,
        description="Line number where issue was found",
    )
    column_number: int | None = Field(
        default=None,
        description="Column number where issue was found",
    )
    rule_name: str | None = Field(
        default=None,
        description="Name of validation rule that triggered this issue",
    )
    suggestion: str | None = Field(
        default=None, description="Suggested fix for the issue"
    )
    context: dict[str, str] | None = Field(
        default=None,
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
            # All values are guaranteed to be str by type annotation
            sanitized_value = value

            # Apply sanitization patterns
            for pattern, replacement in sensitive_patterns:
                sanitized_value = re.sub(pattern, replacement, sanitized_value)

            # Truncate very long values to prevent DoS
            if len(sanitized_value) > 500:
                sanitized_value = sanitized_value[:497] + "..."

            sanitized[key] = sanitized_value

        return sanitized
