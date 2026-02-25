# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
LockFileError — raised when the lockfile is missing, corrupt, or unreadable.

.. versionadded:: 0.20.0  (OMN-2570)
"""

from __future__ import annotations

from omnibase_core.errors.error_lock_base import LockError

__all__ = ["LockFileError"]


class LockFileError(LockError):
    """Raised when the cache file is missing, corrupt, or unreadable.

    Callers should instruct the user to run ``omn lock`` to regenerate
    the lockfile.

    .. versionadded:: 0.20.0  (OMN-2570)
    """
