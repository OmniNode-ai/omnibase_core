# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Compose-contract drift violation model.

Represents a single bidirectional drift between Docker compose / k8s
environment blocks and contract.yaml event_bus topic declarations.

Related ticket: OMN-9062 (trigger: OMN-8840, parent: OMN-9048).
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_compose_drift_kind import EnumComposeDriftKind

__all__ = ["ModelComposeDriftViolation"]


class ModelComposeDriftViolation(BaseModel):
    """A single compose↔contract drift violation.

    Two drift kinds are captured:

    - BANNED_VAR: compose references an env var whose corresponding topic
      is not declared by any contract.yaml — stale compose (e.g. the
      OMN-8840 case where ``ONEX_INPUT_TOPIC`` survived in compose after
      OMN-8784 removed it from code).

    - MISSING_VAR: a contract declares a topic but no compose / k8s
      manifest exposes the corresponding env var — orphaned contract.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    kind: EnumComposeDriftKind = Field(description="Classification of the drift")
    var_name: str = Field(description="Environment variable name involved in the drift")
    compose_path: Path | None = Field(
        default=None,
        description=(
            "Path to the compose / k8s manifest declaring the env var "
            "(None for MISSING_VAR)"
        ),
    )
    contract_path: Path | None = Field(
        default=None,
        description=(
            "Path to the contract.yaml declaring the topic (None for BANNED_VAR)"
        ),
    )
    message: str = Field(description="Human-readable violation message")
