"""Secure Event Envelope Model.

Cryptographically signed event envelope with enterprise security features.

This module provides the ModelSecureEventEnvelope class which extends the base
event envelope with digital signatures, PKI certificates, trust policies,
encrypted payloads, and compliance metadata for secure multi-hop routing in
enterprise environments.

Security Notes:
    **Key Management Best Practices**

    The encryption methods in this module use password-based key derivation
    (PBKDF2-HMAC-SHA256). While PBKDF2 provides strong protection against
    brute-force attacks, the security of encrypted payloads ultimately depends
    on proper key management practices:

    1. **Use Secure Key Management Systems**: Store encryption keys in dedicated
       secret management solutions such as:

       - HashiCorp Vault (recommended for on-premises and hybrid deployments)
       - AWS KMS (for AWS-native workloads)
       - Azure Key Vault (for Azure-native workloads)
       - Google Cloud KMS (for GCP-native workloads)

    2. **Never Hardcode Keys**: Encryption keys must never appear in:

       - Source code or version control systems
       - Configuration files (even if encrypted)
       - Container images or deployment artifacts
       - Log files or error messages

    3. **Production Key Handling**: For production deployments:

       - Use environment variables injected at runtime by orchestration tools
       - Integrate with secrets management (e.g., Kubernetes Secrets with
         external-secrets-operator, Docker secrets)
       - Consider using ModelSecretManager from this package for unified
         secret access across backends

    4. **Key Rotation**: Implement regular key rotation practices:

       - Rotate encryption keys on a defined schedule (e.g., quarterly)
       - Maintain key version metadata in ModelEncryptionMetadata.key_id
       - Support decryption with previous key versions during rotation periods
       - Audit key access and usage patterns

    5. **Access Control**: Restrict key access using:

       - Role-based access control (RBAC) for key management operations
       - Principle of least privilege for service accounts
       - Separate keys for different environments (dev, staging, production)
       - Audit logging for all key access events

Example:
    >>> # Production-ready encryption using environment-sourced keys
    >>> import os
    >>> from uuid import uuid4
    >>> encryption_key = os.environ["ENVELOPE_ENCRYPTION_KEY"]  # From secret manager
    >>> envelope = ModelSecureEventEnvelope.create_secure_encrypted(
    ...     payload=event,
    ...     destination="node-b",
    ...     source_node_id=uuid4(),
    ...     encryption_key=encryption_key,
    ... )

See Also:
    ModelSecretManager: For unified secret access across multiple backends.
    ModelEncryptionMetadata: For cryptographic metadata storage.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from pydantic import ConfigDict, Field, field_serializer, field_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_security_event_status import EnumSecurityEventStatus
from omnibase_core.enums.enum_security_event_type import EnumSecurityEventType
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.core.model_onex_event import ModelOnexEvent
from omnibase_core.models.core.model_route_spec import ModelRouteSpec
from omnibase_core.models.core.model_trust_level import ModelTrustLevel
from omnibase_core.models.errors.model_onex_error import ModelOnexError

# Import base envelope and security models
from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope
from omnibase_core.models.security.model_policy_context import ModelPolicyContext
from omnibase_core.models.security.model_security_context import ModelSecurityContext
from omnibase_core.models.security.model_security_event import ModelSecurityEvent
from omnibase_core.models.security.model_security_summary import ModelSecuritySummary

from .model_chain_metrics import ModelChainMetrics
from .model_compliance_metadata import ModelComplianceMetadata
from .model_encryption_metadata import ModelEncryptionMetadata
from .model_node_signature import ModelNodeSignature
from .model_signature_chain import ModelSignatureChain
from .model_trust_policy import ModelTrustPolicy

if TYPE_CHECKING:
    from omnibase_core.models.security.model_signature_verification_result import (
        ModelSignatureVerificationResult,
    )


class ModelSecureEventEnvelope(ModelEventEnvelope[ModelOnexEvent]):
    """
    Cryptographically signed event envelope with enterprise security features.

    Extends the base event envelope with digital signatures, PKI certificates,
    trust policies, encrypted payloads, and compliance metadata for secure
    multi-hop routing in enterprise environments.
    """

    # Routing specification
    route_spec: ModelRouteSpec = Field(
        default=...,
        description="Routing specification for the envelope",
    )

    # Source node tracking
    source_node_id: UUID = Field(
        default=...,
        description="Source node UUID for the envelope",
    )

    # Routing hops tracking
    route_hops: list[ModelSchemaValue] = Field(
        default_factory=list,
        description="List of routing hops for audit trail (type-safe)",
    )

    @field_validator("route_hops", mode="before")
    @classmethod
    def convert_route_hops_to_schema(
        cls, v: list[Any] | list[ModelSchemaValue] | None
    ) -> list[ModelSchemaValue]:
        """Convert values to ModelSchemaValue for type safety."""
        if not v:
            return []
        # Homogeneous list assumption: if first element is ModelSchemaValue,
        # all elements are (lists come from single serialization source).
        # If already ModelSchemaValue instances, return as-is
        # Note: len(v) > 0 check removed - guaranteed non-empty after early return
        if isinstance(v[0], ModelSchemaValue):
            return v
        # Convert raw values to ModelSchemaValue
        return [ModelSchemaValue.from_value(item) for item in v]

    # Enhanced security context (override parent's dict type)
    security_context: ModelSecurityContext | None = Field(
        default=None,
        description="Enhanced security context with JWT and RBAC",
    )

    # Cryptographic signature chain
    signature_chain: ModelSignatureChain = Field(
        default_factory=lambda: ModelSignatureChain(
            chain_id=UUID(
                "00000000-0000-0000-0000-000000000000"
            ),  # Temp UUID, will be updated after envelope creation
            envelope_id=UUID(
                "00000000-0000-0000-0000-000000000000"
            ),  # Temp UUID, will be updated after envelope creation
            content_hash="initial",  # Will be calculated from envelope content
            signing_policy=None,
            chain_metrics=ModelChainMetrics(
                chain_build_time_ms=0.0, cache_hit_rate=0.0
            ),
        ),
        description="Cryptographic signature chain for audit trail",
    )

    # Trust and policy enforcement
    trust_policy: ModelTrustPolicy | None = Field(
        default=None,
        description="Trust policy governing signature requirements",
    )
    required_trust_level: ModelTrustLevel = Field(
        default_factory=lambda: ModelTrustLevel(
            trust_score=0.5,
            trust_category="medium",
            display_name="Standard",
            last_verified=None,
            expires_at=None,
            issuer=None,
            renewal_period_days=None,
        ),
        description="Required trust level for this envelope",
    )

    # Encryption support
    is_encrypted: bool = Field(
        default=False,
        description="Whether payload is encrypted",
    )
    encryption_metadata: ModelEncryptionMetadata | None = Field(
        default=None,
        description="Encryption details if payload is encrypted",
    )
    encrypted_payload: str | None = Field(
        default=None,
        description="Base64-encoded encrypted payload",
    )

    # Compliance and regulatory
    compliance_metadata: ModelComplianceMetadata = Field(
        default_factory=lambda: ModelComplianceMetadata(
            retention_period_days=365, jurisdiction="US"
        ),
        description="Compliance and regulatory metadata",
    )

    # Security clearance and access control
    security_clearance_required: str | None = Field(
        default=None,
        description="Required security clearance level",
    )
    authorized_roles: list[str] = Field(
        default_factory=list,
        description="Roles authorized to process this envelope",
    )
    authorized_nodes: set[UUID] = Field(
        default_factory=set,
        description="Specific nodes authorized to process envelope",
    )

    # Tamper detection
    content_hash: str = Field(
        default=...,
        description="Hash of envelope content for tamper detection",
    )
    signature_required: bool = Field(
        default=True,
        description="Whether signatures are required",
    )
    minimum_signatures: int = Field(
        default=1,
        description="Minimum required signatures",
    )

    # Security audit trail
    security_events: list[ModelSecurityEvent] = Field(
        default_factory=list,
        description="Security events and audit trail",
    )

    # Performance and timeout settings
    signature_timeout_ms: int = Field(
        default=15000,
        description="Maximum time allowed for signature operations",
    )
    encryption_timeout_ms: int = Field(
        default=10000,
        description="Maximum time allowed for encryption operations",
    )

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("envelope_timestamp")
    def serialize_envelope_timestamp(self, value: datetime) -> str:
        """Serialize datetime to ISO format."""
        return value.isoformat()

    def __init__(self, **data: Any):
        """Initialize secure envelope with proper signature chain setup."""
        super().__init__(**data)

        # Update signature chain with actual envelope ID
        temp_uuid = UUID("00000000-0000-0000-0000-000000000000")
        if self.signature_chain.envelope_id == temp_uuid:
            # envelope_id is already a UUID, no need to wrap it
            self.signature_chain.envelope_id = self.envelope_id

        # Initialize content hash
        if not hasattr(self, "content_hash") or not self.content_hash:
            self._update_content_hash()

    @field_validator("minimum_signatures")
    @classmethod
    def validate_minimum_signatures(cls, v: int) -> int:
        """Validate minimum signature count."""
        if v < 0:
            raise ModelOnexError(
                message="Minimum signatures cannot be negative",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                context={"minimum_signatures": v, "min_allowed": 0},
            )
        if v > 50:
            raise ModelOnexError(
                message="Minimum signatures cannot exceed 50",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                context={"minimum_signatures": v, "max_allowed": 50},
            )
        return v

    @property
    def current_hop_count(self) -> int:
        """Get the current hop count based on route_hops."""
        return len(self.route_hops)

    def add_source_hop(self, hop_identifier: str) -> None:
        """
        Add a source hop to the routing trail.

        Args:
            hop_identifier: String identifier for the hop (typically a node ID)
        """
        self.route_hops.append(ModelSchemaValue.from_value(hop_identifier))

    def _update_content_hash(self) -> None:
        """Update content hash for tamper detection.

        When the envelope is encrypted, the hash is calculated using a sentinel
        value for the payload field rather than the actual payload content. This
        ensures consistent hash computation regardless of whether the plaintext
        payload has been cleared after encryption.

        Security Note:
            For encrypted envelopes, the encrypted_payload and AAD (Additional
            Authenticated Data) provide cryptographic binding to envelope identity.
            The content hash serves as an additional tamper-detection mechanism
            but does not depend on the plaintext payload state after encryption.
        """
        # For encrypted envelopes, use a sentinel for payload to ensure consistent
        # hashing regardless of whether plaintext has been cleared.
        # The encrypted_payload provides cryptographic integrity via AES-GCM.
        # ONEX_EXCLUDE: dict_str_any - hash computation from model_dump serialization
        payload_for_hash: dict[str, Any] | str
        if self.is_encrypted and self.encrypted_payload:
            payload_for_hash = "[ENCRYPTED_PAYLOAD]"
        else:
            payload_for_hash = (
                self.payload.model_dump()
                if hasattr(self.payload, "model_dump")
                else str(self.payload)
            )

        # ONEX_EXCLUDE: dict_str_any - hash computation from model_dump serialization
        hash_input: dict[str, Any] = {
            "envelope_id": self.envelope_id,
            "payload": payload_for_hash,
            "route_spec": self.route_spec.model_dump(),
            "source_node_id": self.source_node_id,
            "created_at": self.envelope_timestamp.isoformat(),
            "security_context": (
                self.security_context.model_dump() if self.security_context else None
            ),
            "compliance_metadata": self.compliance_metadata.model_dump(),
        }

        # Include encrypted payload if present
        if self.is_encrypted and self.encrypted_payload:
            hash_input["encrypted_payload"] = self.encrypted_payload

        # Calculate SHA-256 hash
        content_str = str(hash_input).encode("utf-8")
        self.content_hash = hashlib.sha256(content_str).hexdigest()

    def _create_encryption_aad(self) -> bytes:
        """Create Additional Authenticated Data (AAD) for AES-GCM encryption.

        AAD binds the ciphertext to this specific envelope's identity, preventing
        ciphertext transplantation attacks where encrypted data from one envelope
        is moved to another envelope.

        The AAD includes:
        - envelope_id: Unique identifier for this envelope
        - source_node_id: Origin node that created this envelope
        - envelope_timestamp: When the envelope was created

        Returns:
            bytes: Concatenated AAD suitable for AESGCM encrypt/decrypt
        """
        # Create deterministic AAD from envelope identity fields
        # These fields should never change after envelope creation
        aad_components = [
            str(self.envelope_id),
            str(self.source_node_id),
            self.envelope_timestamp.isoformat(),
        ]
        aad_string = "|".join(aad_components)
        return aad_string.encode("utf-8")

    def _create_redacted_payload(self) -> ModelOnexEvent:
        """Create a redacted placeholder payload for use after encryption.

        Creates a minimal ModelOnexEvent that indicates the original payload
        has been encrypted. This placeholder prevents accidental exposure of
        sensitive data while maintaining structural integrity of the envelope.

        Returns:
            ModelOnexEvent: A placeholder event with redacted content.

        Security Note:
            The redacted payload contains no sensitive information from the
            original event. It uses a special event_type to clearly indicate
            that the actual data is available only through decryption.
        """
        return ModelOnexEvent(
            event_type="core.security.payload_redacted",
            node_id=self.source_node_id,
            timestamp=self.envelope_timestamp,
            event_id=self.envelope_id,
        )

    def clear_plaintext(self) -> None:
        """Clear the plaintext payload after encryption for defense in depth.

        Replaces the plaintext payload field with a redacted placeholder to
        prevent accidental leakage of sensitive data. This should be called
        after encryption when the plaintext is no longer needed.

        Security Rationale:
            After encryption, both the plaintext (payload) and ciphertext
            (encrypted_payload) coexist in the envelope. This creates risks:

            1. **Accidental Serialization**: Serializing the envelope (e.g.,
               for logging, network transfer, or storage) could expose both
               plaintext and ciphertext.

            2. **Memory Exposure**: The plaintext remains in memory longer
               than necessary, increasing the window for memory-based attacks.

            3. **Defense in Depth**: Even if other security measures fail,
               clearing the plaintext ensures sensitive data is not exposed
               in the envelope's readable payload field.

        Raises:
            ModelOnexError: With INVALID_OPERATION code if the envelope
                is not encrypted (clearing plaintext only makes sense
                after encryption).

        Side Effects:
            - Replaces self.payload with a redacted placeholder
            - Logs a TOOL_ACCESS security event for audit trail
            - Does NOT affect the encrypted_payload or content_hash

        Example:
            >>> envelope.encrypt_payload("secret-key")
            >>> envelope.clear_plaintext()
            >>> envelope.payload.event_type
            'core.security.payload_redacted'
            >>> # Original data is still accessible via decryption
            >>> decrypted = envelope.decrypt_payload("secret-key")
            >>> decrypted.event_type
            'original.event.type'

        Note:
            This operation is irreversible on the envelope. To access the
            original payload data, use decrypt_payload() which retrieves
            the data from the encrypted_payload field.

        See Also:
            encrypt_payload: Encrypts the payload (can auto-clear plaintext).
            decrypt_payload: Decrypts and returns the original payload.
        """
        if not self.is_encrypted:
            raise ModelOnexError(
                message="Cannot clear plaintext: envelope is not encrypted. "
                "Clearing plaintext only makes sense after encryption.",
                error_code=EnumCoreErrorCode.INVALID_OPERATION,
                context={
                    "operation": "clear_plaintext",
                    "envelope_id": str(self.envelope_id),
                    "is_encrypted": self.is_encrypted,
                },
            )

        # Replace payload with redacted placeholder
        self.payload = self._create_redacted_payload()

        # Log security event for audit trail
        # Using TOOL_ACCESS event type with reason field to track this security action
        self.log_security_event(
            EnumSecurityEventType.TOOL_ACCESS,
            reason="defense_in_depth",
        )

    @property
    def is_plaintext_cleared(self) -> bool:
        """Check if the plaintext payload has been cleared after encryption.

        Returns:
            bool: True if the payload contains the redacted placeholder,
                False if it contains the original (or any non-redacted) payload.

        Note:
            This property checks if the payload's event_type matches the
            redacted placeholder type. It does not verify whether the
            envelope is encrypted.
        """
        return (
            hasattr(self.payload, "event_type")
            and self.payload.event_type == "core.security.payload_redacted"
        )

    def validate_content_integrity(self) -> bool:
        """Validate envelope content hasn't been tampered with."""
        current_hash = self.content_hash
        self._update_content_hash()
        is_valid = current_hash == self.content_hash

        if not is_valid:
            self.log_security_event(
                EnumSecurityEventType.SECURITY_VIOLATION,
                expected_hash=current_hash,
                actual_hash=self.content_hash,
            )

        return is_valid

    def add_signature(self, signature: ModelNodeSignature) -> None:
        """Add a cryptographic signature to the envelope."""
        # Validate signature is for this envelope
        # Note: ModelNodeSignature doesn't have envelope_version, so this check is removed
        # TODO(OMN-TBD): Consider adding envelope_version to ModelNodeSignature if needed  [NEEDS TICKET]

        # Update content hash before signing
        self._update_content_hash()

        # Ensure signature includes current content hash
        if signature.envelope_state_hash != self.content_hash:
            raise ModelOnexError(
                message="Cannot add signature: envelope state hash mismatch. "
                "The signature was created for a different envelope state. "
                "Regenerate the signature with the current envelope content.",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                context={
                    "operation": "add_signature",
                    "envelope_id": str(self.envelope_id),
                    "expected_hash": self.content_hash[:16] + "...",
                    "signature_hash": signature.envelope_state_hash[:16] + "...",
                },
            )

        # Add to signature chain
        self.signature_chain.add_signature(signature)

        # Log security event
        self.log_security_event(
            EnumSecurityEventType.TOOL_ACCESS,
            signature_key_id=signature.key_id,
            node_id=signature.node_id,
            algorithm=signature.signature_algorithm.value,
        )

    def verify_signatures(
        self,
        trusted_nodes: set[str] | None = None,
    ) -> ModelSignatureVerificationResult:
        """Verify all signatures in the chain."""
        from omnibase_core.models.security.model_chain_validation import (
            ModelChainValidation,
        )
        from omnibase_core.models.security.model_policy_validation import (
            ModelPolicyValidation,
        )
        from omnibase_core.models.security.model_signature_verification_result import (
            ModelSignatureVerificationResult,
        )

        # Default status for no signatures
        if not self.signature_chain.signatures:
            chain_summary = self.signature_chain.get_chain_summary()
            return ModelSignatureVerificationResult(
                status="no_signatures",
                verified=False,
                signature_count=0,
                verified_signatures=0,
                chain_validation=ModelChainValidation(
                    chain_id=UUID(str(chain_summary["chain_id"])),
                    envelope_id=UUID(str(chain_summary["envelope_id"])),
                    signature_count=0,
                    unique_signers=0,
                    operations=[],
                    algorithms=[],
                    has_complete_route=False,
                    validation_status="no_signatures",
                    trust_level="untrusted",
                    created_at=str(chain_summary["created_at"]),
                    last_modified=str(chain_summary["last_modified"]),
                    chain_hash="",
                    compliance_frameworks=[],
                ),
                policy_validation=None,
                verified_at=datetime.now(UTC).isoformat(),
            )

        # Validate content integrity first
        if not self.validate_content_integrity():
            chain_summary = self.signature_chain.get_chain_summary()
            return ModelSignatureVerificationResult(
                status="tampered",
                verified=False,
                signature_count=len(self.signature_chain.signatures),
                verified_signatures=0,
                chain_validation=ModelChainValidation(
                    chain_id=UUID(str(chain_summary["chain_id"])),
                    envelope_id=UUID(str(chain_summary["envelope_id"])),
                    signature_count=(
                        int(chain_summary["signature_count"])
                        if isinstance(chain_summary["signature_count"], int)
                        else 0
                    ),
                    unique_signers=(
                        int(chain_summary["unique_signers"])
                        if isinstance(chain_summary["unique_signers"], int)
                        else 0
                    ),
                    operations=(
                        chain_summary["operations"]
                        if isinstance(chain_summary["operations"], list)
                        else []
                    ),
                    algorithms=(
                        chain_summary["algorithms"]
                        if isinstance(chain_summary["algorithms"], list)
                        else []
                    ),
                    has_complete_route=bool(chain_summary["has_complete_route"]),
                    validation_status=str(chain_summary["validation_status"]),
                    trust_level=str(chain_summary["trust_level"]),
                    created_at=str(chain_summary["created_at"]),
                    last_modified=str(chain_summary["last_modified"]),
                    chain_hash=str(chain_summary["chain_hash"]),
                    compliance_frameworks=(
                        chain_summary["compliance_frameworks"]
                        if isinstance(chain_summary["compliance_frameworks"], list)
                        else []
                    ),
                ),
                policy_validation=None,
                verified_at=datetime.now(UTC).isoformat(),
            )

        # Validate signature chain
        chain_status = self.signature_chain.validate_chain_integrity()
        chain_summary = self.signature_chain.get_chain_summary()
        verified_signatures = getattr(self.signature_chain, "verified_signatures", 0)

        # Apply trust policy if present
        policy_validation = None
        if self.trust_policy:
            policy_result = self.trust_policy.validate_signature_chain(
                self.signature_chain,
                context=None,  # ModelRuleCondition expected, not ModelPolicyContext
            )
            if policy_result:
                policy_validation = ModelPolicyValidation(
                    policy_id=self.trust_policy.policy_id,
                    policy_name=self.trust_policy.name,
                    is_valid=policy_result.status == "compliant",
                    violations=policy_result.violations,
                    warnings=policy_result.warnings,
                )

        result = ModelSignatureVerificationResult(
            status="valid" if chain_status else "invalid",
            verified=chain_status,
            signature_count=len(self.signature_chain.signatures),
            verified_signatures=verified_signatures,
            chain_validation=ModelChainValidation(
                chain_id=UUID(str(chain_summary["chain_id"])),
                envelope_id=UUID(str(chain_summary["envelope_id"])),
                signature_count=(
                    int(chain_summary["signature_count"])
                    if isinstance(chain_summary["signature_count"], int)
                    else 0
                ),
                unique_signers=(
                    int(chain_summary["unique_signers"])
                    if isinstance(chain_summary["unique_signers"], int)
                    else 0
                ),
                operations=(
                    chain_summary["operations"]
                    if isinstance(chain_summary["operations"], list)
                    else []
                ),
                algorithms=(
                    chain_summary["algorithms"]
                    if isinstance(chain_summary["algorithms"], list)
                    else []
                ),
                has_complete_route=bool(chain_summary["has_complete_route"]),
                validation_status=str(chain_summary["validation_status"]),
                trust_level=str(chain_summary["trust_level"]),
                created_at=str(chain_summary["created_at"]),
                last_modified=str(chain_summary["last_modified"]),
                chain_hash=str(chain_summary["chain_hash"]),
                compliance_frameworks=(
                    chain_summary["compliance_frameworks"]
                    if isinstance(chain_summary["compliance_frameworks"], list)
                    else []
                ),
            ),
            policy_validation=policy_validation,
            verified_at=datetime.now(UTC).isoformat(),
        )

        # Log verification event
        self.log_security_event(
            EnumSecurityEventType.AUTHENTICATION_SUCCESS,
            status=result.status,
            verified=result.verified,
            signature_count=result.signature_count,
            verified_signatures=result.verified_signatures,
        )

        return result

    def _get_policy_context(self) -> ModelPolicyContext:
        """Get context for policy evaluation."""
        # Create base context with UUID types where required
        context = ModelPolicyContext(
            envelope_id=self.envelope_id,
            source_node_id=self.source_node_id,
            current_hop_count=self.current_hop_count,
            operation_type="routing",
            is_encrypted=self.is_encrypted,
            frameworks=self.compliance_metadata.frameworks,
            classification=self.compliance_metadata.classification,
            retention_period_days=self.compliance_metadata.retention_period_days,
            jurisdiction=self.compliance_metadata.jurisdiction,
            consent_required=self.compliance_metadata.consent_required,
            audit_level=self.compliance_metadata.audit_level,
            contains_pii=self.compliance_metadata.contains_pii,
            contains_phi=self.compliance_metadata.contains_phi,
            contains_financial=self.compliance_metadata.contains_financial,
            export_controlled=self.compliance_metadata.export_controlled,
            user_id=None,  # Required field
            security_clearance=None,  # Required field
            trust_level=None,  # Required field
        )

        if self.security_context:
            # Keep user_id as UUID for policy context
            context.user_id = self.security_context.user_id
            context.roles = self.security_context.roles
            context.security_clearance = self.security_clearance_required
            context.trust_level = self.security_context.trust_level

        return context

    def encrypt_payload(
        self,
        encryption_key: str,
        algorithm: str = "AES-256-GCM",
        clear_plaintext_after_encryption: bool = True,
    ) -> None:
        """Encrypt the envelope payload using AES-256-GCM authenticated encryption.

        Encrypts the event payload using industry-standard AES-256-GCM (Galois/Counter
        Mode) with PBKDF2 key derivation. This provides both confidentiality and
        authenticity guarantees.

        Security Features:
            - **Key Derivation**: PBKDF2-HMAC-SHA256 with 600,000 iterations
              (OWASP 2023 guidelines) derives a 256-bit key from the password.
            - **Random Salt**: A fresh UUID is generated as salt for each encryption,
              stored in encryption_metadata.key_id.
            - **Random IV**: A cryptographically random 12-byte initialization vector
              is generated per encryption for semantic security.
            - **Authentication**: AES-GCM provides a 128-bit authentication tag that
              detects any tampering with the ciphertext.
            - **AAD Binding**: Additional Authenticated Data (AAD) binds the
              ciphertext to this envelope's identity (envelope_id, source_node_id,
              timestamp) to prevent ciphertext transplantation attacks.
            - **Plaintext Clearing**: By default, the plaintext payload is replaced
              with a redacted placeholder after encryption to prevent accidental
              leakage (defense in depth).

        Args:
            encryption_key: Password or key string for encryption. This is processed
                through PBKDF2 to derive the actual encryption key. Should be a
                strong secret with sufficient entropy.
            algorithm: Encryption algorithm to use. Currently only "AES-256-GCM"
                is supported. Defaults to "AES-256-GCM".
            clear_plaintext_after_encryption: If True (default), replaces the
                plaintext payload with a redacted placeholder after encryption.
                This prevents accidental exposure of sensitive data through
                serialization, logging, or memory inspection. Set to False only
                if you have a specific need to retain the plaintext (not
                recommended for production use).

        Raises:
            ModelOnexError: With VALIDATION_ERROR code if:
                - The payload is already encrypted (is_encrypted is True)
                - An unsupported algorithm is specified

        Side Effects:
            - Sets is_encrypted to True
            - Populates encrypted_payload with base64-encoded ciphertext
            - Populates encryption_metadata with cryptographic parameters
            - Updates content_hash to reflect the encrypted state
            - If clear_plaintext_after_encryption is True (default):
              - Replaces payload with a redacted placeholder
              - Logs a security event for the plaintext clearing

        Example:
            >>> envelope = ModelSecureEventEnvelope.create_secure_direct(
            ...     payload=event,
            ...     destination="node-b",
            ...     source_node_id=source_id,
            ... )
            >>> envelope.encrypt_payload("my-secret-key")
            >>> envelope.is_encrypted
            True
            >>> envelope.is_plaintext_cleared
            True
            >>> envelope.payload.event_type
            'core.security.payload_redacted'
            >>> # Original data is preserved in encrypted_payload
            >>> decrypted = envelope.decrypt_payload("my-secret-key")
            >>> decrypted.event_type
            'original.event.type'

        Note:
            The same encryption_key must be provided to decrypt_payload() to
            successfully decrypt the data. Store this key securely.

        See Also:
            decrypt_payload: To decrypt an encrypted payload.
            clear_plaintext: To manually clear plaintext after encryption.
            create_secure_encrypted: Factory method that creates and encrypts in one step.
        """
        if self.is_encrypted:
            raise ModelOnexError(
                message="Cannot encrypt: payload is already encrypted. Decrypt first if re-encryption is needed.",
                error_code=EnumCoreErrorCode.INVALID_OPERATION,
                context={
                    "operation": "encrypt_payload",
                    "envelope_id": str(self.envelope_id),
                    "is_encrypted": self.is_encrypted,
                },
            )

        if algorithm != "AES-256-GCM":
            raise ModelOnexError(
                message=f"Cannot encrypt: unsupported algorithm '{algorithm}'. Use 'AES-256-GCM' instead.",
                error_code=EnumCoreErrorCode.UNSUPPORTED_OPERATION,
                context={
                    "operation": "encrypt_payload",
                    "envelope_id": str(self.envelope_id),
                    "requested_algorithm": algorithm,
                    "supported_algorithms": ["AES-256-GCM"],
                },
            )

        # Generate random key_id (used as salt for key derivation)
        key_id = uuid4()
        salt = key_id.bytes  # 16 bytes from UUID

        # Derive 32-byte key using PBKDF2 with SHA-256
        # OWASP recommends 600,000+ iterations for PBKDF2-SHA256 (2023 guidelines)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=600000,
        )
        derived_key = kdf.derive(encryption_key.encode("utf-8"))

        # Generate random 12-byte IV (standard for GCM)
        iv = os.urandom(12)

        # Serialize payload to JSON
        payload_json = json.dumps(
            self.payload.model_dump(mode="json"), ensure_ascii=False
        )
        plaintext = payload_json.encode("utf-8")

        # Create Additional Authenticated Data (AAD) from envelope metadata
        # AAD binds ciphertext to this specific envelope, preventing transplantation
        # attacks where ciphertext from one envelope is moved to another
        aad = self._create_encryption_aad()

        # Encrypt using AES-256-GCM with AAD
        # AESGCM automatically appends the 16-byte auth tag to ciphertext
        aesgcm = AESGCM(derived_key)
        ciphertext_with_tag = aesgcm.encrypt(iv, plaintext, aad)

        # Extract auth tag (last 16 bytes) for metadata storage
        auth_tag = ciphertext_with_tag[-16:]

        # Store encrypted data as base64 (includes auth tag)
        self.encrypted_payload = base64.b64encode(ciphertext_with_tag).decode("utf-8")

        # Create encryption metadata with AAD hash for verification
        aad_hash = hashlib.sha256(aad).hexdigest()
        self.encryption_metadata = ModelEncryptionMetadata(
            algorithm=algorithm,
            key_id=key_id,
            iv=base64.b64encode(iv).decode("utf-8"),
            auth_tag=base64.b64encode(auth_tag).decode("utf-8"),
            aad_hash=aad_hash,
        )

        # Mark as encrypted
        self.is_encrypted = True

        # Update content hash after encryption
        self._update_content_hash()

        # Clear plaintext for defense in depth (default behavior)
        if clear_plaintext_after_encryption:
            self.clear_plaintext()

    def decrypt_payload(self, decryption_key: str) -> ModelOnexEvent:
        """Decrypt the envelope payload using AES-256-GCM authenticated decryption.

        Decrypts an encrypted payload, verifying authenticity via the GCM
        authentication tag and AAD binding. This method reverses the encryption
        performed by encrypt_payload().

        Security Verification:
            - **Key Derivation**: Derives the same 256-bit key using PBKDF2
              with the stored salt (key_id).
            - **AAD Verification**: Verifies the AAD hash matches the stored
              value, detecting ciphertext transplantation attacks.
            - **Authentication**: GCM mode verifies the 128-bit auth tag,
              detecting any tampering with the ciphertext or AAD.
            - **Secure Failure**: Raises SECURITY_VIOLATION on any authentication
              failure, preventing timing attacks.

        Args:
            decryption_key: Password or key string for decryption. Must be the
                same value that was passed to encrypt_payload(). The key is
                processed through PBKDF2 to derive the actual decryption key.

        Returns:
            ModelOnexEvent: The decrypted and validated event payload,
                reconstructed from the JSON-serialized plaintext.

        Raises:
            ModelOnexError: With VALIDATION_ERROR code if:
                - The payload is not encrypted (is_encrypted is False)
                - Missing encrypted_payload or encryption_metadata
                - Unsupported encryption algorithm in metadata
                - Failed to parse decrypted JSON payload
            ModelOnexError: With SECURITY_VIOLATION code if:
                - AAD hash mismatch (envelope metadata was modified)
                - Authentication tag verification failed (wrong key or
                  ciphertext tampering)

        Example:
            >>> # First encrypt a payload
            >>> envelope.encrypt_payload("my-secret-key")
            >>> envelope.is_encrypted
            True
            >>> # Then decrypt it
            >>> decrypted_event = envelope.decrypt_payload("my-secret-key")
            >>> decrypted_event.event_type
            'my_event_type'

        Note:
            This method does NOT modify the envelope state. The envelope
            remains encrypted after calling this method. To work with the
            decrypted payload, use the returned ModelOnexEvent.

        See Also:
            encrypt_payload: To encrypt a payload.
            _create_encryption_aad: For AAD binding details.
        """
        if not self.is_encrypted:
            raise ModelOnexError(
                message="Cannot decrypt: envelope payload is not encrypted.",
                error_code=EnumCoreErrorCode.INVALID_OPERATION,
                context={
                    "operation": "decrypt_payload",
                    "envelope_id": str(self.envelope_id),
                    "is_encrypted": self.is_encrypted,
                },
            )

        if not self.encrypted_payload or not self.encryption_metadata:
            missing_fields = []
            if not self.encrypted_payload:
                missing_fields.append("encrypted_payload")
            if not self.encryption_metadata:
                missing_fields.append("encryption_metadata")
            raise ModelOnexError(
                message=f"Cannot decrypt: missing required encryption data ({', '.join(missing_fields)}). "
                "The envelope may be corrupted or was not properly encrypted.",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                context={
                    "operation": "decrypt_payload",
                    "envelope_id": str(self.envelope_id),
                    "has_encrypted_payload": bool(self.encrypted_payload),
                    "has_encryption_metadata": bool(self.encryption_metadata),
                    "missing_fields": missing_fields,
                },
            )

        if self.encryption_metadata.algorithm != "AES-256-GCM":
            raise ModelOnexError(
                message=f"Cannot decrypt: unsupported algorithm '{self.encryption_metadata.algorithm}'. "
                "Only 'AES-256-GCM' is supported for decryption.",
                error_code=EnumCoreErrorCode.UNSUPPORTED_OPERATION,
                context={
                    "operation": "decrypt_payload",
                    "envelope_id": str(self.envelope_id),
                    "algorithm": self.encryption_metadata.algorithm,
                    "supported_algorithms": ["AES-256-GCM"],
                },
            )

        # Use key_id bytes as salt (same as encryption)
        salt = self.encryption_metadata.key_id.bytes

        # Derive key using same PBKDF2 method
        # Must match encryption iteration count (600,000 per OWASP guidelines)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=600000,
        )
        derived_key = kdf.derive(decryption_key.encode("utf-8"))

        # Decode base64 encrypted payload and IV
        ciphertext_with_tag = base64.b64decode(self.encrypted_payload)
        iv = base64.b64decode(self.encryption_metadata.iv)

        # Recreate AAD from envelope metadata for authenticated decryption
        # AAD must match exactly what was used during encryption
        aad = self._create_encryption_aad()

        # Verify AAD hash matches stored hash (if available) for extra validation
        if self.encryption_metadata.aad_hash:
            current_aad_hash = hashlib.sha256(aad).hexdigest()
            if not hmac.compare_digest(
                current_aad_hash, self.encryption_metadata.aad_hash
            ):
                raise ModelOnexError(
                    message="Cannot decrypt: envelope metadata has been modified after encryption "
                    "(AAD hash mismatch indicates possible ciphertext transplantation attack).",
                    error_code=EnumCoreErrorCode.SECURITY_VIOLATION,
                    context={
                        "operation": "decrypt_payload",
                        "envelope_id": str(self.envelope_id),
                        "expected_aad_hash": self.encryption_metadata.aad_hash[:16]
                        + "...",
                        "actual_aad_hash": current_aad_hash[:16] + "...",
                    },
                )

        # Decrypt using AESGCM with AAD (authentication is automatic - raises InvalidTag on failure)
        aesgcm = AESGCM(derived_key)
        try:
            plaintext = aesgcm.decrypt(iv, ciphertext_with_tag, aad)
        except InvalidTag as e:
            raise ModelOnexError(
                message="Cannot decrypt: authentication tag verification failed. "
                "This indicates wrong decryption key, tampered ciphertext, or modified envelope metadata.",
                error_code=EnumCoreErrorCode.SECURITY_VIOLATION,
                context={
                    "operation": "decrypt_payload",
                    "envelope_id": str(self.envelope_id),
                    "algorithm": self.encryption_metadata.algorithm,
                    "possible_causes": [
                        "incorrect decryption key",
                        "ciphertext has been tampered with",
                        "envelope metadata was modified after encryption",
                    ],
                },
            ) from e

        # Parse JSON back to ModelOnexEvent
        try:
            payload_dict = json.loads(plaintext.decode("utf-8"))
            return ModelOnexEvent.model_validate(payload_dict)
        except (json.JSONDecodeError, ValueError) as e:
            raise ModelOnexError(
                message=f"Cannot decrypt: decrypted data is not valid JSON or does not match "
                f"ModelOnexEvent schema ({type(e).__name__}: {e}).",
                error_code=EnumCoreErrorCode.PARSING_ERROR,
                context={
                    "operation": "decrypt_payload",
                    "envelope_id": str(self.envelope_id),
                    "error_type": type(e).__name__,
                    "error_details": str(e),
                },
            ) from e

    def check_authorization(
        self,
        node_id: UUID,
        user_context: ModelSecurityContext | None = None,
    ) -> bool:
        """Check if node/user is authorized to process this envelope."""
        # Check node authorization
        if self.authorized_nodes and node_id not in self.authorized_nodes:
            self.log_security_event(
                EnumSecurityEventType.AUTHORIZATION_FAILED,
                node_id=node_id,
                reason="node_not_authorized",
            )
            return False

        # Check role-based authorization
        if user_context and self.authorized_roles:
            user_roles = user_context.roles
            if not any(role in self.authorized_roles for role in user_roles):
                self.log_security_event(
                    EnumSecurityEventType.AUTHORIZATION_FAILED,
                    node_id=node_id,
                    user_roles=user_roles,
                    required_roles=self.authorized_roles,
                    reason="insufficient_roles",
                )
                return False

        # Check security clearance
        if self.security_clearance_required and user_context:
            user_clearance = user_context.trust_level
            if not user_clearance or str(user_clearance) < str(
                self.security_clearance_required,
            ):
                self.log_security_event(
                    EnumSecurityEventType.AUTHORIZATION_FAILED,
                    node_id=node_id,
                    user_clearance=user_clearance,
                    required_clearance=self.security_clearance_required,
                    reason="insufficient_clearance",
                )
                return False

        return True

    def log_security_event(
        self, event_type: EnumSecurityEventType, **kwargs: Any
    ) -> None:
        """Log a security event for audit trail."""
        event = ModelSecurityEvent(
            event_id=uuid4(),
            event_type=event_type,
            timestamp=datetime.now(UTC),
            envelope_id=self.envelope_id,
            status=EnumSecurityEventStatus.SUCCESS,  # Required field
            **kwargs,
        )
        self.security_events.append(event)

    def get_security_summary(self) -> ModelSecuritySummary:
        """Get comprehensive security summary for reporting."""
        from omnibase_core.models.security.model_security_summary import (
            ModelAuthorizationSummary,
            ModelComplianceSummary,
            ModelSecurityEventSummary,
            ModelSignatureChainSummary,
        )

        chain_summary = self.signature_chain.get_chain_summary()

        # Create last security event summary if exists
        last_event_summary = None
        if self.security_events:
            last_event = self.security_events[-1]
            last_event_summary = ModelSecurityEventSummary(
                event_id=last_event.event_id,
                event_type=last_event.event_type,
                timestamp=last_event.timestamp.isoformat(),
                envelope_id=last_event.envelope_id,
            )

        return ModelSecuritySummary(
            envelope_id=self.envelope_id,
            security_level=self.required_trust_level.trust_category,
            is_encrypted=self.is_encrypted,
            signature_required=self.signature_required,
            content_hash=self.content_hash,
            signature_chain=ModelSignatureChainSummary(
                chain_id=UUID(str(chain_summary["chain_id"])),
                envelope_id=UUID(str(chain_summary["envelope_id"])),
                signature_count=(
                    int(chain_summary["signature_count"])
                    if isinstance(chain_summary["signature_count"], int)
                    else 0
                ),
                unique_signers=(
                    int(chain_summary["unique_signers"])
                    if isinstance(chain_summary["unique_signers"], int)
                    else 0
                ),
                operations=(
                    chain_summary["operations"]
                    if isinstance(chain_summary["operations"], list)
                    else []
                ),
                algorithms=(
                    chain_summary["algorithms"]
                    if isinstance(chain_summary["algorithms"], list)
                    else []
                ),
                has_complete_route=bool(chain_summary["has_complete_route"]),
                validation_status=str(chain_summary["validation_status"]),
                trust_level=str(chain_summary["trust_level"]),
                created_at=str(chain_summary["created_at"]),
                last_modified=str(chain_summary["last_modified"]),
                chain_hash=str(chain_summary["chain_hash"]),
                compliance_frameworks=(
                    chain_summary["compliance_frameworks"]
                    if isinstance(chain_summary["compliance_frameworks"], list)
                    else []
                ),
            ),
            compliance=ModelComplianceSummary(
                frameworks=self.compliance_metadata.frameworks,
                classification=self.compliance_metadata.classification,
                contains_pii=self.compliance_metadata.contains_pii,
                contains_phi=self.compliance_metadata.contains_phi,
                contains_financial=self.compliance_metadata.contains_financial,
            ),
            authorization=ModelAuthorizationSummary(
                authorized_roles=self.authorized_roles,
                authorized_nodes=list[Any](self.authorized_nodes),
                security_clearance_required=self.security_clearance_required,
            ),
            security_events_count=len(self.security_events),
            last_security_event=last_event_summary,
        )

    @classmethod
    def create_secure_direct(
        cls,
        payload: ModelOnexEvent,
        destination: str,
        source_node_id: UUID,
        security_context: ModelSecurityContext | None = None,
        trust_policy: ModelTrustPolicy | None = None,
        **kwargs: Any,
    ) -> ModelSecureEventEnvelope:
        """Create secure envelope for direct routing."""
        # Create base envelope
        route_spec = ModelRouteSpec.create_direct_route(destination)

        envelope = cls(
            payload=payload,
            route_spec=route_spec,
            source_node_id=source_node_id,
            security_context=security_context,
            trust_policy=trust_policy,
            **kwargs,
        )

        # Add source hop to trace
        envelope.add_source_hop(str(source_node_id))

        return envelope

    @classmethod
    def create_secure_encrypted(
        cls,
        payload: ModelOnexEvent,
        destination: str,
        source_node_id: UUID,
        encryption_key: str,
        security_context: ModelSecurityContext | None = None,
        trust_policy: ModelTrustPolicy | None = None,
        **kwargs: Any,
    ) -> ModelSecureEventEnvelope:
        """Create secure envelope with encrypted payload."""
        envelope = cls.create_secure_direct(
            payload,
            destination,
            source_node_id,
            security_context,
            trust_policy,
            **kwargs,
        )

        # Encrypt the payload
        envelope.encrypt_payload(encryption_key)

        return envelope

    def __str__(self) -> str:
        """Human-readable representation."""
        security_info = []

        if self.is_encrypted:
            security_info.append("encrypted")

        if self.signature_chain.signatures:
            security_info.append(f"{len(self.signature_chain.signatures)} sigs")

        if self.required_trust_level.trust_category != "medium":
            security_info.append(f"trust:{self.required_trust_level.trust_category}")

        security_str = f" [{', '.join(security_info)}]" if security_info else ""

        return super().__str__() + security_str
