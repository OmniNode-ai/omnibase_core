"""
Model for contract loader representation in ONEX NodeBase implementation.

This model supports the PATTERN-005 NodeBase functionality for
unified contract loading and resolution.

"""

from pathlib import Path

from pydantic import BaseModel, Field

from omnibase_core.models.core.model_contract_cache import ModelContractCache
from omnibase_core.models.core.model_contract_content import ModelContractContent
from omnibase_core.models.core.model_contract_reference import ModelContractReference


class ModelContractLoader(BaseModel):
    """Model representing contract loader state and configuration."""

    cache_enabled: bool = Field(
        default=True,
        description="Whether contract caching is enabled",
    )
    contract_cache: dict[str, ModelContractCache] = Field(
        default_factory=dict,
        description="Contract cache storage",
    )
    resolution_stack: list[str] = Field(
        default_factory=list,
        description="Current resolution stack for circular reference detection",
    )
    base_path: Path = Field(
        default=..., description="Base path for contract resolution"
    )
    loaded_contracts: dict[str, ModelContractContent] = Field(
        default_factory=dict,
        description="Successfully loaded contracts",
    )
    resolved_references: dict[str, ModelContractReference] = Field(
        default_factory=dict,
        description="Resolved contract references",
    )
