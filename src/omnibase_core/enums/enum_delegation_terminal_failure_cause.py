# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed terminal failure causes for delegation wire results."""

from __future__ import annotations

from enum import Enum, unique


@unique
class EnumDelegationTerminalFailureCause(str, Enum):
    """Machine-readable cause of a terminal delegation failure."""

    PROVIDER_QUOTA_EXHAUSTED = "provider_quota_exhausted"


__all__: list[str] = ["EnumDelegationTerminalFailureCause"]
