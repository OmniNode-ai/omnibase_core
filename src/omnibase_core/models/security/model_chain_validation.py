"""Chain Validation Model.

Chain validation details for signature verification.
"""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ModelChainValidation(BaseModel):
    """Chain validation details.

    Note:
        This model uses frozen=True for immutability and from_attributes=True
        to support pytest-xdist parallel execution where class identity may
        differ between workers.
    """

    model_config = ConfigDict(frozen=True, from_attributes=True)

    chain_id: UUID = Field(default=..., description="Chain identifier")
    envelope_id: UUID = Field(default=..., description="Envelope identifier")
    signature_count: int = Field(default=..., description="Total signatures in chain")
    unique_signers: int = Field(default=..., description="Number of unique signers")
    operations: list[str] = Field(default=..., description="Operations performed")
    algorithms: list[str] = Field(default=..., description="Algorithms used")
    has_complete_route: bool = Field(
        default=..., description="Whether route is complete"
    )
    validation_status: str = Field(default=..., description="Validation status")
    trust_level: str = Field(default=..., description="Trust level")
    created_at: str = Field(default=..., description="Chain creation timestamp")
    last_modified: str = Field(default=..., description="Last modification timestamp")
    chain_hash: str = Field(default=..., description="Chain hash (truncated)")
    compliance_frameworks: list[str] = Field(
        default=..., description="Applicable frameworks"
    )
