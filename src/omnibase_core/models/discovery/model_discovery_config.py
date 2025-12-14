"""Tool discovery configuration model with caching, depth control, and filtering options."""

import warnings
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError


class ModelDiscoveryConfig(BaseModel):
    """
    Tool discovery configuration with advanced options for filtering, caching, and performance.

    Supports flexible discovery strategies for different deployment environments.
    """

    # Basic discovery settings
    discovery_mode: str = Field(
        default="standard",
        description="Discovery mode identifier",
    )
    max_depth: int | None = Field(
        default=None,
        description="Maximum directory depth to traverse",
        ge=0,
        le=20,
    )
    follow_symlinks: bool = Field(
        default=False,
        description="Whether to follow symbolic links",
    )

    # Performance and caching
    enable_caching: bool = Field(
        default=True,
        description="Enable discovery result caching",
    )
    cache_ttl_seconds: int = Field(
        default=300,
        description="Cache time-to-live in seconds",
        gt=0,
        le=86400,
    )
    parallel_discovery: bool = Field(
        default=True,
        description="Enable parallel directory scanning",
    )
    max_concurrent_scans: int = Field(
        default=10,
        description="Maximum concurrent directory scans",
        ge=1,
        le=50,
    )

    # Filtering and inclusion
    include_patterns: list[str] = Field(
        default_factory=lambda: ["tool_*.py"],
        description="File patterns to include in discovery",
    )
    exclude_patterns: list[str] = Field(
        default_factory=lambda: ["__pycache__", "*.pyc", "test_*"],
        description="File patterns to exclude from discovery",
    )
    exclude_directories: set[str] = Field(
        default_factory=lambda: {".git", ".svn", "node_modules", "__pycache__"},
        description="Directory names to exclude",
    )

    # Validation and contract checking
    validate_contracts: bool = Field(
        default=True,
        description="Validate tool contracts during discovery",
    )
    strict_contract_validation: bool = Field(
        default=True,
        description="Use strict contract validation rules",
    )
    schema_validation_timeout: int = Field(
        default=30,
        description="Timeout for schema validation per tool",
        gt=0,
        le=300,
    )

    # Error handling
    fail_fast: bool = Field(default=False, description="Stop discovery on first error")
    max_errors_before_abort: int = Field(
        default=10,
        description="Maximum errors before aborting discovery",
        ge=1,
        le=100,
    )
    log_skipped_tools: bool = Field(
        default=True,
        description="Log information about skipped tools",
    )

    # Advanced features
    deduplicate_tools: bool = Field(
        default=True,
        description="Remove duplicate tool discoveries",
    )
    sort_results: bool = Field(
        default=True,
        description="Sort discovery results alphabetically",
    )
    include_metadata: bool = Field(
        default=True,
        description="Include tool metadata in discovery results",
    )

    @field_validator("discovery_mode")
    @classmethod
    def validate_discovery_mode(cls, v: Any) -> Any:
        """Validate discovery mode."""
        valid_modes = {"standard", "recursive", "shallow", "deep", "cached", "fast"}
        if v not in valid_modes:
            msg = f"discovery_mode must be one of {valid_modes}"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )
        return v

    @field_validator("include_patterns")
    @classmethod
    def validate_include_patterns_not_empty(cls, v: Any) -> Any:
        """Ensure include patterns is not empty."""
        if not v:
            msg = "include_patterns cannot be empty"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )
        return v

    @model_validator(mode="after")
    def warn_deep_max_depth(self) -> "ModelDiscoveryConfig":
        """Emit warning for potentially problematic max_depth values.

        This is a post-construction validator that emits a warning (not an error)
        when max_depth exceeds 15, which may cause performance issues during
        directory traversal.
        """
        if self.max_depth is not None and self.max_depth > 15:
            warnings.warn(
                f"max_depth {self.max_depth} may cause performance issues. "
                "Consider using max_depth <= 15 for optimal discovery performance.",
                UserWarning,
                stacklevel=3,  # Account for Pydantic validator call stack
            )
        return self
