# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelContextBundleL2 — standard context bundle level 2 (OMN-10251)."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from omnibase_core.enums.overseer.enum_context_bundle_level import (
    EnumContextBundleLevel,
)
from omnibase_core.models.overseer.model_context_bundle_l1 import ModelContextBundleL1


class ModelContextBundleL2(ModelContextBundleL1, frozen=True, extra="forbid"):
    """Level 2 — standard context.

    Adds entrypoint and file-scope information on top of L1.
    """

    level: Literal[EnumContextBundleLevel.L2] = Field(  # type: ignore[assignment]  # NOTE(OMN-10251): pydantic Field default narrowing to Literal[EnumMember] is a mypy false positive.
        default=EnumContextBundleLevel.L2,
        description="Context bundle level.",
    )
    entrypoints: tuple[str, ...] = Field(
        ..., description="Suggested code entrypoints for the task."
    )
    file_scope: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Files in scope for the task.",
    )


__all__ = ["ModelContextBundleL2"]
