"""
Emitter identity model for envelope observability.

The emitter identity captures the component that emitted a message,
used for debugging, tracing, and consumer group derivation. This is
distinct from runtime_id which identifies the gateway that signed
the envelope.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelEmitterIdentity(BaseModel):
    """
    Concrete model implementing ProtocolNodeIdentity for envelope emitter context.

    This captures the identity of the component that emitted the message,
    used for observability, debugging, and consumer group derivation.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    env: str = Field(
        ...,
        min_length=1,
        description="Environment name (must match envelope realm).",
    )

    service: str = Field(
        ...,
        min_length=1,
        description="Service name (e.g., 'omniintelligence').",
    )

    node_name: str = Field(
        ...,
        min_length=1,
        description="Node or handler name.",
    )

    version: str = Field(
        ...,
        min_length=1,
        description="Version string (e.g., 'v1').",
    )


__all__ = ["ModelEmitterIdentity"]
