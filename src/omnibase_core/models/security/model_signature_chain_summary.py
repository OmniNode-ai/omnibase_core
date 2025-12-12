"""
Signature Chain Summary Model.

Signature chain summary with validation status and trust level information.
"""

from uuid import UUID

from pydantic import BaseModel, Field

from omnibase_core.models.security.model_security_summaries import ModelChainInfoSummary


class ModelSignatureChainSummary(BaseModel):
    """Signature chain summary."""

    chain_id: UUID = Field(default=..., description="Chain identifier")
    envelope_id: UUID = Field(default=..., description="Envelope identifier")
    signature_count: int = Field(default=..., description="Total signatures")
    unique_signers: int = Field(default=..., description="Unique signers")
    operations: list[str] = Field(default=..., description="Operations performed")
    algorithms: list[str] = Field(default=..., description="Algorithms used")
    has_complete_route: bool = Field(default=..., description="Route completeness")
    validation_status: str = Field(default=..., description="Validation status")
    trust_level: str = Field(default=..., description="Trust level")
    created_at: str = Field(default=..., description="Creation timestamp")
    last_modified: str = Field(default=..., description="Last modification")
    chain_hash: str = Field(default=..., description="Chain hash (truncated)")
    compliance_frameworks: list[str] = Field(
        default=..., description="Compliance frameworks"
    )

    def get_operation_count(self) -> int:
        """Get number of operations."""
        return len(self.operations)

    def get_algorithm_count(self) -> int:
        """Get number of algorithms."""
        return len(self.algorithms)

    def get_compliance_count(self) -> int:
        """Get number of compliance frameworks."""
        return len(self.compliance_frameworks)

    def is_valid(self) -> bool:
        """Check if chain is valid."""
        return self.validation_status.lower() == "valid"

    def is_trusted(self) -> bool:
        """Check if chain is trusted."""
        return self.trust_level.lower() in ["high", "trusted"]

    def get_signer_efficiency(self) -> float:
        """Get signer efficiency ratio."""
        if self.signature_count == 0:
            return 0.0
        return self.unique_signers / self.signature_count

    def get_chain_summary(self) -> ModelChainInfoSummary:
        """Get signature chain summary."""
        return ModelChainInfoSummary(
            chain_id=self.chain_id,
            envelope_id=self.envelope_id,
            signature_count=self.signature_count,
            unique_signers=self.unique_signers,
            signer_efficiency=self.get_signer_efficiency(),
            operation_count=self.get_operation_count(),
            algorithm_count=self.get_algorithm_count(),
            compliance_count=self.get_compliance_count(),
            is_valid=self.is_valid(),
            is_trusted=self.is_trusted(),
            has_complete_route=self.has_complete_route,
            validation_status=self.validation_status,
            trust_level=self.trust_level,
        )
