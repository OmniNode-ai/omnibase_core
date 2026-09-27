# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""ValidatorRuntimeLaneRoles: a contract's runtime_lane_roles name known roles (OMN-19746).

A contract says which lane ROLES it needs (``runtime_lane_roles: [lab]``) and
never names a lane. A role outside ``EnumRuntimeLaneRole`` would scope the node
to a role no deployment can hold, which detaches it everywhere, so the
validator refuses it in CI and pre-commit.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.validation.validator_runtime_lane_roles import (
    RULE_RUNTIME_LANE_ROLE_UNKNOWN,
    ValidatorRuntimeLaneRoles,
)

pytestmark = pytest.mark.unit


def _write(tmp_path: Path, body: str) -> Path:
    node = tmp_path / "node_example"
    node.mkdir()
    path = node / "contract.yaml"
    path.write_text(body, encoding="utf-8")
    return path


def _codes(tmp_path: Path) -> list[str]:
    result = ValidatorRuntimeLaneRoles().validate(tmp_path)
    return [issue.code or "" for issue in result.issues]


def test_known_roles_pass(tmp_path: Path) -> None:
    _write(tmp_path, "name: node_example\nruntime_lane_roles: [lab, fault_injection]\n")
    assert _codes(tmp_path) == []


def test_a_contract_without_roles_passes(tmp_path: Path) -> None:
    _write(tmp_path, "name: node_example\nruntime_profiles: [main]\n")
    assert _codes(tmp_path) == []


def test_an_unknown_role_is_refused(tmp_path: Path) -> None:
    _write(tmp_path, "name: node_example\nruntime_lane_roles: [labb]\n")
    assert _codes(tmp_path) == [RULE_RUNTIME_LANE_ROLE_UNKNOWN]


def test_a_lane_id_in_place_of_a_role_is_refused(tmp_path: Path) -> None:
    # A contract that names a deployment's lane is exactly what the ruling
    # forbids: the lane is the overlay's business, the contract names a role.
    _write(tmp_path, "name: node_example\nruntime_lane_roles: [customer-edge-7]\n")
    assert _codes(tmp_path) == [RULE_RUNTIME_LANE_ROLE_UNKNOWN]


@pytest.mark.parametrize("value", ["[]", "3", "{lab: true}"])
def test_an_empty_or_malformed_role_list_is_refused(tmp_path: Path, value: str) -> None:
    _write(tmp_path, f"name: node_example\nruntime_lane_roles: {value}\n")
    assert _codes(tmp_path) == [RULE_RUNTIME_LANE_ROLE_UNKNOWN]


def test_the_message_names_the_contract_the_role_and_the_vocabulary(
    tmp_path: Path,
) -> None:
    _write(tmp_path, "name: node_example\nruntime_lane_roles: [labb]\n")
    result = ValidatorRuntimeLaneRoles().validate(tmp_path)
    message = result.issues[0].message
    assert "node_example" in message
    assert "labb" in message
    assert "fault_injection" in message
