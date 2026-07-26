# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Per-role dispatch report verdict enums (OMN-15161).

Fleet-generic port of steel_onslaught PR #213's ``SO*Verdict`` enums. Each
dispatch role (``omnibase_core.enums.enum_dispatch_report_role.EnumDispatchReportRole``)
has its own closed verdict enum -- a report's ``verdict`` field is never a
free string, it is drawn from exactly one of these four sets, matching the
role the report is for.

See ``docs/plans/2026-07-26-steel-node-dispatch-integration-plan.md`` §3 P1
and epic OMN-15154.
"""

from __future__ import annotations

from enum import StrEnum

__all__ = [
    "EnumDispatchReportImplementerVerdict",
    "EnumDispatchReportLanderVerdict",
    "EnumDispatchReportScoutVerdict",
    "EnumDispatchReportVerifierVerdict",
]


class EnumDispatchReportImplementerVerdict(StrEnum):
    """Closed verdict set for an implementer's final report."""

    IMPLEMENTED = "implemented"
    PARTIAL = "partial"
    BLOCKED = "blocked"


class EnumDispatchReportVerifierVerdict(StrEnum):
    """Closed verdict set for a verifier's final report."""

    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    INCONCLUSIVE = "inconclusive"


class EnumDispatchReportLanderVerdict(StrEnum):
    """Closed verdict set for a lander's final report."""

    MERGED = "merged"
    BLOCKED = "blocked"
    ABORTED = "aborted"


class EnumDispatchReportScoutVerdict(StrEnum):
    """Closed verdict set for a scout's final report."""

    FOUND = "found"
    NOT_FOUND = "not_found"
    BLOCKED = "blocked"
