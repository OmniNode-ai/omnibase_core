# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
TypedDict for lifecycle event metadata fields.

This TypedDict defines the optional fields that can be passed to lifecycle events
(NODE_START, NODE_SUCCESS, NODE_FAILURE) in the MixinNodeLifecycle mixin.
"""

from __future__ import annotations

from typing import TypedDict
from uuid import UUID

# OMN-14339: node_version is annotated with the structural ProtocolSemVer
# (types.type_semver) instead of the concrete ModelSemVer — importing the
# model here created a types -> models import-layering back-edge forbidden by
# the core-foundation-no-upward contract in .importlinter (OMN-3210). Callers
# populate the field with real ModelSemVer instances (which satisfy the
# protocol structurally), and the sole consumer (MixinNodeLifecycle)
# constructs ModelOnexEventMetadata via model_validate(dict(...)), which
# re-validates node_version against the concrete field at runtime.
from omnibase_core.types.type_json import JsonType
from omnibase_core.types.type_semver import ProtocolSemVer


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
    node_version: ProtocolSemVer
    operation_type: str
    execution_time_ms: float
    result_summary: str
    status: str
    reason: str
    registry_id: UUID
    trust_state: str
    ttl: int


__all__ = ["TypedDictLifecycleEventFields"]
