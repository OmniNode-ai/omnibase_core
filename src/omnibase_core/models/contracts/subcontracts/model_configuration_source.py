"""
Configuration Source Model.

Model for configuration source specifications in the ONEX configuration management system.
"""

from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelConfigurationSource(BaseModel):
    """Configuration source specification with priority and validation."""

    # Model version for instance tracking
    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Model version (MUST be provided in YAML contract)",
    )

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )

    # ONEX: Add unique identifier for source tracking
    source_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for this configuration source",
    )

    source_type: str = Field(
        default=...,
        description="Type of configuration source (file, environment, database, etc.)",
        pattern=r"^[a-z_]+$",
    )

    source_path: object | None = Field(
        default=None,
        description="Path or identifier for the configuration source",
    )

    priority: int = Field(
        default=100,
        description="Priority for configuration merging (lower = higher priority)",
        ge=0,
        le=1000,
    )

    required: bool = Field(
        default=False,
        description="Whether this configuration source is required",
    )

    watch_for_changes: bool = Field(
        default=False,
        description="Whether to monitor this source for configuration changes",
    )
