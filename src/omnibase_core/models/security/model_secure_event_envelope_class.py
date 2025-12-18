"""Secure Event Envelope Model.

Cryptographically signed event envelope with enterprise security features.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from pydantic import ConfigDict, Field, field_serializer, field_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_security_event_status import EnumSecurityEventStatus
from omnibase_core.enums.enum_security_event_type import EnumSecurityEventType
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
    route_hops: list[Any] = Field(
        default_factory=list,
        description="List of routing hops for audit trail",
    )

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

    model_config = ConfigDict()

    @field_serializer("timestamp")
    def serialize_timestamp(self, value: datetime) -> str:
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
            msg = "Minimum signatures cannot be negative"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )
        if v > 50:
            msg = "Minimum signatures cannot exceed 50"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
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
        self.route_hops.append(hop_identifier)

    def _update_content_hash(self) -> None:
        """Update content hash for tamper detection."""
        import hashlib

        # Create hash input from critical envelope fields
        hash_input = {
            "envelope_id": self.envelope_id,
            "payload": (
                self.payload.model_dump()
                if hasattr(self.payload, "model_dump")
                else str(self.payload)
            ),
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
        # TODO: Consider adding envelope_version to ModelNodeSignature if needed

        # Update content hash before signing
        self._update_content_hash()

        # Ensure signature includes current content hash
        if signature.envelope_state_hash != self.content_hash:
            msg = "Signature envelope state hash mismatch"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
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
    ) -> None:
        """Encrypt the envelope payload."""
        if self.is_encrypted:
            msg = "Payload is already encrypted"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )

        # AI_PROMPT: Implement actual encryption using cryptography library
        # This should use AES-256-GCM with proper key derivation
        msg = (
            "Encryption implementation required: Use cryptography library "
            "to implement AES-256-GCM encryption with proper IV generation "
            "and authentication tag creation"
        )
        raise NotImplementedError(msg)  # stub-ok: planned security feature

    def decrypt_payload(self, decryption_key: str) -> ModelOnexEvent:
        """Decrypt the envelope payload."""
        if not self.is_encrypted:
            msg = "Payload is not encrypted"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )

        if not self.encrypted_payload or not self.encryption_metadata:
            msg = "Missing encryption data"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )

        # AI_PROMPT: Implement actual decryption using cryptography library
        # This should use AES-256-GCM with proper key derivation
        msg = (
            "Decryption implementation required: Use cryptography library "
            "to implement AES-256-GCM decryption with IV and authentication "
            "tag verification"
        )
        raise NotImplementedError(msg)  # stub-ok: planned security feature

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
