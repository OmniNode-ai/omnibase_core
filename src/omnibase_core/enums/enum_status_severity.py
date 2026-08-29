# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Semantic severity roles for status tiles (OMN-16884, Phase C3).

A severity is a **semantic role**, never a colour. The role is what a widget
contract carries; the colour is looked up from the active theme instance by
token name at render time. That is the whole point: a config that carries a hex
value has already decided what a theme is allowed to decide.

Ordering is declared here rather than left to tile order, so a grid can sort and
summarise deterministically. ``UNKNOWN`` deliberately sorts **above** ``NOMINAL``
and **below** ``ATTENTION``: a tile whose state cannot be read is worse than one
known to be fine — you are blind to it — but it is not evidence of a fault, and
ranking it above a real attention verdict would bury the verdicts that are.

Severity verdicts are computed **upstream** and arrive as facts. Nothing here
thresholds anything; a client that inferred severity would be inferring
authoritative system state, which the truth doctrine forbids.
"""

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper

__all__ = ("EnumStatusSeverity",)


@unique
class EnumStatusSeverity(UtilStrValueHelper, str, Enum):
    """Semantic severity role of a status tile.

    Attributes:
        NOMINAL: Operating as expected.
        UNKNOWN: State could not be determined. Not an alarm, not an all-clear.
        ATTENTION: Degraded or trending wrong; a human should look.
        CRITICAL: Failing now.
    """

    NOMINAL = "nominal"
    UNKNOWN = "unknown"
    ATTENTION = "attention"
    CRITICAL = "critical"

    @property
    def severity_rank(self) -> int:
        """Declared ordering, ascending in severity.

        A grid sorts by this descending so the worst tiles surface first, and
        summarises by it without inventing an order of its own.

        Returns:
            The rank: ``NOMINAL`` 0, ``UNKNOWN`` 1, ``ATTENTION`` 2,
            ``CRITICAL`` 3.
        """
        return _SEVERITY_RANKS[self]

    @property
    def theme_color_token(self) -> str:
        """Name of the ``ModelRendererThemeContract`` token this role resolves to.

        A **token name**, never a token value: the value lives in the active
        theme instance (OMN-16882), so light/dark/warm render the same severity
        differently without any config changing.

        Returns:
            The theme field name, e.g. ``'color_status_error'`` for
            ``CRITICAL``.
        """
        return _SEVERITY_THEME_TOKENS[self]


_SEVERITY_RANKS: dict[EnumStatusSeverity, int] = {
    EnumStatusSeverity.NOMINAL: 0,
    EnumStatusSeverity.UNKNOWN: 1,
    EnumStatusSeverity.ATTENTION: 2,
    EnumStatusSeverity.CRITICAL: 3,
}

_SEVERITY_THEME_TOKENS: dict[EnumStatusSeverity, str] = {
    EnumStatusSeverity.NOMINAL: "color_status_success",
    EnumStatusSeverity.UNKNOWN: "color_status_info",
    EnumStatusSeverity.ATTENTION: "color_status_warning",
    EnumStatusSeverity.CRITICAL: "color_status_error",
}
