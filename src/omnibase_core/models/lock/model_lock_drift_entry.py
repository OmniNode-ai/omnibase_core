# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
ModelLockDriftEntry dataclass — one command that has drifted from the lockfile.

.. versionadded:: 0.20.0  (OMN-2570)
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["ModelLockDriftEntry"]


@dataclass
class ModelLockDriftEntry:
    """One command that has drifted from the lockfile.

    Attributes:
        command_id: The drifted command's ID.
        locked_fingerprint: Fingerprint stored in the lockfile.
        current_fingerprint: Fingerprint from the current catalog.
        status: One of ``"changed"``, ``"added"``, or ``"removed"``.
    """

    command_id: str  # string-id-ok: dot-notation namespaced CLI command ID, not a UUID
    locked_fingerprint: str | None = None
    current_fingerprint: str | None = None
    status: str = "changed"
