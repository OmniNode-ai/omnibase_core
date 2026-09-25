# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""A node contract may declare the runtime lanes it attaches on (OMN-19408).

The .201 stability-test runtime loaded the lab lane-health projection, whose
scope (OMN-18769 AC6) holds rows for the three lab lanes only. Every health
event it consumed there was correctly dropped, the projection wrote nothing,
and the apply-divergence detector held the lane unhealthy for eleven hours.
The defect was the attachment, not the fold: nothing let the contract say
where it may run.

``runtime_lanes`` is that declaration. Core owns the lane NAMES and the typed
shape the infra loader parses; infra owns the attach decision -- the same
split as ``runtime_profiles`` (OMN-12957).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from omnibase_core.constants.constants_runtime_lanes import (
    LAB_RUNTIME_LANES,
    REGISTERED_RUNTIME_LANES,
)
from omnibase_core.models.contracts.subcontracts.model_runtime_lane_scope import (
    ModelRuntimeLaneScope,
)

pytestmark = pytest.mark.unit


def test_the_lab_lanes_are_registered_lanes() -> None:
    assert LAB_RUNTIME_LANES <= REGISTERED_RUNTIME_LANES
    assert frozenset({"compose-dev", "onex-lab", "onex-lab-k3s"}) == LAB_RUNTIME_LANES


def test_stability_test_is_a_lane_a_runtime_can_declare_but_not_a_lab_lane() -> None:
    # The stability-test deployment must be able to name itself honestly, and
    # naming itself must not make it a lab lane (OMN-18769 AC6 is unchanged).
    assert "stability-test" in REGISTERED_RUNTIME_LANES
    assert "stability-test" not in LAB_RUNTIME_LANES


def test_scope_admits_a_lane_inside_it_and_refuses_one_outside_it() -> None:
    scope = ModelRuntimeLaneScope(lanes=("compose-dev", "onex-lab", "onex-lab-k3s"))
    assert scope.admits("compose-dev") is True
    assert scope.admits("stability-test") is False


def test_scope_normalizes_case_whitespace_and_duplicates() -> None:
    scope = ModelRuntimeLaneScope(lanes=[" Compose-Dev ", "compose-dev", "ONEX-LAB"])
    assert scope.lanes == ("compose-dev", "onex-lab")


def test_a_single_string_is_one_lane() -> None:
    assert ModelRuntimeLaneScope(lanes="stability-test").lanes == ("stability-test",)


def test_an_unregistered_lane_is_refused_by_name() -> None:
    # A typo would otherwise scope the node to a lane no runtime can declare,
    # which silently detaches it everywhere.
    with pytest.raises(ValidationError, match="stabilty-test"):
        ModelRuntimeLaneScope(lanes=("compose-dev", "stabilty-test"))


def test_an_empty_scope_is_refused() -> None:
    # Declaring the field with no lanes would detach the node on every lane.
    # Omit the field instead; an unscoped contract attaches wherever its
    # runtime profile owns it.
    with pytest.raises(ValidationError):
        ModelRuntimeLaneScope(lanes=())


@pytest.mark.parametrize("bad", [[""], ["  "], [3], 3, None])
def test_malformed_entries_are_refused(bad: object) -> None:
    with pytest.raises(ValidationError):
        ModelRuntimeLaneScope(lanes=bad)


def test_admits_refuses_an_undeclared_runtime_lane() -> None:
    # A runtime that cannot name its lane is never inside a lane scope.
    scope = ModelRuntimeLaneScope(lanes=("compose-dev",))
    assert scope.admits(None) is False
    assert scope.admits("") is False


def test_scope_is_frozen() -> None:
    scope = ModelRuntimeLaneScope(lanes=("compose-dev",))
    with pytest.raises(ValidationError):
        scope.lanes = ("onex-lab",)  # type: ignore[misc]
