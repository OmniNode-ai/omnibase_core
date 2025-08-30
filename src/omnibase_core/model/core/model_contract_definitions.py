"""
Model for contract definitions representation in ONEX NodeBase implementation.

This model supports the PATTERN-005 ContractLoader functionality for
strongly typed contract definitions section.

Author: ONEX Framework Team
"""

from typing import Dict

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.core.models.model_yaml_schema_object import \
    ModelYamlSchemaObject


class ModelContractDefinitions(BaseModel):
    """Model representing contract definitions section."""

    model_config = ConfigDict(extra="ignore")

    definitions: Dict[str, ModelYamlSchemaObject] = Field(
        default_factory=dict, description="Contract definitions mapping"
    )
