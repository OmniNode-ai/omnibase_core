# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""ModelDelegationRequest: wire envelope for Claude Code hook delegation (OMN-10609)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_redaction_policy import EnumRedactionPolicy
from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelDelegationRequest(BaseModel):
    """Envelope emitted by a Claude Code hook when delegating tool execution.

    Carries enough context for the delegation pipeline to route, audit, and
    replay the request without re-reading the original hook payload.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    envelope_id: UUID = Field(default_factory=uuid4)
    correlation_id: UUID = Field(default_factory=uuid4)
    causation_id: UUID
    # string-id-ok: Claude Code session IDs are opaque strings, not UUIDs
    session_id: str
    # string-id-ok: Claude Code tool_use_id is "toolu_01..." not a UUID
    tool_use_id: str
    hook_name: str
    tool_name: str
    # String rather than EnumTaskType to avoid a cross-repo import into omnibase_core.
    task_type: str
    input_hash: str
    input_redaction_policy: EnumRedactionPolicy = EnumRedactionPolicy.HASH_ONLY
    requested_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC),
    )
    contract_version: ModelSemVer = Field(
        default_factory=lambda: ModelSemVer(major=1, minor=0, patch=0),
    )


__all__ = ["ModelDelegationRequest"]
