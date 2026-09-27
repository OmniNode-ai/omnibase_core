# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Execution-graph replay verdict outcome vocabulary."""

from __future__ import annotations

from enum import StrEnum, unique


@unique
class EnumExecutionGraphVerdictOutcome(StrEnum):
    """Closed execution-graph replay verdict outcome values."""

    DONE = "done"
    REFUSED = "refused"


__all__ = ["EnumExecutionGraphVerdictOutcome"]
