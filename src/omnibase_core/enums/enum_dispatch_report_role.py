# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Dispatch report role enum (OMN-15161).

Fleet-generic port of steel_onslaught PR #213's ``SODispatchRole``. The four
roles are the closed set of dispatch report contracts modeled in
``omnibase_core.models.dispatch.report``: ``implementer`` (builds/fixes code
and opens or updates a PR), ``verifier`` (independently re-checks an
implementer's claim against live evidence), ``lander`` (merges/finalizes a
PR), and ``scout`` (investigates/discovers, no PR required).

See ``docs/plans/2026-07-26-steel-node-dispatch-integration-plan.md`` §3 P1
and epic OMN-15154.
"""

from __future__ import annotations

from enum import StrEnum

__all__ = ["EnumDispatchReportRole"]


class EnumDispatchReportRole(StrEnum):
    """The four dispatch roles covered by the dispatch report contracts."""

    IMPLEMENTER = "implementer"
    VERIFIER = "verifier"
    LANDER = "lander"
    SCOUT = "scout"
