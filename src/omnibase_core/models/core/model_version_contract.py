"""
Version Contract Model - Tier 3 Metadata.

Pydantic model for contract file information and validation status.
"""

from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_version_manifest import EnumContractCompliance
from omnibase_core.primitives.model_semver import SemVerField

if TYPE_CHECKING:
    pass


class ModelVersionContract(BaseModel):
    """Contract file information and validation status."""

    contract_file: str = Field(
        default="contract.yaml",
        description="Contract file name",
    )
    contract_version: SemVerField = Field(description="Contract version")
    contract_name: str = Field(description="Contract identifier")
    m1_compliant: bool = Field(
        default=True,
        description="Whether contract follows M1 standards",
    )
    validation_status: EnumContractCompliance = Field(
        description="Contract validation status",
    )
    validation_date: datetime | None = Field(
        default=None,
        description="Date when contract was validated",
    )
    validation_errors: list[str] = Field(
        default_factory=list,
        description="Contract validation errors",
    )
