# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""What a declared quality rule is entitled to do to a verdict (OMN-18295)."""

from __future__ import annotations

from enum import StrEnum


class EnumQualityRuleEnforcement(StrEnum):
    """The authority one declared quality-gate rule holds over acceptance.

    A rule is one of these or the other, never both. That exclusivity is the
    whole point: delegation ``ca144d1a-ea03-475f-bc81-650ccfa0495e`` had its
    ``concise`` miss priced into a graded score of 0.900, cleared an 0.800 bar,
    printed ``score_vs_bar=at_or_above_bar`` — and was then failed by the SAME
    miss acting a second time as an absolute veto. One axis, two rules,
    opposite verdicts, and nothing on the receipt named which one decided.

    ``SCORED`` moves the graded score and leaves the verdict to the required
    bar. ``BLOCKING`` vetoes acceptance outright, whatever the score says. A
    rule the contract does not declare is treated as blocking by the producer,
    so forgetting to declare one cannot silently strip a veto.
    """

    BLOCKING = "blocking"
    SCORED = "scored"


__all__ = ["EnumQualityRuleEnforcement"]
