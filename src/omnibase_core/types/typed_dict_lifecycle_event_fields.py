# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
TypedDict for lifecycle event metadata fields.

This TypedDict defines the optional fields that can be passed to lifecycle events
(NODE_START, NODE_SUCCESS, NODE_FAILURE) in the MixinNodeLifecycle mixin.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict
from uuid import UUID

# OMN-14337 residual: this TypedDict is the constructor-kwargs shape for
# ModelOnexEventMetadata (its node_version field is ModelSemVer | None); it is
# **-unpacked into that Pydantic model, so the structural ProtocolSemVer does not
# satisfy the concrete field. Deferred to OMN-14339 (narrowed .importlinter line).
if TYPE_CHECKING:
    from omnibase_core.models.primitives.model_semver import ModelSemVer

from omnibase_core.types.type_json import JsonType


class TypedDictLifecycleEventFields(TypedDict, total=False):
    """TypedDict for event metadata passed to lifecycle events.

    All fields are optional (total=False) and provide context about
    the node execution state when lifecycle events are emitted.
    """

    input_state: dict[str, JsonType]
    output_state: dict[str, JsonType]
    error: str
    error_type: str
    error_code: str
    recoverable: bool
    node_version: ModelSemVer
    operation_type: str
    execution_time_ms: float
    result_summary: str
    status: str
    reason: str
    registry_id: UUID
    trust_state: str
    ttl: int


__all__ = ["TypedDictLifecycleEventFields"]
