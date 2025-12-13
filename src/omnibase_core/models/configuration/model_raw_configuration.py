"""
Raw Configuration Model for ONEX Configuration System.

Strongly typed model for unvalidated configuration data loaded from YAML files.
"""

from pydantic import BaseModel, Field

from omnibase_core.models.configuration.model_raw_registry_mode import (
    ModelRawRegistryMode,
)
from omnibase_core.models.configuration.model_raw_service import ModelRawService
from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelRawConfiguration(BaseModel):
    """
    Strongly typed model for raw configuration data from YAML files.

    This represents the structure we expect in YAML configuration files
    before validation and conversion to service registry configuration.
    """

    configuration_version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Configuration schema version",
    )

    default_mode: str | None = Field(
        default="development",
        description="Default registry mode",
    )

    services: dict[str, ModelRawService] = Field(
        default_factory=dict,
        description="Raw service definitions from YAML",
    )

    registry_modes: dict[str, ModelRawRegistryMode] = Field(
        default_factory=dict,
        description="Raw registry mode definitions from YAML",
    )
