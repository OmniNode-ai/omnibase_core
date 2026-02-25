# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
LockPartialError — raised when a partial lockfile is detected.

.. versionadded:: 0.20.0  (OMN-2570)
"""

from __future__ import annotations

from omnibase_core.errors.error_lock_base import LockError

__all__ = ["LockPartialError"]


class LockPartialError(LockError):
    """Raised when a partial lockfile is detected.

    A lockfile must cover all commands in the catalog — partial lockfiles
    (a subset of commands) are rejected to prevent silent gaps in
    enforcement.

    Callers should regenerate the lockfile with ``omn lock``.

    .. versionadded:: 0.20.0  (OMN-2570)
    """
