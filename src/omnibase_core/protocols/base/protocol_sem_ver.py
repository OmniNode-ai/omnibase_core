# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Semantic Version Protocol (canonical re-export).

The single canonical ``ProtocolSemVer`` structural protocol lives in
``omnibase_core.types.type_semver`` (the richer superset surface). This module
re-exports it so the historical ``omnibase_core.protocols.base`` import path
keeps resolving to the same object.
"""

from __future__ import annotations

from omnibase_core.types.type_semver import ProtocolSemVer

__all__ = ["ProtocolSemVer"]
