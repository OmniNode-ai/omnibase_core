from typing import Any
from uuid import UUID

from pydantic import Field

from omnibase_core.enums.enum_chain_validation_status import EnumChainValidationStatus
from omnibase_core.enums.enum_compliance_framework import EnumComplianceFramework
from omnibase_core.enums.enum_trust_level import EnumTrustLevel
from omnibase_core.errors.model_onex_error import ModelOnexError

"""
ModelSignatureChain: Tamper-evident signature chain for secure envelopes

This model manages a collection of cryptographic signatures from multiple nodes,
providing comprehensive audit trails and tamper detection for event routing.
"""

import hashlib
import json
import logging
from datetime import datetime, timedelta
from enum import Enum

from pydantic import BaseModel, Field, validator

from omnibase_core.errors.error_codes import EnumCoreErrorCode
from omnibase_core.models.security.model_chain_metrics import ModelChainMetrics
from omnibase_core.enums.enum_node_operation import EnumNodeOperation
from omnibase_core.models.security.model_node_signature import ModelNodeSignature
from omnibase_core.models.security.model_signing_policy import ModelSigningPolicy

logger = logging.getLogger(__name__)


class ModelSignatureChain(BaseModel):
    """
    Tamper-evident signature chain for secure envelope routing.

    Manages an ordered collection of cryptographic signatures from nodes
    that have processed an envelope, providing comprehensive audit trails
    and tamper detection capabilities.
    """

    # Chain identification
    chain_id: UUID = Field(
        default=...,
        description="Unique identifier for this signature chain",
        min_length=1,
    )
    envelope_id: UUID = Field(
        default=...,
        description="ID of the envelope this chain belongs to",
        min_length=1,
    )

    # Signature collection
    signatures: list[ModelNodeSignature] = Field(
        default_factory=list,
        description="Ordered list[Any]of signatures in the chain",
    )

    # Chain metadata
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the chain was created (UTC)",
    )
    last_modified: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the chain was last modified (UTC)",
    )

    # Chain integrity
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

    # Trust and validation
    validation_status: EnumChainValidationStatus = Field(
        default=EnumChainValidationStatus.INCOMPLETE,
        description="Current validation status of the chain",
    )
    trust_level: EnumTrustLevel = Field(
        default=EnumTrustLevel.UNTRUSTED,
        description="Overall trust level of the chain",
    )

    # Policy compliance
    signing_policy: ModelSigningPolicy | None = Field(
        default=None,
        description="Signing policy requirements for this chain",
    )
    compliance_frameworks: list[EnumComplianceFramework] = Field(
        default_factory=list,
        description="Compliance frameworks this chain must satisfy",
    )

    # Performance and debugging
    chain_metrics: ModelChainMetrics | None = Field(
        default=None,
        description="Performance metrics for chain operations",
    )

    @validator("signatures")
    def validate_signature_order(self, v: Any) -> Any:
        """Validate signatures are in correct hop order."""
        if not v:
            return v

        for i, signature in enumerate(v):
            if signature.hop_index != i:
                msg = f"Signature at position {i} has hop_index {signature.hop_index}"
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=msg,
                )

        return v

    def add_signature(
        self,
        signature: ModelNodeSignature,
        validate_chain: bool = True,
    ) -> bool:
        """Add a new signature to the chain.

        Args:
            signature: Signature to add
            validate_chain: Whether to validate chain integrity after adding

        Returns:
            True if signature was successfully added
        """
        try:
            # Validate signature can be added
            if not self._can_add_signature(signature):
                return False

            # Set correct hop index
            signature.hop_index = len(self.signatures)

            # Set previous signature hash if not first signature
            if self.signatures:
                previous_signature = self.signatures[-1]
                signature.previous_signature_hash = (
                    previous_signature.get_signature_hash()
                )

            # Add signature to chain
            self.signatures.append(signature)
            self.last_modified = datetime.utcnow()

            # Update chain hash
            self._update_chain_hash()

            # Validate chain if requested
            if validate_chain:
                self.validate_chain_integrity()

            return True

        except ModelOnexError:
            # Re-raise ModelOnexError for proper error handling
            raise
        except Exception as e:
            # Log the error and fail fast
            logger.exception(
                f"Failed to add signature to chain {self.chain_id}: {e!s}",
                extra={
                    "chain_id": self.chain_id,
                    "signature_node_id": signature.node_id,
                },
            )
            msg = f"Failed to add signature to chain: {e!s}"
            raise ModelOnexError(
                msg,
                error_code=EnumCoreErrorCode.SECURITY_VIOLATION,
                component="signature_chain",
                operation="add_signature",
            )

    def _can_add_signature(self, signature: ModelNodeSignature) -> bool:
        """Check if signature can be added to the chain."""
        # Check if node already signed
        existing_signers = {sig.node_id for sig in self.signatures}
        if signature.node_id in existing_signers:
            return False

        # Check operation sequence validity
        if self.signatures:
            last_operation = self.signatures[-1].operation
            if not signature.is_valid_operation_sequence(last_operation):
                return False
        # First signature must be SOURCE
        elif signature.operation != EnumNodeOperation.SOURCE:
            return False

        # Check content hash matches
        return signature.envelope_state_hash == self.content_hash

    def _update_chain_hash(self) -> None:
        """Update the chain hash based on current signatures."""
        if not self.signatures:
            self.chain_hash = ""
            return

        # Create deterministic representation of chain
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

        # Calculate hash
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

            # Validate signature continuity
            for i, signature in enumerate(self.signatures):
                # Check hop index
                if signature.hop_index != i:
                    self.validation_status = EnumChainValidationStatus.INVALID
                    return False

                # Check previous signature hash
                if i == 0:
                    # First signature should not have previous hash
                    if signature.previous_signature_hash is not None:
                        self.validation_status = EnumChainValidationStatus.INVALID
                        return False
                else:
                    # Subsequent signatures must link to previous
                    previous_signature = self.signatures[i - 1]
                    expected_hash = previous_signature.get_signature_hash()

                    if signature.previous_signature_hash != expected_hash:
                        self.validation_status = EnumChainValidationStatus.TAMPERED
                        return False

                # Validate operation sequence
                previous_operation = self.signatures[i - 1].operation if i > 0 else None
                if not signature.is_valid_operation_sequence(previous_operation):
                    self.validation_status = EnumChainValidationStatus.INVALID
                    return False

            # Check signing policy compliance
            if not self._validate_signing_policy():
                self.validation_status = EnumChainValidationStatus.INCOMPLETE
                return False

            # All validations passed
            self.validation_status = EnumChainValidationStatus.VALID
            return True

        except ModelOnexError:
            # Re-raise ModelOnexError for proper error handling
            raise
        except Exception as e:
            # Log the error and fail fast
            logger.exception(
                f"Chain integrity validation failed for chain {self.chain_id}: {e!s}",
                extra={
                    "chain_id": self.chain_id,
                    "signatures_count": len(self.signatures),
                },
            )
            self.validation_status = EnumChainValidationStatus.INVALID
            msg = f"Chain integrity validation failed: {e!s}"
            raise ModelOnexError(
                msg,
                error_code=EnumCoreErrorCode.SECURITY_VIOLATION,
                component="signature_chain",
                operation="validate_chain_integrity",
            )

    def _validate_signing_policy(self) -> bool:
        """Validate chain meets signing policy requirements."""
        if not self.signing_policy:
            return True  # No policy to validate against

        policy = self.signing_policy

        # Check minimum signatures
        if len(self.signatures) < policy.minimum_signatures:
            return False

        # Check required operations
        chain_operations = {sig.operation.value for sig in self.signatures}
        for required_op in policy.required_operations:
            if required_op not in chain_operations:
                return False

        # Check trusted node requirements
        trusted_count = len(
            [sig for sig in self.signatures if sig.node_id in policy.trusted_nodes],
        )

        return not trusted_count < policy.minimum_trusted_signatures

    def get_unique_signers(self) -> set[str]:
        """Get set of unique node IDs that signed this chain."""
        return {signature.node_id for signature in self.signatures}

    def get_signature_by_node(self, node_id: str) -> ModelNodeSignature | None:
        """Get signature from specific node."""
        for signature in self.signatures:
            if signature.node_id == node_id:
                return signature
        return None

    def get_signatures_by_operation(
        self,
        operation: EnumNodeOperation,
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
        return [(sig.node_id, sig.operation) for sig in self.signatures]

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

            # Current signature must be after previous (allow 5 second clock skew)
            if curr_time < prev_time - timedelta(seconds=5):
                return False

        return True

    def get_signature_age_stats(self) -> dict[str, str | int | float]:
        """Get statistics about signature ages."""
        if not self.signatures:
            return {}

        now = datetime.utcnow()
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

        # Check for duplicate nodes
        signers = [sig.node_id for sig in self.signatures]
        if len(signers) != len(set(signers)):
            anomalies.append("Duplicate signatures from same node detected")

        # Check for timestamp anomalies
        if not self.verify_timestamp_sequence():
            anomalies.append("Invalid timestamp sequence detected")

        # Check for suspicious routing loops
        if len(self.signatures) > 20:  # Configurable threshold
            anomalies.append(
                f"Unusually long routing chain: {len(self.signatures)} hops",
            )

        # Check for missing required operations
        operations = {sig.operation for sig in self.signatures}
        if EnumNodeOperation.SOURCE not in operations:
            anomalies.append("Missing SOURCE operation")

        # Check for signature gaps
        for i, signature in enumerate(self.signatures):
            if signature.hop_index != i:
                anomalies.append(f"Gap in signature sequence at hop {i}")

        return anomalies

    @classmethod
    def create_new_chain(
        cls,
        envelope_id: str | UUID,
        content_hash: str,
        signing_policy: ModelSigningPolicy | None = None,
        compliance_frameworks: list[EnumComplianceFramework] | None = None,
    ) -> "ModelSignatureChain":
        """Create a new signature chain for an envelope."""
        import uuid

        return cls(
            chain_id=uuid.uuid4(),  # UUID object, not string
            envelope_id=(
                UUID(envelope_id) if isinstance(envelope_id, str) else envelope_id
            ),
            content_hash=content_hash,
            signing_policy=signing_policy,
            compliance_frameworks=compliance_frameworks or [],
            validation_status=EnumChainValidationStatus.INCOMPLETE,
            trust_level=EnumTrustLevel.UNTRUSTED,
        )

    def __str__(self) -> str:
        """Human-readable representation."""
        return (
            f"SignatureChain[{str(self.chain_id)[:8]}] "
            f"{len(self.signatures)} signatures, "
            f"status: {self.validation_status.value}"
        )
