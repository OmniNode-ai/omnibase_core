"""
Raw Configuration Model for ONEX Configuration System.

Strongly typed model for unvalidated configuration data loaded from YAML files.
"""

from typing import Dict, Optional

from pydantic import BaseModel, Field

from omnibase_core.model.configuration.model_raw_registry_mode import \
    ModelRawRegistryMode
from omnibase_core.model.configuration.model_raw_service import ModelRawService


class ModelRawConfiguration(BaseModel):
    """
    Strongly typed model for raw configuration data from YAML files.

    This represents the structure we expect in YAML configuration files
    before validation and conversion to service registry configuration.
    """

    configuration_version: Optional[str] = Field(
        default="1.0", description="Configuration schema version"
    )

    default_mode: Optional[str] = Field(
        default="development", description="Default registry mode"
    )

    services: Dict[str, ModelRawService] = Field(
        default_factory=dict, description="Raw service definitions from YAML"
    )

    registry_modes: Dict[str, ModelRawRegistryMode] = Field(
        default_factory=dict, description="Raw registry mode definitions from YAML"
    )
