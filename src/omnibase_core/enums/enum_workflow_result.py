# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Terminal result states for a workflow run."""

from __future__ import annotations

from enum import Enum, unique

__all__ = ["EnumWorkflowResult"]


@unique
class EnumWorkflowResult(str, Enum):
    """Terminal result states for a workflow run.

    Values:
        COMPLETED: Terminal event received, evidence written (exit 0).
        TIMEOUT: ``--timeout`` exceeded without terminal event (exit 1).
        PARTIAL: Some evidence written but no terminal event (exit 2).
        FAILED: Terminal event received with failure payload (exit 1).
    """

    COMPLETED = "completed"
    TIMEOUT = "timeout"
    PARTIAL = "partial"
    FAILED = "failed"
