"""
Log Level Override Model.

Strongly-typed model for per-module or per-logger log level overrides.
Replaces dict[str, str] with proper type safety and enum validation.

Strict typing is enforced: No Any types allowed in implementation.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_log_level import EnumLogLevel
from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelLogLevelOverride(BaseModel):
    """
    Strongly-typed log level override configuration.

    Defines per-module or per-logger log level overrides with
    proper enum validation and type safety.
    """

    # Model version for instance tracking
    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Model version (MUST be provided in YAML contract)",
    )

    logger_name: str = Field(
        ...,
        description=(
            "Name of the logger or module to override. "
            "Must follow Python logger naming conventions using dotted notation "
            "(e.g., 'myapp', 'myapp.module', 'myapp.module.submodule'). "
            "Valid characters: lowercase letters, numbers, underscores, and dots."
        ),
        min_length=1,
        pattern=r"^[a-z_][a-z0-9_]*(\.[a-z_][a-z0-9_]*)*$",
    )

    log_level: EnumLogLevel = Field(
        ...,
        description="Log level to apply to this logger/module",
    )

    apply_to_children: bool = Field(
        default=True,
        description="Whether to apply this override to child loggers",
    )

    override_priority: int = Field(
        default=100,
        description="Priority of this override (higher values take precedence)",
        ge=0,
        le=1000,
    )

    description: str | None = Field(
        default=None,
        description="Reason for this log level override",
    )

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )
