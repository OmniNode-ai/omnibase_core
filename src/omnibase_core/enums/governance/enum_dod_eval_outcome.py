# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Terminal outcome of the shared definition-of-done evaluation."""

from __future__ import annotations

from enum import StrEnum, unique


@unique
class EnumDodEvalOutcome(StrEnum):
    """Whether a completed definition-of-done verification counts as done."""

    DONE = "done"
    REFUSED = "refused"


__all__ = ["EnumDodEvalOutcome"]
