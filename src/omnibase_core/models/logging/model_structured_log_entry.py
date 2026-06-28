# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelStructuredLogEntry — canonical wire-format model for ONEX log events.

Published to onex.evt.platform.log-entry.v1 (OMN-13703).

Design constraints:
  - frozen, extra="forbid": no silent field additions or mutation
  - No defensive defaults: every required field must be supplied explicitly
  - UUID typed: correlation_id, session_id, node_id are UUIDs or None (not raw str)
  - timestamp is a datetime with timezone, not an ISO string
  - artifact_refs is a list of str artifact IDs (not embedded objects)

Layering: omnibase_core only; omnimarket imports from here.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_log_entry_status import EnumLogEntryStatus
from omnibase_core.enums.enum_log_level import EnumLogLevel
from omnibase_core.enums.enum_redaction_state import EnumRedactionState
from omnibase_core.enums.enum_suppression_decision import EnumSuppressionDecision


class ModelStructuredLogEntry(BaseModel):
    """Canonical wire-format model for onex.evt.platform.log-entry.v1.

    Every field is explicitly required or carries a documented sentinel default.
    No `Any` types; no silent fallbacks.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    # -------------------------------------------------------------------------
    # Identity
    # -------------------------------------------------------------------------
    entry_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for this log entry.",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="UTC timestamp at which the entry was created.",
    )

    # -------------------------------------------------------------------------
    # Provenance
    # -------------------------------------------------------------------------
    source_system: str = Field(
        ...,
        description="The system or subsystem that produced this entry (e.g. node name).",
    )
    operation: str = Field(
        ...,
        description=(
            "The operation or function within source_system that emitted this entry."
        ),
    )
    node_id: UUID | None = Field(
        default=None,
        description="ONEX node UUID that produced this entry, when available.",
    )
    correlation_id: UUID | None = Field(
        default=None,
        description="Cross-boundary correlation identifier for request tracing.",
    )
    session_id: UUID | None = Field(
        default=None,
        description="Session UUID grouping a set of correlated operations.",
    )

    # -------------------------------------------------------------------------
    # Content
    # -------------------------------------------------------------------------
    level: EnumLogLevel = Field(
        ...,
        description="Severity level of this log entry.",
    )
    message: str = Field(
        ...,
        description="Human-readable log message.",
    )

    # -------------------------------------------------------------------------
    # Governance
    # -------------------------------------------------------------------------
    status: EnumLogEntryStatus = Field(
        ...,
        description="Lifecycle status of this entry (emitted/suppressed/redacted/failed).",
    )
    redaction_state: EnumRedactionState = Field(
        ...,
        description="How much of this entry was redacted before publishing.",
    )
    suppression_decision: EnumSuppressionDecision = Field(
        ...,
        description="Suppression ruling applied to this entry.",
    )

    # -------------------------------------------------------------------------
    # References
    # -------------------------------------------------------------------------
    artifact_refs: list[str] = Field(
        default_factory=list,
        description=(
            "Artifact IDs (opaque string references) associated with this log entry."
        ),
    )
    metadata: dict[str, str] = Field(
        default_factory=dict,
        description="Arbitrary key-value string pairs for structured context.",
    )


__all__ = ["ModelStructuredLogEntry"]
