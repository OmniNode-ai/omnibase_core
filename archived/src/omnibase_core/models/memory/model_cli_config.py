"""
CLI Configuration Model - ONEX Standards Compliant.

Replaces the CliConfigType dict alias with proper Pydantic model
providing runtime validation, type safety, and clean architecture.

ZERO TOLERANCE: No Any types or dict patterns allowed.
"""

from typing import Literal

from pydantic import BaseModel, Field, field_validator

from omnibase_core.core.errors.core_errors import CoreErrorCode, OnexError


class ModelCliConfig(BaseModel):
    """
    CLI configuration model with strong typing and validation.

    Provides structured configuration for user preferences and settings
    with runtime validation and type safety.

    Replaces: CliConfigType = dict[str, str | int | bool]

    ZERO TOLERANCE: No Any types or dict patterns allowed.
    """

    # API Configuration
    api_url: str = Field(
        default="http://localhost:8089/api/v1",
        description="API endpoint URL for memory service",
        min_length=1,
        max_length=500,
    )

    api_key: str | None = Field(
        default=None,
        description="API authentication key",
        max_length=200,
    )

    # Connection Settings
    connection_timeout: int = Field(
        default=30,
        description="Connection timeout in seconds",
        ge=1,
        le=300,
    )

    # Display Configuration
    default_limit: int = Field(
        default=10,
        description="Default result limit for queries",
        ge=1,
        le=1000,
    )

    rich_output: bool = Field(
        default=True,
        description="Enable rich formatting in output",
    )

    verbose_logging: bool = Field(
        default=False,
        description="Enable verbose logging output",
    )

    # Session Management
    auto_session: bool = Field(
        default=True,
        description="Automatically manage session state",
    )

    # Export Configuration
    export_format: Literal["json", "yaml", "csv", "txt"] = Field(
        default="json",
        description="Default export format for results",
    )

    # Output Configuration
    output_file: str | None = Field(
        default=None,
        description="Default output file path",
        max_length=500,
    )

    # Pagination Settings
    page_size: int = Field(
        default=25,
        description="Results per page for pagination",
        ge=1,
        le=100,
    )

    @field_validator("api_url")
    @classmethod
    def validate_api_url(cls, v: str) -> str:
        """Validate API URL format."""
        v = v.strip()
        if not v:
            raise OnexError(
                error_code=CoreErrorCode.VALIDATION_FAILED,
                message="API URL cannot be empty",
                context={"context": {"onex_principle": "Strong types only"}},
            )

        # Basic URL validation - must start with http:// or https://
        if not (v.startswith("http://") or v.startswith("https://")):
            raise OnexError(
                error_code=CoreErrorCode.VALIDATION_FAILED,
                message="API URL must start with http:// or https://",
                context={
                    "context": {
                        "provided_url": v,
                        "onex_principle": "Strong validation for configuration",
                    }
                },
            )

        return v

    @field_validator("api_key")
    @classmethod
    def validate_api_key(cls, v: str | None) -> str | None:
        """Validate API key format if provided."""
        if v is not None:
            v = v.strip()
            if not v:
                return None  # Empty string becomes None

            # Basic API key validation - non-empty and reasonable length
            if len(v) < 8:
                raise OnexError(
                    error_code=CoreErrorCode.VALIDATION_FAILED,
                    message="API key must be at least 8 characters",
                    context={
                        "context": {"onex_principle": "Strong validation for security"}
                    },
                )

        return v

    @field_validator("output_file")
    @classmethod
    def validate_output_file(cls, v: str | None) -> str | None:
        """Validate output file path if provided."""
        if v is not None:
            v = v.strip()
            if not v:
                return None  # Empty string becomes None

            # Basic path validation - no dangerous patterns
            dangerous_patterns = ["../", "~", "/etc/", "/var/", "/usr/", "/root/"]
            v_lower = v.lower()

            for pattern in dangerous_patterns:
                if pattern in v_lower:
                    raise OnexError(
                        error_code=CoreErrorCode.VALIDATION_FAILED,
                        message=f"Output file path contains dangerous pattern: {pattern}",
                        context={
                            "context": {
                                "file_path": v,
                                "dangerous_pattern": pattern,
                                "onex_principle": "Security validation for file paths",
                            }
                        },
                    )

        return v

    class Config:
        """Pydantic configuration for ONEX compliance."""

        extra = "forbid"  # Reject additional fields for strict typing
        use_enum_values = True  # Convert enum values to strings
        validate_assignment = True  # Validate on field assignment

    def to_dict(self) -> dict[str, str | int | bool | None]:
        """
        Convert to dictionary format for serialization.

        Returns:
            Dictionary representation with type information preserved
        """
        return self.model_dump(exclude_none=True, mode="python")

    @classmethod
    def from_dict(cls, data: dict[str, str | int | bool | None]) -> "ModelCliConfig":
        """
        Create from dictionary data with validation.

        Args:
            data: Dictionary containing configuration values

        Returns:
            Validated ModelCliConfig instance

        Raises:
            OnexError: If validation fails
        """
        try:
            return cls.model_validate(data)
        except Exception as e:
            raise OnexError(
                error_code=CoreErrorCode.VALIDATION_FAILED,
                message=f"CLI configuration validation failed: {e}",
                context={"context": {"input_data": data}},
            ) from e
