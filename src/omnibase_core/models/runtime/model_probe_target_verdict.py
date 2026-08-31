# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Result of a satisfied probe-target assertion (OMN-17312)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelProbeTargetVerdict"]


class ModelProbeTargetVerdict(BaseModel):
    """A stamp that satisfied a target's declaration, and what was compared."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    target_name: str = Field(
        ...,
        min_length=1,
        description="The target the stamp was asserted against.",
    )
    declared_by: str = Field(
        ...,
        min_length=1,
        description="The surface the declaration was read from.",
    )
    compared_fields: list[str] = Field(
        ...,
        min_length=1,
        description=(
            "Every field actually compared, e.g. ['host', "
            "'package:omnimarket']. Non-empty by construction so 'asserted' "
            "can never quietly mean 'compared nothing' — the OMN-14531 "
            "failure class, where 16/16 sweeps passed while scanning zero "
            "items."
        ),
    )
