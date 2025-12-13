"""
ModelOutputConfig

Output formatting and destination configuration.

IMPORT ORDER CONSTRAINTS (Critical - Do Not Break):
===============================================
This module is part of a carefully managed import chain to avoid circular dependencies.

Safe Runtime Imports (OK to import at module level):
- Standard library modules only
"""

from typing import Any

from pydantic import BaseModel, Field, field_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError


class ModelOutputConfig(BaseModel):
    """Output formatting and destination configuration."""

    format: str = Field(default="json", description="Output format (json|yaml|text)")
    colored: bool = Field(default=True, description="Enable colored output")
    progress_bars: bool = Field(default=True, description="Show progress bars")
    log_level: str = Field(default="INFO", description="Logging level")

    @field_validator("format")
    @classmethod
    def validate_format(cls, v: Any) -> Any:
        allowed = {"json", "yaml", "text"}
        if v not in allowed:
            raise ModelOnexError(
                f"format must be one of {allowed}", EnumCoreErrorCode.VALIDATION_ERROR
            )
        return v

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: Any) -> Any:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v not in allowed:
            raise ModelOnexError(
                f"log_level must be one of {allowed}",
                EnumCoreErrorCode.VALIDATION_ERROR,
            )
        return v
