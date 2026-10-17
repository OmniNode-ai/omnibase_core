# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Which property of the DoD evidence admissibility predicate decided a verdict.

Ported from onex_change_control's ``validation/evidence_admissibility.py``
(OMN-15309) for OMN-17427; used by
``omnibase_core.handlers.handler_evidence_admissibility``.
"""

from __future__ import annotations

from enum import StrEnum

__all__ = ["EnumAdmissibilityRule"]


class EnumAdmissibilityRule(StrEnum):
    """Which property of the predicate decided the verdict."""

    ADMISSIBLE = "ADMISSIBLE"
    #: not a usable string at all, or no command survives lexing
    NOT_EXECUTED = "NOT_EXECUTED"
    #: a command runs, but its exit status is fixed by the author's own text
    NOT_FALSIFIABLE = "NOT_FALSIFIABLE"
    #: reads back only artifacts this same change authors
    INSIDE_OWN_DIFF = "INSIDE_OWN_DIFF"
