"""
Model for contract reference representation in ONEX NodeBase implementation.

This model supports the PATTERN-005 ContractLoader functionality for
unified contract loading and $ref resolution.

"""

from pathlib import Path

from pydantic import BaseModel, Field


class ModelContractReference(BaseModel):
    """Model representing a contract reference ($ref)."""

    ref_path: str = Field(
        default=...,
        description="The reference path (e.g., 'contracts/models.yaml#/InputState')",
    )
    file_path: Path = Field(default=..., description="Resolved file path")
    json_path: str = Field(
        default="",
        description="JSON path within the file (empty string if none)",
    )
