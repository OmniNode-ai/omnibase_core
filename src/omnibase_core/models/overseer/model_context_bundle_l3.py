# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelContextBundleL3 — rich context bundle level 3 (OMN-10251)."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from omnibase_core.enums.overseer.enum_context_bundle_level import (
    EnumContextBundleLevel,
)
from omnibase_core.models.overseer.model_context_bundle_l2 import ModelContextBundleL2


class ModelContextBundleL3(ModelContextBundleL2, frozen=True, extra="forbid"):
    """Level 3 — rich context.

    Adds architectural decisions and history on top of L2.
    """

    level: Literal[EnumContextBundleLevel.L3] = Field(  # type: ignore[assignment]
        default=EnumContextBundleLevel.L3,
        description="Context bundle level.",
    )
    decisions: list[str] = Field(
        default_factory=list,
        description="Active architectural decisions relevant to this task.",
    )
    history: list[str] = Field(
        default_factory=list,
        description="Relevant historical context entries.",
    )


__all__ = ["ModelContextBundleL3"]
