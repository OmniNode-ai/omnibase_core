# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelContextBundleL0 — minimal context bundle level 0 (OMN-10251)."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from omnibase_core.enums.overseer.enum_context_bundle_level import (
    EnumContextBundleLevel,
)
from omnibase_core.models.overseer.model_context_bundle_base import _ContextBundleBase


class ModelContextBundleL0(_ContextBundleBase, frozen=True, extra="forbid"):
    """Level 0 — minimal context.

    Contains only the fields required for task routing and FSM tracking.
    """

    level: Literal[EnumContextBundleLevel.L0] = Field(
        default=EnumContextBundleLevel.L0,
        description="Context bundle level.",
    )


__all__ = ["ModelContextBundleL0"]
