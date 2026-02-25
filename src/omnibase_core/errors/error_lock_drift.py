# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
LockDriftError — raised when the current catalog does not match the lockfile.

.. versionadded:: 0.20.0  (OMN-2570)
"""

from __future__ import annotations

from omnibase_core.errors.error_lock_base import LockError

__all__ = ["LockDriftError"]


class LockDriftError(LockError):
    """Raised when the current catalog does not match the lockfile.

    Indicates that one or more contract fingerprints have changed since
    the lockfile was generated.  The CLI halts on drift to prevent
    non-deterministic execution in CI environments.

    Callers should instruct the user to run ``omn lock`` to regenerate
    the lockfile, or investigate which contracts have changed.

    .. versionadded:: 0.20.0  (OMN-2570)
    """
