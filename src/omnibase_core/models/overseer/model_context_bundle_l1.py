# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelContextBundleL1 — basic context bundle level 1 (OMN-10251)."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from omnibase_core.enums.overseer.enum_context_bundle_level import (
    EnumContextBundleLevel,
)
from omnibase_core.models.overseer.model_context_bundle_l0 import ModelContextBundleL0
from omnibase_core.utils.util_decorators import allow_string_id


@allow_string_id(
    reason=(
        "ticket_id is a Linear ticket reference (e.g., 'OMN-1234'), not a system UUID."
    )
)
class ModelContextBundleL1(ModelContextBundleL0, frozen=True, extra="forbid"):
    """Level 1 — basic context.

    Adds ticket metadata and summary on top of L0.
    """

    level: Literal[EnumContextBundleLevel.L1] = Field(  # type: ignore[assignment]
        default=EnumContextBundleLevel.L1,
        description="Context bundle level.",
    )
    ticket_id: str = Field(
        ..., description="Linear ticket identifier."
    )  # string-id-ok: Linear ticket reference
    summary: str = Field(..., description="Human-readable task summary.")


__all__ = ["ModelContextBundleL1"]
