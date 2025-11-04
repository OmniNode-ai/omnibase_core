"""
Mixin metadata information model.

Provides comprehensive information about mixin capabilities, compatibility,
dependencies, and usage for autonomous code generation systems.
"""

from typing import Any

from pydantic import BaseModel, Field

from omnibase_core.models.primitives.model_semver import ModelSemVer


# ONEX NAMING VALIDATION: This model correctly follows the Model* prefix convention.
# Any validator suggesting "MixinModelInfo" is incorrect - all Pydantic BaseModel
# subclasses must start with "Model" per ONEX architectural standards.
# Correct: ModelMixinInfo | Incorrect: MixinModelInfo
class ModelMixinInfo(BaseModel):
    """
    Metadata information for a single mixin.

    Provides comprehensive information about mixin capabilities, compatibility,
    dependencies, and usage for autonomous code generation systems.
    """

    model_config = {
        "extra": "ignore",
        "validate_assignment": True,
    }

    name: str = Field(
        ...,
        description="Mixin class name (e.g., 'MixinEventBus')",
        json_schema_extra={"example": "MixinEventBus"},
    )
    description: str = Field(
        ...,
        description="Human-readable description of mixin functionality",
        json_schema_extra={"example": "Event-driven communication capabilities"},
    )
    version: ModelSemVer = Field(
        ...,
        description="Semantic version of the mixin",
        json_schema_extra={"example": {"major": 1, "minor": 0, "patch": 0}},
    )
    category: str = Field(
        ...,
        description="Functional category (e.g., 'communication', 'caching')",
        json_schema_extra={"example": "communication"},
    )
    requires: list[str] = Field(
        default_factory=list,
        description="Required dependencies (packages, modules)",
        json_schema_extra={
            "example": ["omnibase_core.core.onex_container", "pydantic"]
        },
    )
    compatible_with: list[str] = Field(
        default_factory=list,
        description="List of mixins this is compatible with",
        json_schema_extra={"example": ["MixinCaching", "MixinHealthCheck"]},
    )
    incompatible_with: list[str] = Field(
        default_factory=list,
        description="List of mixins this is incompatible with",
        json_schema_extra={"example": ["MixinSynchronous"]},
    )
    config_schema: dict[str, Any] = Field(
        default_factory=dict,
        description="Configuration schema for this mixin",
        json_schema_extra={
            "example": {
                "event_bus_type": {
                    "type": "string",
                    "enum": ["redis", "kafka", "memory"],
                    "default": "redis",
                }
            }
        },
    )
    usage_examples: list[str] = Field(
        default_factory=list,
        description="Usage examples and use cases",
        json_schema_extra={
            "example": [
                "Database adapters that need to publish events",
                "API clients that emit status updates",
            ]
        },
    )
