# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""What a runtime lane is for (OMN-19746).

A runtime lane is a deployment: whoever runs the runtime names it, in the
``runtime.lane`` overlay document they supply, and says what it is for by
giving it roles. Core owns the role vocabulary and names no lane
(operator ruling 2026-09-26: this architecture ships to customers who have no
access to our lab, so the set of lanes cannot be compiled into a package).

The vocabulary is closed, like the runtime profiles in
``constants_runtime_profiles``. A new role is new product behaviour and takes a
core release; a new lane never does. A contract that needs a kind of lane
declares ``runtime_lane_roles`` and is attached only where the lane's overlay
grants every role it names. A lane that needs no role declares
``roles: []``.
"""

from __future__ import annotations

from enum import StrEnum, unique


@unique
class EnumRuntimeLaneRole(StrEnum):
    """A role a deployment's overlay may grant its runtime lane.

    Only roles that code reads are declared (plan decision 2): a role exists to
    admit role-gated contracts or to switch a behaviour on. A role is added in
    the same core change as the first code that reads it.
    """

    LAB = "lab"
    """A lab-first verification surface whose health is keyed per lane. Read by
    the auto-wiring ownership filter (the lab lane-health contract) and by the
    runtime-health event's lane keying."""

    FAULT_INJECTION = "fault_injection"
    """A lane on which synthetic provider fault routes may be materialised. Read
    by the fault-route gate."""


__all__ = ["EnumRuntimeLaneRole"]
