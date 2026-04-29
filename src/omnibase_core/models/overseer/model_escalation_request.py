# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelEscalationRequest — escalation wire type for domain runners (OMN-10251)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from omnibase_core.enums.overseer.enum_capability_tier import EnumCapabilityTier
from omnibase_core.enums.overseer.enum_context_bundle_level import (
    EnumContextBundleLevel,
)
from omnibase_core.enums.overseer.enum_failure_class import EnumFailureClass
from omnibase_core.utils.util_decorators import allow_dict_str_any, allow_string_id


@allow_string_id(
    reason=(
        "task_id and node_id are overseer wire IDs (correlation strings), "
        "not system UUIDs."
    )
)
@allow_dict_str_any(
    reason=(
        "error_detail is a heterogeneous error context payload "
        "with varying value types per failure class."
    )
)
class ModelEscalationRequest(BaseModel, frozen=True, extra="forbid"):
    """Escalation request emitted by domain runners when local retries are exhausted.

    Carries the failure classification, capability tier required for resolution,
    and context bundle level for the next dispatch.
    """

    task_id: str  # string-id-ok: overseer correlation string
    domain: str
    node_id: str  # string-id-ok: node correlation string
    failure_class: EnumFailureClass
    capability_tier: EnumCapabilityTier = EnumCapabilityTier.C2
    context_bundle_level: EnumContextBundleLevel = EnumContextBundleLevel.L2
    attempt: int = Field(default=1, ge=1)
    max_attempts_exhausted: int = Field(default=3, ge=1)
    error_message: str | None = None
    error_detail: dict[str, Any] = Field(
        default_factory=dict
    )  # ONEX_EXCLUDE: dict_str_any - heterogeneous error context
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    # string-version-ok: wire type across domain runners and overseer; JSON
    schema_version: str = "1.0"


__all__ = ["ModelEscalationRequest"]
