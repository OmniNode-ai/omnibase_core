# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Minimal shared transport envelope for cross-repo event compatibility.

Migrated from omnibase_compat.models.event_envelope (OMN-12188).
Canonical location is now omnibase_core.models.events.model_event_envelope_v1_minimal.
"""

from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.utils.util_decorators import allow_dict_str_any


@allow_dict_str_any(
    "payload is an open-schema wire transport field for cross-repo event compatibility; "
    "schema is intentionally untyped to decouple producer and consumer schemas"
)
class ModelEventEnvelopeV1Minimal(BaseModel):
    """Minimal shared transport envelope for cross-repo event compatibility.

    Intentionally narrow. Does not include timestamp, source, trace_id,
    correlation_id, or category. Add those in a versioned successor or
    additive minor release once real usage patterns are established.

    For a full-featured envelope with tracing, QoS, and security context,
    use ModelEventEnvelope[T] from omnibase_core.models.events.model_event_envelope.
    """

    model_config = ConfigDict(frozen=True)

    event_id: UUID = Field(default_factory=uuid4)
    event_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    # string-version-ok: wire schema guard for cross-repo transport compatibility
    schema_version: str = "1.0"
    data_provenance: str | None = Field(
        default=None,
        description=(
            "Data provenance label. Expected values: "
            '"demo_seeded", "demo_projected_shortcut", "measured", "estimated", "unknown". '
            "Uses str (not enum) to preserve cross-repo wire compatibility."
        ),
    )


EventEnvelopeV1Minimal = ModelEventEnvelopeV1Minimal


__all__: list[str] = ["EventEnvelopeV1Minimal", "ModelEventEnvelopeV1Minimal"]
