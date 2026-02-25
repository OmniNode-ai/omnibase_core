# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
ModelLockDiffResult dataclass — result of ServiceLockManager.diff().

.. versionadded:: 0.20.0  (OMN-2570)
"""

from __future__ import annotations

from dataclasses import dataclass, field

from omnibase_core.models.lock.model_lock_drift_entry import ModelLockDriftEntry

__all__ = ["ModelLockDiffResult"]


@dataclass
class ModelLockDiffResult:
    """Result of ``ServiceLockManager.diff()``.

    Attributes:
        drifted: List of commands that have drifted.
        is_clean: True when there is no drift (drifted is empty).
    """

    drifted: list[ModelLockDriftEntry] = field(default_factory=list)

    @property
    def is_clean(self) -> bool:
        """Return True when no commands have drifted."""
        return not self.drifted
