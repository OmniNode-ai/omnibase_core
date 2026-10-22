# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Repository type of a CI inheritance baseline (OMN-21277).

RULING 2026-10-14T19:54:41Z: repositories of the same type run the same CI.
The type names the set of reusable omnibase_core workflows a repository
inherits; its baseline lists only the inline jobs it still carries.
"""

from __future__ import annotations

from enum import StrEnum

__all__ = ["EnumCiRepositoryType"]


class EnumCiRepositoryType(StrEnum):
    """Repository types that inherit one CI from omnibase_core."""

    PYTHON = "python"
