from typing import Any
from uuid import UUID, uuid4

from pydantic import Field

from omnibase_core.enums.enum_chain_validation_status import EnumChainValidationStatus
from omnibase_core.enums.enum_compliance_framework import EnumComplianceFramework
from omnibase_core.enums.enum_trust_level import EnumTrustLevel
from omnibase_core.models.errors.model_onex_error import ModelOnexError

"\nModelSignatureChain: Tamper-evident signature chain for secure envelopes\n\nThis model manages a collection of cryptographic signatures from multiple nodes,\nproviding comprehensive audit trails and tamper detection for event routing.\n"
import hashlib
import json
import logging
from datetime import UTC, datetime, timedelta

from pydantic import BaseModel, ConfigDict, field_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_node_operation import EnumNodeOperation
from omnibase_core.models.security.model_chain_metrics import ModelChainMetrics
from omnibase_core.models.security.model_node_signature import ModelNodeSignature
from omnibase_core.models.security.model_signing_policy import ModelSigningPolicy

logger = logging.getLogger(__name__)


class ModelSignatureChain(BaseModel):
    """
    Tamper-evident signature chain for secure envelope routing.

    Manages an ordered collection of cryptographic signatures from nodes
    that have processed an envelope, providing comprehensive audit trails
    and tamper detection capabilities.

    Note:
        This model uses from_attributes=True to support pytest-xdist parallel
        execution where class identity may differ between workers.
    """

    model_config = ConfigDict(from_attributes=True)

    chain_id: UUID = Field(
        default=...,
        description="Unique identifier for this signature chain",
    )
    envelope_id: UUID = Field(
        default=...,
        description="ID of the envelope this chain belongs to",
    )
    signatures: list[ModelNodeSignature] = Field(
        default_factory=list, description="Ordered list[Any]of signatures in the chain"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When the chain was created (UTC)",
    )
    last_modified: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When the chain was last modified (UTC)",
    )
    chain_hash: str = Field(
        default="",
        description="SHA-256 hash of the complete signature chain",
        min_length=0,
    )
    content_hash: str = Field(
        default=...,
        description="SHA-256 hash of the original envelope content",
        min_length=1,
    )
    validation_status: EnumChainValidationStatus = Field(
        default=EnumChainValidationStatus.INCOMPLETE,
        description="Current validation status of the chain",
    )
    trust_level: EnumTrustLevel = Field(
        default=EnumTrustLevel.UNTRUSTED, description="Overall trust level of the chain"
    )
    signing_policy: ModelSigningPolicy | None = Field(
        default=None, description="Signing policy requirements for this chain"
    )
    compliance_frameworks: list[EnumComplianceFramework] = Field(
        default_factory=list,
        description="Compliance frameworks this chain must satisfy",
    )
    chain_metrics: ModelChainMetrics | None = Field(
        default=None, description="Performance metrics for chain operations"
    )

    @field_validator("signatures")
    @classmethod
    def validate_signature_order(cls, v: Any) -> Any:
        """Validate signatures are in correct hop order."""
        if not v:
            return v
        for i, signature in enumerate(v):
            if signature.hop_index != i:
                raise ModelOnexError(
                    message=f"Signature hop_index mismatch: expected {i} at position {i}, but got {signature.hop_index}",
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    context={
                        "position": i,
                        "expected_hop_index": i,
                        "actual_hop_index": signature.hop_index,
                    },
                )
        return v

    def add_signature(
        self, signature: ModelNodeSignature, validate_chain: bool = True
    ) -> bool:
        """Add a new signature to the chain.

        Args:
            signature: Signature to add
            validate_chain: Whether to validate chain integrity after adding

        Returns:
            True if signature was successfully added
        """
        try:
            if not self._can_add_signature(signature):
                return False
            signature.hop_index = len(self.signatures)
            if self.signatures:
                previous_signature = self.signatures[-1]
                signature.previous_signature_hash = (
                    previous_signature.get_signature_hash()
                )
            self.signatures.append(signature)
            self.last_modified = datetime.now(UTC)
            self._update_chain_hash()
            if validate_chain:
                self.validate_chain_integrity()
            return True
        except ModelOnexError:
            raise
        except (
            AttributeError,
            ValueError,
            TypeError,
            KeyError,
            RuntimeError,
            OSError,
        ) as e:
            logger.exception(
                f"Failed to add signature to chain {self.chain_id}: {e!s}",
                extra={
                    "chain_id": self.chain_id,
                    "signature_node_id": signature.node_id,
                },
            )
            raise ModelOnexError(
                message=f"Failed to add signature to chain: {e!s}",
                error_code=EnumCoreErrorCode.SECURITY_VIOLATION,
                context={
                    "chain_id": str(self.chain_id),
                    "signature_node_id": str(signature.node_id),
                    "operation": "add_signature",
                },
            ) from e

    def _can_add_signature(self, signature: ModelNodeSignature) -> bool:
        """Check if signature can be added to the chain."""
        existing_signers = {sig.node_id for sig in self.signatures}
        if signature.node_id in existing_signers:
            return False
        if self.signatures:
            last_operation = self.signatures[-1].operation
            if not signature.is_valid_operation_sequence(last_operation):
                return False
        elif signature.operation != EnumNodeOperation.SOURCE:
            return False
        return signature.envelope_state_hash == self.content_hash

    def _update_chain_hash(self) -> None:
        """Update the chain hash based on current signatures."""
        if not self.signatures:
            self.chain_hash = ""
            return
        chain_data = {
            "chain_id": self.chain_id,
            "envelope_id": self.envelope_id,
            "content_hash": self.content_hash,
            "signatures": [
                {
                    "node_id": sig.node_id,
                    "signature": sig.signature,
                    "timestamp": sig.timestamp.isoformat(),
                    "hop_index": sig.hop_index,
                    "operation": sig.operation.value,
                }
                for sig in self.signatures
            ],
        }
        chain_json = json.dumps(chain_data, sort_keys=True)
        self.chain_hash = hashlib.sha256(chain_json.encode()).hexdigest()

    def validate_chain_integrity(self) -> bool:
        """Validate the integrity of the signature chain.

        Returns:
            True if chain integrity is valid
        """
        try:
            if not self.signatures:
                self.validation_status = EnumChainValidationStatus.INCOMPLETE
                return False
            for i, signature in enumerate(self.signatures):
                if signature.hop_index != i:
                    self.validation_status = EnumChainValidationStatus.INVALID
                    return False
                if i == 0:
                    if signature.previous_signature_hash is not None:
                        self.validation_status = EnumChainValidationStatus.INVALID
                        return False
                else:
                    previous_signature = self.signatures[i - 1]
                    expected_hash = previous_signature.get_signature_hash()
                    if signature.previous_signature_hash != expected_hash:
                        self.validation_status = EnumChainValidationStatus.TAMPERED
                        return False
                previous_operation = self.signatures[i - 1].operation if i > 0 else None
                if not signature.is_valid_operation_sequence(previous_operation):
                    self.validation_status = EnumChainValidationStatus.INVALID
                    return False
            if not self._validate_signing_policy():
                self.validation_status = EnumChainValidationStatus.INCOMPLETE
                return False
            self.validation_status = EnumChainValidationStatus.VALID
            return True
        except ModelOnexError:
            raise
        except (
            AttributeError,
            ValueError,
            TypeError,
            KeyError,
            RuntimeError,
            OSError,
        ) as e:
            logger.exception(
                f"Chain integrity validation failed for chain {self.chain_id}: {e!s}",
                extra={
                    "chain_id": self.chain_id,
                    "signatures_count": len(self.signatures),
                },
            )
            self.validation_status = EnumChainValidationStatus.INVALID
            raise ModelOnexError(
                message=f"Chain integrity validation failed: {e!s}",
                error_code=EnumCoreErrorCode.SECURITY_VIOLATION,
                context={
                    "chain_id": str(self.chain_id),
                    "signatures_count": len(self.signatures),
                    "operation": "validate_chain_integrity",
                },
            ) from e

    def _validate_signing_policy(self) -> bool:
        """Validate chain meets signing policy requirements."""
        if not self.signing_policy:
            return True
        policy = self.signing_policy
        if len(self.signatures) < policy.minimum_signatures:
            return False
        chain_operations = {sig.operation.value for sig in self.signatures}
        for required_op in policy.required_operations:
            if required_op not in chain_operations:
                return False
        trusted_count = len(
            [sig for sig in self.signatures if sig.node_id in policy.trusted_nodes]
        )
        return not trusted_count < policy.minimum_trusted_signatures

    def get_unique_signers(self) -> set[str]:
        """Get set of unique node IDs that signed this chain."""
        return {str(signature.node_id) for signature in self.signatures}

    def get_signature_by_node(self, node_id: UUID) -> ModelNodeSignature | None:
        """Get signature from specific node."""
        for signature in self.signatures:
            if signature.node_id == node_id:
                return signature
        return None

    def get_signatures_by_operation(
        self, operation: EnumNodeOperation
    ) -> list[ModelNodeSignature]:
        """Get all signatures for specific operation type."""
        return [sig for sig in self.signatures if sig.operation == operation]

    def has_complete_route(self) -> bool:
        """Check if chain has complete routing from source to destination."""
        operations = {sig.operation for sig in self.signatures}
        return (
            EnumNodeOperation.SOURCE in operations
            and EnumNodeOperation.DESTINATION in operations
        )

    def calculate_trust_score(self, trusted_nodes: set[str]) -> float:
        """Calculate trust score based on trusted node participation.

        Args:
            trusted_nodes: Set of trusted node IDs

        Returns:
            Trust score between 0.0 and 1.0
        """
        if not self.signatures:
            return 0.0
        trusted_signatures = 0
        for signature in self.signatures:
            if signature.node_id in trusted_nodes:
                trusted_signatures += 1
        return trusted_signatures / len(self.signatures)

    def get_routing_path(self) -> list[tuple[str, EnumNodeOperation]]:
        """Get the routing path as list[Any]of (node_id, operation) tuples."""
        return [(str(sig.node_id), sig.operation) for sig in self.signatures]

    def get_chain_summary(self) -> dict[str, str | int | float | bool | list[str]]:
        """Get summary information about the signature chain."""
        operations = [sig.operation for sig in self.signatures]
        algorithms = {sig.signature_algorithm for sig in self.signatures}
        return {
            "chain_id": str(self.chain_id),
            "envelope_id": str(self.envelope_id),
            "signature_count": len(self.signatures),
            "unique_signers": len(self.get_unique_signers()),
            "operations": [op.value for op in operations],
            "algorithms": list[Any](algorithms),
            "has_complete_route": self.has_complete_route(),
            "validation_status": self.validation_status.value,
            "trust_level": self.trust_level.value,
            "created_at": self.created_at.isoformat(),
            "last_modified": self.last_modified.isoformat(),
            "chain_hash": self.chain_hash[:16] + "..." if self.chain_hash else "",
            "compliance_frameworks": [fw.value for fw in self.compliance_frameworks],
        }

    def verify_timestamp_sequence(self) -> bool:
        """Verify signatures have valid timestamp sequence."""
        if len(self.signatures) < 2:
            return True
        for i in range(1, len(self.signatures)):
            prev_time = self.signatures[i - 1].timestamp
            curr_time = self.signatures[i].timestamp
            if curr_time < prev_time - timedelta(seconds=5):
                return False
        return True

    def get_signature_age_stats(self) -> dict[str, str | int | float]:
        """Get statistics about signature ages."""
        if not self.signatures:
            return {}
        now = datetime.now(UTC)
        ages = [(now - sig.timestamp).total_seconds() for sig in self.signatures]
        return {
            "oldest_signature_seconds": max(ages),
            "newest_signature_seconds": min(ages),
            "average_age_seconds": sum(ages) / len(ages),
            "total_routing_time_seconds": max(ages) - min(ages) if len(ages) > 1 else 0,
        }

    def detect_anomalies(self) -> list[str]:
        """Detect potential anomalies in the signature chain."""
        anomalies = []
        signers = [sig.node_id for sig in self.signatures]
        if len(signers) != len(set(signers)):
            anomalies.append("Duplicate signatures from same node detected")
        if not self.verify_timestamp_sequence():
            anomalies.append("Invalid timestamp sequence detected")
        if len(self.signatures) > 20:
            anomalies.append(
                f"Unusually long routing chain: {len(self.signatures)} hops"
            )
        operations = {sig.operation for sig in self.signatures}
        if EnumNodeOperation.SOURCE not in operations:
            anomalies.append("Missing SOURCE operation")
        for i, signature in enumerate(self.signatures):
            if signature.hop_index != i:
                anomalies.append(f"Gap in signature sequence at hop {i}")
        return anomalies

    @classmethod
    def create_new_chain(
        cls,
        envelope_id: UUID,
        content_hash: str,
        signing_policy: ModelSigningPolicy | None = None,
        compliance_frameworks: list[EnumComplianceFramework] | None = None,
    ) -> "ModelSignatureChain":
        """Create a new signature chain for an envelope."""

        return cls(
            chain_id=uuid4(),
            envelope_id=envelope_id,
            content_hash=content_hash,
            signing_policy=signing_policy,
            compliance_frameworks=compliance_frameworks
            if compliance_frameworks is not None
            else [],
            validation_status=EnumChainValidationStatus.INCOMPLETE,
            trust_level=EnumTrustLevel.UNTRUSTED,
        )

    def __str__(self) -> str:
        """Human-readable representation."""
        return f"SignatureChain[{str(self.chain_id)[:8]}] {len(self.signatures)} signatures, status: {self.validation_status.value}"
