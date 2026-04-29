# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelContextBundleL4 — maximum context bundle level 4 (OMN-10251)."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from omnibase_core.enums.overseer.enum_context_bundle_level import (
    EnumContextBundleLevel,
)
from omnibase_core.models.overseer.model_context_bundle_l3 import ModelContextBundleL3


class ModelContextBundleL4(ModelContextBundleL3, frozen=True, extra="forbid"):
    """Level 4 — maximum context.

    Adds full dependency graph and raw context payload on top of L3.
    """

    # NOTE(OMN-10251): mypy cannot narrow Enum member default to Literal[EnumMember] — structural subtyping false positive.
    level: Literal[EnumContextBundleLevel.L4] = Field(  # type: ignore[assignment]
        default=EnumContextBundleLevel.L4,
        description="Context bundle level.",
    )
    dependency_graph: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Mapping of task IDs to their dependency task IDs.",
    )
    raw_context: dict[str, str] = Field(
        default_factory=dict,
        description="Arbitrary key-value context payload.",
    )


__all__ = ["ModelContextBundleL4"]
