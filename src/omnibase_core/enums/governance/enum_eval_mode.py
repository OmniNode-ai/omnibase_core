# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Eval Mode Enum.

Treatment vs control mode for A/B eval runs.
"""

from enum import Enum, unique


@unique
class EnumEvalMode(str, Enum):
    """Mode for an eval run: ONEX features on or off.

    - ONEX_ON: All ENABLE_* feature flags active (treatment group)
    - ONEX_OFF: All ENABLE_* feature flags disabled (control group)
    """

    ONEX_ON = "onex_on"
    """Treatment group: ONEX features enabled."""

    ONEX_OFF = "onex_off"
    """Control group: ONEX features disabled."""

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value
