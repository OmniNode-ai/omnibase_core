"""
Core envelope model for runtime-gateway-centric message routing.

This model wraps all messages with verifiable routing metadata and signatures.
The key design principle is that environment is not a topic prefix - it's a
routing boundary enforced by a runtime acting as a gateway.

Identity Alignment:
    - realm IS the envelope-level equivalent of ProtocolNodeIdentity.env
    - runtime_id is the gateway signer (who signed and enforced policy)
    - emitter_identity is the component identity (who executed logic)

Invariant:
    When emitter_identity is present, emitter_identity.env MUST equal realm.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Generic, TypeVar
from uuid import UUID, uuid4

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from omnibase_core.crypto.crypto_blake3_hasher import hash_canonical_json
from omnibase_core.crypto.crypto_ed25519_signer import sign_base64, verify_base64
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.envelope.model_emitter_identity import ModelEmitterIdentity
from omnibase_core.models.envelope.model_envelope_signature import (
    ModelEnvelopeSignature,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.protocols.crypto.protocol_key_provider import ProtocolKeyProvider
from omnibase_core.protocols.event_bus.protocol_node_identity import (
    ProtocolNodeIdentity,
)

T = TypeVar("T")


class ModelMessageEnvelope(BaseModel, Generic[T]):
    """
    Signed envelope for runtime-gateway-centric message routing.

    This envelope wraps all inter-service messages with:
    - Routing metadata (realm, runtime_id, bus_id)
    - Tracing context (trace_id, causality_id)
    - Cryptographic signature (Blake3 + Ed25519)
    - Optional emitter identity for observability

    Design Principles:
        - realm = routing boundary (same concept as ProtocolNodeIdentity.env)
        - runtime_id = gateway that signed and enforced policy
        - emitter_identity = component that executed logic (optional)
        - Signature is bound to runtime_id, NOT emitter_identity

    Security Warning:
        IMPORTANT: emitter_identity is UNTRUSTED metadata provided for observability
        and debugging purposes only. It is NOT covered by the cryptographic signature
        and can be spoofed by any party with access to the message. NEVER use
        emitter_identity for authorization decisions. For authentication, use
        runtime_id which is cryptographically verified by the signature.

    Attributes:
        realm: Routing boundary identifier (e.g., "dev", "staging", "prod").
        runtime_id: Gateway runtime that signed this envelope.
        bus_id: Message bus identifier for routing.
        trace_id: Distributed tracing ID (OpenTelemetry compatible).
        causality_id: ID of the envelope that caused this one (optional).
        emitted_at: Timestamp when envelope was created (UTC).
        tenant_id: Multi-tenant isolation identifier (optional).
        emitter_identity: Component identity for observability (optional).
        signature: Cryptographic signature over envelope contents.
        payload: The wrapped message payload.

    Example:
        >>> envelope = ModelMessageEnvelope[MyEvent](
        ...     realm="dev",
        ...     runtime_id="runtime-dev-001",
        ...     bus_id="kafka-cluster-a",
        ...     trace_id=uuid4(),
        ...     emitted_at=datetime.now(UTC),
        ...     signature=signature,
        ...     payload=my_event,
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    # Required routing fields
    realm: str = Field(
        ...,
        min_length=1,
        description="Routing boundary identifier (== ProtocolNodeIdentity.env).",
    )

    # string-id-ok: runtime_id is a human-readable gateway identifier like "runtime-dev-001"
    runtime_id: str = Field(
        ...,
        min_length=1,
        description="Gateway runtime that signed this envelope.",
    )

    # string-id-ok: bus_id is a named cluster identifier like "kafka-cluster-a"
    bus_id: str = Field(
        ...,
        min_length=1,
        description="Message bus identifier for routing.",
    )

    trace_id: UUID = Field(
        default_factory=uuid4,
        description="Distributed tracing ID (OpenTelemetry compatible).",
    )

    emitted_at: datetime = Field(
        ...,
        description="Timestamp when envelope was created (UTC, timezone-aware).",
    )

    # Signature (required for trust)
    signature: ModelEnvelopeSignature = Field(
        ...,
        description="Cryptographic signature over envelope contents.",
    )

    # Payload
    payload: T = Field(
        ...,
        description="The wrapped message payload.",
    )

    # Optional fields
    causality_id: UUID | None = Field(
        default=None,
        description="ID of the envelope that caused this one.",
    )

    # string-id-ok: tenant_id is a named tenant identifier, not a UUID
    tenant_id: str | None = Field(
        default=None,
        description="Multi-tenant isolation identifier.",
    )

    emitter_identity: ModelEmitterIdentity | None = Field(
        default=None,
        description="Component identity for observability and consumer group derivation.",
    )

    @field_validator("emitted_at")
    @classmethod
    def validate_emitted_at_timezone_aware(cls, v: datetime) -> datetime:
        """
        Validate that emitted_at is timezone-aware.

        Naive datetimes are ambiguous in distributed systems and can cause
        interoperability issues. All timestamps must be explicitly UTC.
        """
        if v.tzinfo is None:
            msg = "emitted_at must be timezone-aware (use datetime.now(UTC))"
            raise ValueError(msg)  # error-ok: Standard Pydantic validation
        return v

    @model_validator(mode="after")
    def validate_identity_realm_match(self) -> ModelMessageEnvelope[T]:
        """
        Validate that emitter_identity.env matches envelope realm.

        This is a security invariant: if a component claims an identity,
        its environment must match the envelope's routing realm.
        """
        if self.emitter_identity is not None:
            if self.emitter_identity.env != self.realm:
                raise ModelOnexError(
                    message=(
                        f"Identity mismatch: emitter_identity.env='{self.emitter_identity.env}' "
                        f"does not match envelope realm='{self.realm}'"
                    ),
                    error_code=EnumCoreErrorCode.ENVELOPE_IDENTITY_MISMATCH,
                    context={
                        "emitter_env": self.emitter_identity.env,
                        "envelope_realm": self.realm,
                    },
                )
        return self

    @model_validator(mode="after")
    def validate_signer_matches_runtime_id(self) -> ModelMessageEnvelope[T]:
        """
        Validate that signature.signer matches runtime_id.

        This is a security invariant: the signature's claimed signer must match
        the envelope's runtime_id. A mismatch indicates either a configuration
        error or an attempted signature replay attack.
        """
        if self.signature.signer != self.runtime_id:
            raise ModelOnexError(
                message=(
                    f"Signer mismatch: signature.signer='{self.signature.signer}' "
                    f"does not match runtime_id='{self.runtime_id}'"
                ),
                error_code=EnumCoreErrorCode.ENVELOPE_SIGNER_MISMATCH,
                context={
                    "signature_signer": self.signature.signer,
                    "runtime_id": self.runtime_id,
                },
            )
        return self

    @staticmethod
    def _build_signing_dict(
        realm: str,
        runtime_id: str,  # string-id-ok: human-readable gateway identifier
        bus_id: str,  # string-id-ok: named cluster identifier
        trace_id: UUID,
        emitted_at: datetime,
        payload_hash: str,
        causality_id: UUID | None = None,
        tenant_id: str | None = None,  # string-id-ok: named tenant identifier
    ) -> dict[str, str]:
        """
        Build canonical signing dictionary for signature computation.

        This is the single source of truth for which fields are included
        in the cryptographic signature. The dict is JSON-serialized with
        sorted keys for deterministic signing.

        Note: emitter_identity is deliberately excluded as it is untrusted
        observability metadata, not part of the security envelope.
        """
        signing_dict: dict[str, str] = {
            "realm": realm,
            "runtime_id": runtime_id,
            "bus_id": bus_id,
            "trace_id": str(trace_id),
            "emitted_at": emitted_at.isoformat(),
            "payload_hash": payload_hash,
        }
        if causality_id:
            signing_dict["causality_id"] = str(causality_id)
        if tenant_id:
            signing_dict["tenant_id"] = tenant_id
        return signing_dict

    @staticmethod
    def _encode_signing_dict(signing_dict: dict[str, str]) -> bytes:
        """Encode signing dict to canonical JSON bytes for signature operations."""
        return json.dumps(signing_dict, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )

    @staticmethod
    def _compute_payload_hash_for(payload: T) -> str:
        """
        Compute Blake3 hash for any supported payload type.

        This is the single source of truth for payload hash computation,
        used both during envelope creation and verification.

        Payload Handling Strategy:
            - BaseModel: Uses model_dump(mode="json") for deterministic serialization
            - dict: Passed directly to canonical JSON serializer (keys sorted)
            - Other types (str, int, list, etc.): Wrapped in {"value": payload}
              This fallback ensures primitives and lists have a consistent dict
              structure for canonical JSON hashing. The wrapper is intentional
              to maintain hash determinism across all payload types.

        Returns:
            64-character lowercase hex Blake3 hash string.

        Raises:
            TypeError: If payload cannot be JSON serialized (e.g., circular refs).
            ValueError: If serialization produces invalid JSON.
        """
        if isinstance(payload, BaseModel):
            payload_dict = payload.model_dump(mode="json")
        elif isinstance(payload, dict):
            payload_dict = payload
        else:
            # Fallback: wrap primitives/lists in a dict for consistent hashing.
            # This ensures hash determinism for payloads like "hello" or [1, 2, 3].
            payload_dict = {"value": payload}
        return hash_canonical_json(payload_dict)

    def _get_signing_content(self) -> bytes:
        """
        Get the canonical bytes that are signed.

        The signing content includes routing metadata and payload hash,
        but NOT emitter_identity (which is for observability only).
        """
        signing_dict = self._build_signing_dict(
            realm=self.realm,
            runtime_id=self.runtime_id,
            bus_id=self.bus_id,
            trace_id=self.trace_id,
            emitted_at=self.emitted_at,
            payload_hash=self.signature.payload_hash,
            causality_id=self.causality_id,
            tenant_id=self.tenant_id,
        )
        return self._encode_signing_dict(signing_dict)

    def _compute_payload_hash(self) -> str:
        """Compute the Blake3 hash of the current payload."""
        return self._compute_payload_hash_for(self.payload)

    def verify_signature(self, key_provider: ProtocolKeyProvider) -> bool:
        """
        Verify the envelope signature using the key provider.

        This method verifies:
        1. The payload hashes to the stored payload_hash (integrity)
        2. The signature over the metadata is valid (authenticity)

        Args:
            key_provider: Provider for looking up runtime public keys.

        Returns:
            True if signature is valid and payload is intact, False otherwise.

        Raises:
            ModelOnexError: If runtime_id's public key is not found,
                or if payload cannot be serialized for hash verification.

        Security:
            This method fails closed - unknown runtime_id = untrusted.
            Both payload integrity and signature authenticity must pass.
        """
        public_key = key_provider.get_public_key(self.runtime_id)
        if public_key is None:
            raise ModelOnexError(
                message=f"Public key not found for runtime_id='{self.runtime_id}'",
                error_code=EnumCoreErrorCode.ENVELOPE_KEY_NOT_FOUND,
                context={"runtime_id": self.runtime_id},
            )

        # Step 1: Verify payload integrity - hash must match stored hash
        try:
            computed_hash = self._compute_payload_hash()
        except (TypeError, ValueError) as e:
            # Payload is not JSON-serializable (circular refs, custom objects, etc.)
            raise ModelOnexError(
                message=f"Failed to serialize payload for hash verification: {e}",
                error_code=EnumCoreErrorCode.ENVELOPE_PAYLOAD_SERIALIZATION_FAILED,
                context={
                    "payload_type": type(self.payload).__name__,
                    "runtime_id": self.runtime_id,
                },
            ) from e

        if computed_hash != self.signature.payload_hash:
            return False

        # Step 2: Verify signature authenticity
        signing_content = self._get_signing_content()
        return verify_base64(public_key, signing_content, self.signature.signature)

    @classmethod
    def create_signed(
        cls,
        *,
        realm: str,
        runtime_id: str,  # string-id-ok: human-readable gateway identifier
        bus_id: str,  # string-id-ok: named cluster identifier
        payload: T,
        private_key: bytes,
        trace_id: UUID | None = None,
        causality_id: UUID | None = None,
        tenant_id: str | None = None,  # string-id-ok: named tenant identifier
        emitter_identity: ProtocolNodeIdentity | None = None,
        emitted_at: datetime | None = None,
    ) -> ModelMessageEnvelope[T]:
        """
        Create a new signed envelope.

        This is the preferred way to create envelopes as it ensures
        the signature is correctly computed over the envelope contents.

        Args:
            realm: Routing boundary identifier.
            runtime_id: Gateway runtime creating this envelope.
            bus_id: Message bus identifier.
            payload: Message payload to wrap.
            private_key: 32-byte Ed25519 private key for signing.
            trace_id: Optional trace ID (generated if not provided).
            causality_id: Optional causality chain ID.
            tenant_id: Optional tenant identifier.
            emitter_identity: Optional component identity.
            emitted_at: Optional timestamp (now if not provided).

        Returns:
            Signed ModelMessageEnvelope.

        Raises:
            ModelOnexError: If signing fails or identity validation fails.
        """
        # Use provided timestamp or current UTC time
        timestamp = emitted_at or datetime.now(UTC)
        actual_trace_id = trace_id or uuid4()

        # Convert emitter_identity if provided
        emitter_model: ModelEmitterIdentity | None = None
        if emitter_identity is not None:
            emitter_model = ModelEmitterIdentity(
                env=emitter_identity.env,
                service=emitter_identity.service,
                node_name=emitter_identity.node_name,
                version=emitter_identity.version,
            )

        # Compute payload hash using shared helper
        try:
            payload_hash = cls._compute_payload_hash_for(payload)
        except (TypeError, ValueError) as e:
            raise ModelOnexError(
                message=f"Failed to compute payload hash: {e}",
                error_code=EnumCoreErrorCode.ENVELOPE_PAYLOAD_SERIALIZATION_FAILED,
                context={"payload_type": type(payload).__name__},
            ) from e

        # Build signing content using shared helpers
        signing_dict = cls._build_signing_dict(
            realm=realm,
            runtime_id=runtime_id,
            bus_id=bus_id,
            trace_id=actual_trace_id,
            emitted_at=timestamp,
            payload_hash=payload_hash,
            causality_id=causality_id,
            tenant_id=tenant_id,
        )
        signing_content = cls._encode_signing_dict(signing_dict)

        # Sign
        try:
            signature_b64 = sign_base64(private_key, signing_content)
        except Exception as e:
            raise ModelOnexError(
                message=f"Failed to sign envelope: {e}",
                error_code=EnumCoreErrorCode.ENVELOPE_SIGNING_FAILED,
                context={"runtime_id": runtime_id},
            ) from e

        # Create signature model
        signature = ModelEnvelopeSignature(
            algorithm="ed25519",
            signer=runtime_id,
            payload_hash=payload_hash,
            signature=signature_b64,
        )

        # Create and validate envelope
        return cls(
            realm=realm,
            runtime_id=runtime_id,
            bus_id=bus_id,
            trace_id=actual_trace_id,
            emitted_at=timestamp,
            signature=signature,
            payload=payload,
            causality_id=causality_id,
            tenant_id=tenant_id,
            emitter_identity=emitter_model,
        )


__all__ = ["ModelMessageEnvelope"]
