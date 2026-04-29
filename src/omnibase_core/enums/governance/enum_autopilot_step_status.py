# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Autopilot step status enum."""

from enum import Enum, unique


@unique
class EnumAutopilotStepStatus(str, Enum):
    """Status of a single autopilot pipeline step."""

    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"
    NOT_RUN = "not_run"

    def __str__(self) -> str:
        return self.value
