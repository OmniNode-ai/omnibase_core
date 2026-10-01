# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""A command line that runs a file or module of the repository (OMN-20295)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class _ScriptRef:
    """A command line that runs a file or module of the repository."""

    name: str
    is_module: bool
