# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
LockError — base error for all lockfile failures.

.. versionadded:: 0.20.0  (OMN-2570)
"""

from __future__ import annotations

__all__ = ["LockError"]


class LockError(Exception):
    """Base error for all lockfile failures.

    Raised by ServiceLockManager when a lock operation fails.
    Catch this base class to handle all lock errors uniformly.

    .. versionadded:: 0.20.0  (OMN-2570)
    """
