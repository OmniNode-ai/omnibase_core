# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Probe Status Enum (governance namespace).

Execution status for each Phase 2 investigation probe.
This is the OCC-origin governance enum with COMPLETED/FAILED/SKIPPED/TIMED_OUT values,
distinct from omnibase_core.enums.enum_triage_probe_status.EnumProbeStatus (SUCCESS/DEGRADED/ERROR).
"""

from enum import Enum, unique


@unique
class EnumProbeStatus(str, Enum):
    """Execution status for begin-day investigation probes.

    Tracks the outcome of each parallel probe in Phase 2:
    - COMPLETED: Probe ran successfully and produced findings
    - FAILED: Probe encountered an error during execution
    - SKIPPED: Probe was not dispatched (skill not available or filtered out)
    - TIMED_OUT: Probe exceeded its time budget
    """

    COMPLETED = "completed"
    """Probe ran successfully and produced findings."""

    FAILED = "failed"
    """Probe encountered an error during execution."""

    SKIPPED = "skipped"
    """Probe was not dispatched (skill not available or filtered out)."""

    TIMED_OUT = "timed_out"
    """Probe exceeded its time budget."""

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value
