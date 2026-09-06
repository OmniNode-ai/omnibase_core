# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""AST location protocol used by the process-environment validator."""

from __future__ import annotations

from typing import Protocol


class _LocatedAstNode(Protocol):
    """The AST location fields required for a reportable raw-reader finding."""

    lineno: int
    col_offset: int
