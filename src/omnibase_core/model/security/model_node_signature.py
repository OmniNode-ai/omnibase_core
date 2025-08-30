"""
ModelNodeSignature: Cryptographic signature for envelope audit trails

This model represents a single node's cryptographic signature in the envelope
routing chain, providing non-repudiation and tamper detection capabilities.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, validator

from omnibase_core.model.security.model_operation_details import \
    ModelOperationDetails
from omnibase_core.model.security.model_signature_metadata import \
    ModelSignatureMetadata

logger = logging.getLogger(__name__)


class SignatureAlgorithmEnum(str, Enum):
    """Supported cryptographic signature algorithms."""

    RS256 = "RS256"  # RSA with SHA-256
    RS384 = "RS384"  # RSA with SHA-384
    RS512 = "RS512"  # RSA with SHA-512
    PS256 = "PS256"  # RSA-PSS with SHA-256
    PS384 = "PS384"  # RSA-PSS with SHA-384
    PS512 = "PS512"  # RSA-PSS with SHA-512
    ES256 = "ES256"  # ECDSA with SHA-256
    ES384 = "ES384"  # ECDSA with SHA-384
    ES512 = "ES512"  # ECDSA with SHA-512


@dataclass
class CertificateInfo:
    """Information extracted from an X.509 certificate."""

    certificate_id: str
    subject_dn: str
    issuer_dn: str
    serial_number: str
    not_before: datetime
    not_after: datetime
    public_key_hash: str
    key_usage: list[str]
    extended_key_usage: list[str]


class NodeOperationEnum(str, Enum):
    """Types of operations a node can perform on an envelope."""

    SOURCE = "source"  # Original envelope creation
    ROUTE = "route"  # Routing decision and forwarding
    TRANSFORM = "transform"  # Data transformation or enrichment
    VALIDATE = "validate"  # Validation or compliance checking
    DESTINATION = "destination"  # Final delivery and processing
    ENCRYPTION = "encryption"  # Payload encryption/decryption
    AUDIT = "audit"  # Audit logging and compliance


class ModelNodeSignature(BaseModel):
    """
    Cryptographic signature from a single node in the envelope routing chain.

    Provides non-repudiation, tamper detection, and audit trail capabilities
    through PKI-based digital signatures.
    """

    # Node identification
    node_id: str = Field(
        ..., description="Unique identifier of the signing node", min_length=1
    )
    node_name: Optional[str] = Field(
        None, description="Human-readable name of the signing node"
    )

    # Signature metadata
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the signature was created (UTC)",
    )
    signature: str = Field(
        ..., description="Base64-encoded digital signature", min_length=1
    )

    # Cryptographic details
    signature_algorithm: SignatureAlgorithmEnum = Field(
        default=SignatureAlgorithmEnum.RS256,
        description="Cryptographic algorithm used for signing",
    )
    key_id: str = Field(
        ..., description="Certificate fingerprint or key identifier", min_length=1
    )
    certificate_thumbprint: Optional[str] = Field(
        None, description="SHA-256 thumbprint of the signing certificate"
    )

    # Operation context
    operation: NodeOperationEnum = Field(
        ..., description="Type of operation performed by this node"
    )
    operation_details: Optional[ModelOperationDetails] = Field(
        None,
        description="Additional details about the operation performed",
    )

    # Audit and compliance
    hop_index: int = Field(
        ..., description="Position in the routing chain (0-based)", ge=0
    )
    previous_signature_hash: Optional[str] = Field(
        None, description="Hash of the previous signature in the chain"
    )
    envelope_state_hash: str = Field(
        ...,
        description="Hash of envelope state when signature was created",
        min_length=1,
    )

    # Security context
    user_context: Optional[str] = Field(
        None, description="User ID or service account that initiated the operation"
    )
    security_clearance: Optional[str] = Field(
        None, description="Security clearance level required for this operation"
    )

    # Performance and debugging
    processing_time_ms: Optional[int] = Field(
        None, description="Time spent processing the envelope (milliseconds)", ge=0
    )
    signature_time_ms: Optional[int] = Field(
        None, description="Time spent creating the signature (milliseconds)", ge=0
    )

    # Error handling
    error_message: Optional[str] = Field(
        None, description="Error message if operation failed"
    )
    warning_messages: list[str] = Field(
        default_factory=list, description="Non-fatal warnings during processing"
    )

    # Additional metadata
    signature_metadata: Optional[ModelSignatureMetadata] = Field(
        None, description="Additional signature metadata"
    )

    @validator("hop_index")
    def validate_hop_index(cls, v):
        """Validate hop index is reasonable."""
        if v > 1000:  # Sanity check for routing loops
            raise ValueError("Hop index too large - possible routing loop")
        return v

    @validator("signature")
    def validate_signature_format(cls, v):
        """Validate signature is properly base64 encoded."""
        import base64

        try:
            base64.b64decode(v, validate=True)
        except Exception as e:
            # Log the specific base64 decoding error
            logger.error(
                f"Invalid base64 signature format: {str(e)}",
                extra={"signature_preview": v[:20] + "..." if len(v) > 20 else v},
            )
            raise ValueError(f"Signature must be valid base64 encoding: {str(e)}")
        return v

    @classmethod
    def create_source_signature(
        cls,
        node_id: str,
        signature: str,
        key_id: str,
        envelope_state_hash: str,
        user_context: Optional[str] = None,
        **kwargs,
    ) -> "ModelNodeSignature":
        """Create a source signature for envelope origination."""
        return cls(
            node_id=node_id,
            signature=signature,
            key_id=key_id,
            envelope_state_hash=envelope_state_hash,
            operation=NodeOperationEnum.SOURCE,
            hop_index=0,
            user_context=user_context,
            **kwargs,
        )

    @classmethod
    def create_routing_signature(
        cls,
        node_id: str,
        signature: str,
        key_id: str,
        envelope_state_hash: str,
        hop_index: int,
        previous_signature_hash: str,
        routing_decision: str,
        **kwargs,
    ) -> "ModelNodeSignature":
        """Create a routing signature for envelope forwarding."""
        return cls(
            node_id=node_id,
            signature=signature,
            key_id=key_id,
            envelope_state_hash=envelope_state_hash,
            operation=NodeOperationEnum.ROUTE,
            hop_index=hop_index,
            previous_signature_hash=previous_signature_hash,
            operation_details=ModelOperationDetails(routing_decision=routing_decision),
            **kwargs,
        )

    @classmethod
    def create_destination_signature(
        cls,
        node_id: str,
        signature: str,
        key_id: str,
        envelope_state_hash: str,
        hop_index: int,
        previous_signature_hash: str,
        delivery_status: str,
        **kwargs,
    ) -> "ModelNodeSignature":
        """Create a destination signature for envelope delivery."""
        return cls(
            node_id=node_id,
            signature=signature,
            key_id=key_id,
            envelope_state_hash=envelope_state_hash,
            operation=NodeOperationEnum.DESTINATION,
            hop_index=hop_index,
            previous_signature_hash=previous_signature_hash,
            operation_details=ModelOperationDetails(delivery_status=delivery_status),
            **kwargs,
        )

    def verify_signature_chain_continuity(
        self, previous_signature: Optional["ModelNodeSignature"]
    ) -> bool:
        """Verify this signature properly continues the chain."""
        if self.hop_index == 0:
            # Source signature should not have previous signature
            return previous_signature is None and self.previous_signature_hash is None

        if previous_signature is None:
            return False

        # Verify hop index sequence
        if self.hop_index != previous_signature.hop_index + 1:
            return False

        # Verify hash chain continuity
        import hashlib

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
            self.signature_metadata = ModelSignatureMetadata()
        return self.signature_metadata

    def get_signature_hash(self) -> str:
        """Get SHA-256 hash of this signature for chain verification."""
        import hashlib

        return hashlib.sha256(self.signature.encode()).hexdigest()

    def is_valid_operation_sequence(
        self, previous_operation: Optional[NodeOperationEnum]
    ) -> bool:
        """Verify this operation is valid given the previous operation."""
        if previous_operation is None:
            return self.operation == NodeOperationEnum.SOURCE

        # Define valid operation transitions
        valid_transitions = {
            NodeOperationEnum.SOURCE: {
                NodeOperationEnum.ROUTE,
                NodeOperationEnum.TRANSFORM,
                NodeOperationEnum.VALIDATE,
                NodeOperationEnum.DESTINATION,
                NodeOperationEnum.AUDIT,
            },
            NodeOperationEnum.ROUTE: {
                NodeOperationEnum.ROUTE,
                NodeOperationEnum.TRANSFORM,
                NodeOperationEnum.VALIDATE,
                NodeOperationEnum.DESTINATION,
                NodeOperationEnum.AUDIT,
            },
            NodeOperationEnum.TRANSFORM: {
                NodeOperationEnum.ROUTE,
                NodeOperationEnum.VALIDATE,
                NodeOperationEnum.DESTINATION,
                NodeOperationEnum.AUDIT,
            },
            NodeOperationEnum.VALIDATE: {
                NodeOperationEnum.ROUTE,
                NodeOperationEnum.DESTINATION,
                NodeOperationEnum.AUDIT,
            },
            NodeOperationEnum.ENCRYPTION: {
                NodeOperationEnum.ROUTE,
                NodeOperationEnum.DESTINATION,
                NodeOperationEnum.AUDIT,
            },
            NodeOperationEnum.AUDIT: {NodeOperationEnum.DESTINATION},
            NodeOperationEnum.DESTINATION: set(),  # Terminal operation
        }

        return self.operation in valid_transitions.get(previous_operation, set())

    def __str__(self) -> str:
        """Human-readable representation."""
        error_info = f" [ERROR: {self.error_message}]" if self.error_message else ""
        return f"Signature[{self.hop_index}] {self.node_id}:{self.operation.value}{error_info}"
