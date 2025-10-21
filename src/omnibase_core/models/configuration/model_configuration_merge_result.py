from typing import Any

from pydantic import Field

"""
Configuration Merge Result Model for ONEX Configuration System.

Strongly typed model to replace dict[str, Any]ionary usage in configuration merging.
"""

from pydantic import BaseModel

from omnibase_core.models.service.model_service_registry_config import (
    ModelServiceRegistryConfig,
)


class ModelConfigurationMergeResult(BaseModel):
    """
    Strongly typed model for configuration merge results.

    Replaces dict[str, Any]ionary usage in configuration management
    with proper Pydantic validation and type safety.
    """

    merged_data: ModelServiceRegistryConfig = Field(
        description="The merged and validated service configuration",
    )

    source_files: list[str] = Field(
        default_factory=list,
        description="List of configuration file paths that were merged",
    )

    environment_overrides_applied: int = Field(
        default=0,
        description="Number of environment variable overrides applied",
    )

    validation_errors: list[str] = Field(
        default_factory=list,
        description="Any validation errors encountered during merge",
    )

    merge_strategy_used: str = Field(
        default="deep_merge",
        description="The merge strategy that was applied",
    )
