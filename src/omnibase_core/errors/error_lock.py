# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Lockfile error hierarchy re-exports for the registry-driven CLI lockfile system.

Convenience re-export of all lock errors from their canonical single-class modules.

.. versionadded:: 0.20.0  (OMN-2570)
"""

from __future__ import annotations

from omnibase_core.errors.error_lock_base import LockError
from omnibase_core.errors.error_lock_drift import LockDriftError
from omnibase_core.errors.error_lock_file import LockFileError
from omnibase_core.errors.error_lock_partial import LockPartialError

__all__ = [
    "LockDriftError",
    "LockError",
    "LockFileError",
    "LockPartialError",
]
