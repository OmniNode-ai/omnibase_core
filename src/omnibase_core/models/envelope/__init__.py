"""
Envelope models for runtime-gateway-centric message routing.

This module provides ModelMessageEnvelope and supporting models
for cryptographically signed message transport with realm-based routing.

Key Concepts:
    - realm: Routing boundary identifier (== ProtocolNodeIdentity.env)
    - runtime_id: Gateway that signed and enforced policy
    - emitter_identity: Component that executed logic (optional, for observability)
"""

from omnibase_core.models.envelope.model_emitter_identity import ModelEmitterIdentity
from omnibase_core.models.envelope.model_envelope_signature import (
    ModelEnvelopeSignature,
)
from omnibase_core.models.envelope.model_message_envelope import ModelMessageEnvelope

__all__ = [
    "ModelEmitterIdentity",
    "ModelEnvelopeSignature",
    "ModelMessageEnvelope",
]
