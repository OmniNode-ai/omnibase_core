# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""State corruption error for node state persistence.

.. versionadded:: 0.35.1
    Added as part of Local-First Node Runtime (OMN-7061)
"""

from __future__ import annotations


class StateCorruptionError(Exception):
    """Raised when persisted state is corrupt or unreadable.

    Distinct from missing state (which returns None). Implementations must raise
    this when data exists but cannot be deserialized or fails integrity checks.
    """
