"""
Model for contract information in introspection metadata.
"""

from pydantic import BaseModel, Field

from omnibase_core.models.primitives.model_semver import (
    ModelSemVer,
    default_model_version,
)


class ModelIntrospectionContractInfo(BaseModel):
    """Contract information for introspection metadata."""

    contract_version: ModelSemVer = Field(
        default_factory=default_model_version,
        description="Contract version as SemVer",
    )
    has_definitions: bool = Field(description="Whether contract has definitions")
    definition_count: int = Field(description="Number of definitions in contract")
    contract_path: str | None = Field(description="Path to contract file")
