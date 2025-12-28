"""ONEX-compatible node signature model for cryptographic operations."""

import base64
import hashlib
from datetime import UTC, datetime
from typing import ClassVar, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.constants import TIMEOUT_LONG_MS
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_node_operation import EnumNodeOperation
from omnibase_core.enums.enum_signature_algorithm import EnumSignatureAlgorithm
from omnibase_core.errors import ModelOnexError
from omnibase_core.models.security.model_operation_details import ModelOperationDetails
from omnibase_core.models.security.model_security_summaries import (
    ModelProcessingSummary,
    SignatureOptionalParams,
)
from omnibase_core.models.security.model_signature_metadata import (
    ModelSignatureMetadata,
)


class ModelNodeSignature(BaseModel):
    """
    Cryptographic signature from a single node in the envelope routing chain.

    Provides non-repudiation, tamper detection, and audit trail capabilities
    through PKI-based digital signatures.
    """

    model_config = ConfigDict(
        validate_assignment=True, extra="forbid", from_attributes=True
    )
    MAX_HOP_INDEX: ClassVar[int] = 1000
    MAX_PROCESSING_TIME_MS: ClassVar[int] = TIMEOUT_LONG_MS
    MAX_SIGNATURE_TIME_MS: ClassVar[int] = 60000
    node_id: UUID = Field(
        default=..., description="Unique identifier of the signing node"
    )
    node_name: str | None = Field(
        default=None, description="Human-readable name of the signing node"
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When the signature was created (UTC)",
    )
    signature: str = Field(
        default=..., description="Base64-encoded digital signature", min_length=1
    )
    signature_algorithm: EnumSignatureAlgorithm = Field(
        default=EnumSignatureAlgorithm.RS256,
        description="Cryptographic algorithm used for signing",
    )
    key_id: UUID = Field(
        default=...,
        description="Certificate fingerprint or key identifier",
    )
    certificate_thumbprint: str | None = Field(
        default=None, description="SHA-256 thumbprint of the signing certificate"
    )
    operation: EnumNodeOperation = Field(
        default=..., description="Type of operation performed by this node"
    )
    operation_details: ModelOperationDetails | None = Field(
        default=None, description="Additional details about the operation performed"
    )
    hop_index: int = Field(
        default=...,
        description="Position in the routing chain (0-based)",
        ge=0,
        le=MAX_HOP_INDEX,
    )
    previous_signature_hash: str | None = Field(
        default=None, description="Hash of the previous signature in the chain"
    )
    envelope_state_hash: str = Field(
        default=...,
        description="Hash of envelope state when signature was created",
        min_length=1,
    )
    user_context: str | None = Field(
        default=None,
        description="User ID or service account that initiated the operation",
    )
    security_clearance: str | None = Field(
        default=None, description="Security clearance level required for this operation"
    )
    processing_time_ms: int | None = Field(
        default=None,
        description="Time spent processing the envelope (milliseconds)",
        ge=0,
        le=MAX_PROCESSING_TIME_MS,
    )
    signature_time_ms: int | None = Field(
        default=None,
        description="Time spent creating the signature (milliseconds)",
        ge=0,
        le=MAX_SIGNATURE_TIME_MS,
    )
    error_message: str | None = Field(
        default=None, description="Error message if operation failed"
    )
    warning_messages: list[str] = Field(
        default_factory=list, description="Non-fatal warnings during processing"
    )
    signature_metadata: ModelSignatureMetadata | None = Field(
        default=None, description="Additional signature metadata"
    )

    @field_validator("hop_index")
    @classmethod
    def validate_hop_index(cls, v: int) -> int:
        """Validate hop index is reasonable."""
        if v > cls.MAX_HOP_INDEX:
            raise ModelOnexError(
                message=f"Hop index too large - possible routing loop (max: {cls.MAX_HOP_INDEX})",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                context={"hop_index": v, "max_hop_index": cls.MAX_HOP_INDEX},
            )
        return v

    @field_validator("signature")
    @classmethod
    def validate_signature_format(cls, v: str) -> str:
        """Validate signature is properly base64 encoded."""
        try:
            base64.b64decode(v, validate=True)
        except ValueError as e:
            raise ModelOnexError(
                message=f"Signature must be valid base64 encoding: {e!s}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                context={"signature_preview": v[:20] + "..." if len(v) > 20 else v},
            ) from e
        return v

    @field_validator("envelope_state_hash")
    @classmethod
    def validate_hash_format(cls, v: str) -> str:
        """Validate hash format."""
        if len(v) != 64:
            raise ModelOnexError(
                message="Envelope state hash must be 64 characters (SHA-256)",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                context={"hash_length": len(v), "expected_length": 64},
            )
        try:
            int(v, 16)
        except ValueError as e:
            raise ModelOnexError(
                message="Envelope state hash must be hexadecimal",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                context={"hash_preview": v[:20] + "..." if len(v) > 20 else v},
            ) from e
        return v

    @classmethod
    def create_source_signature(
        cls,
        node_id: UUID,
        signature: str,
        key_id: UUID,
        envelope_state_hash: str,
        user_context: str | None = None,
        **kwargs: SignatureOptionalParams,
    ) -> Self:
        """Create a source signature for envelope origination."""
        return cls(
            node_id=node_id,
            signature=signature,
            key_id=key_id,
            envelope_state_hash=envelope_state_hash,
            operation=EnumNodeOperation.SOURCE,
            hop_index=0,
            user_context=user_context,
            **kwargs,  # type: ignore[arg-type]
        )

    @classmethod
    def create_routing_signature(
        cls,
        node_id: UUID,
        signature: str,
        key_id: UUID,
        envelope_state_hash: str,
        hop_index: int,
        previous_signature_hash: str,
        routing_decision: str,
        **kwargs: SignatureOptionalParams,
    ) -> Self:
        """Create a routing signature for envelope forwarding."""
        if hop_index <= 0:
            raise ModelOnexError(
                message="Routing signature must have hop_index > 0",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                context={"hop_index": hop_index, "operation": "routing"},
            )
        return cls(
            node_id=node_id,
            signature=signature,
            key_id=key_id,
            envelope_state_hash=envelope_state_hash,
            operation=EnumNodeOperation.ROUTE,
            hop_index=hop_index,
            previous_signature_hash=previous_signature_hash,
            operation_details=ModelOperationDetails(routing_decision=routing_decision),
            **kwargs,  # type: ignore[arg-type]
        )

    @classmethod
    def create_destination_signature(
        cls,
        node_id: UUID,
        signature: str,
        key_id: UUID,
        envelope_state_hash: str,
        hop_index: int,
        previous_signature_hash: str,
        delivery_status: str,
        **kwargs: SignatureOptionalParams,
    ) -> Self:
        """Create a destination signature for envelope delivery."""
        if hop_index <= 0:
            raise ModelOnexError(
                message="Destination signature must have hop_index > 0",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                context={"hop_index": hop_index, "operation": "destination"},
            )
        return cls(
            node_id=node_id,
            signature=signature,
            key_id=key_id,
            envelope_state_hash=envelope_state_hash,
            operation=EnumNodeOperation.DESTINATION,
            hop_index=hop_index,
            previous_signature_hash=previous_signature_hash,
            operation_details=ModelOperationDetails(delivery_status=delivery_status),
            **kwargs,  # type: ignore[arg-type]
        )

    def verify_signature_chain_continuity(
        self, previous_signature: Self | None
    ) -> bool:
        """Verify this signature properly continues the chain."""
        if self.hop_index == 0:
            return previous_signature is None and self.previous_signature_hash is None
        if previous_signature is None:
            return False
        if self.hop_index != previous_signature.hop_index + 1:
            return False
        previous_hash = hashlib.sha256(
            previous_signature.signature.encode()
        ).hexdigest()
        return self.previous_signature_hash == previous_hash

    def mark_error(self, error_message: str) -> None:
        """Mark this signature as having an error."""
        self.error_message = error_message

    def add_warning(self, warning_message: str) -> None:
        """Add a warning to this signature."""
        self.warning_messages.append(warning_message)

    def ensure_metadata(self) -> ModelSignatureMetadata:
        """Ensure metadata object exists and return it."""
        if self.signature_metadata is None:
            from omnibase_core.models.primitives.model_semver import ModelSemVer

            self.signature_metadata = ModelSignatureMetadata(
                signature_version=ModelSemVer(major=1, minor=0, patch=0)
            )
        return self.signature_metadata

    def get_signature_hash(self) -> str:
        """Get SHA-256 hash of this signature for chain verification."""
        return hashlib.sha256(self.signature.encode()).hexdigest()

    def is_valid_operation_sequence(
        self, previous_operation: EnumNodeOperation | None
    ) -> bool:
        """Verify this operation is valid given the previous operation."""
        if previous_operation is None:
            return self.operation == EnumNodeOperation.SOURCE
        valid_transitions = {
            EnumNodeOperation.SOURCE: {
                EnumNodeOperation.ROUTE,
                EnumNodeOperation.TRANSFORM,
                EnumNodeOperation.VALIDATE,
                EnumNodeOperation.DESTINATION,
                EnumNodeOperation.AUDIT,
            },
            EnumNodeOperation.ROUTE: {
                EnumNodeOperation.ROUTE,
                EnumNodeOperation.TRANSFORM,
                EnumNodeOperation.VALIDATE,
                EnumNodeOperation.DESTINATION,
                EnumNodeOperation.AUDIT,
            },
            EnumNodeOperation.TRANSFORM: {
                EnumNodeOperation.ROUTE,
                EnumNodeOperation.VALIDATE,
                EnumNodeOperation.DESTINATION,
                EnumNodeOperation.AUDIT,
            },
            EnumNodeOperation.VALIDATE: {
                EnumNodeOperation.ROUTE,
                EnumNodeOperation.DESTINATION,
                EnumNodeOperation.AUDIT,
            },
            EnumNodeOperation.ENCRYPTION: {
                EnumNodeOperation.ROUTE,
                EnumNodeOperation.DESTINATION,
                EnumNodeOperation.AUDIT,
            },
            EnumNodeOperation.AUDIT: {EnumNodeOperation.DESTINATION},
            EnumNodeOperation.DESTINATION: set(),
        }
        return self.operation in valid_transitions.get(previous_operation, set())

    def has_errors(self) -> bool:
        """Check if this signature has errors."""
        return self.error_message is not None

    def has_warnings(self) -> bool:
        """Check if this signature has warnings."""
        return len(self.warning_messages) > 0

    def is_valid(self) -> bool:
        """Check if this signature is valid (no errors)."""
        return not self.has_errors()

    def get_processing_summary(self) -> ModelProcessingSummary:
        """Get a summary of processing information."""
        return ModelProcessingSummary(
            node_id=self.node_id,
            operation=self.operation.value,
            hop_index=self.hop_index,
            timestamp=self.timestamp.isoformat(),
            processing_time_ms=self.processing_time_ms,
            signature_time_ms=self.signature_time_ms,
            has_errors=self.has_errors(),
            has_warnings=self.has_warnings(),
            error_count=len(self.warning_messages),
        )

    def __str__(self) -> str:
        """Human-readable representation."""
        error_info = f" [ERROR: {self.error_message}]" if self.error_message else ""
        warning_info = (
            f" [WARNINGS: {len(self.warning_messages)}]"
            if self.warning_messages
            else ""
        )
        return f"Signature[{self.hop_index}] {self.node_id}:{self.operation.value}{error_info}{warning_info}"
