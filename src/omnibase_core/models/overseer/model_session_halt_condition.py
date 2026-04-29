# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelSessionHaltCondition — condition that triggers an immediate session halt (OMN-10251)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from omnibase_core.utils.util_decorators import allow_string_id


@allow_string_id(
    reason=(
        "condition_id is a named halt condition identifier (e.g., 'cost_ceiling'), "
        "not a system UUID."
    )
)
class ModelSessionHaltCondition(BaseModel):
    """Condition that triggers an immediate halt of the session."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    condition_id: str  # string-id-ok: named halt condition identifier, not a UUID
    description: str
    check_type: Literal["cost_ceiling", "phase_failure_count", "time_elapsed", "custom"]
    threshold: float


__all__ = ["ModelSessionHaltCondition"]
