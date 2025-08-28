"""
Model for contract information in introspection metadata.
"""

from typing import Optional

from pydantic import BaseModel, Field

from omnibase.core.models.model_semver import ModelSemVer


class ModelIntrospectionContractInfo(BaseModel):
    """Contract information for introspection metadata."""

    contract_version: ModelSemVer = Field(description="Contract version as SemVer")
    has_definitions: bool = Field(description="Whether contract has definitions")
    definition_count: int = Field(description="Number of definitions in contract")
    contract_path: Optional[str] = Field(description="Path to contract file")

    class Config:
        json_schema_extra = {
            "example": {
                "contract_version": {
                    "major": 1,
                    "minor": 0,
                    "patch": 0,
                    "prerelease": None,
                    "build": None,
                },
                "has_definitions": True,
                "definition_count": 5,
                "contract_path": "/path/to/contract.yaml",
            }
        }
