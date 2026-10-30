# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the pure collaborator-lane checker and generic validator (OMN-21599).

Operator ruling 2026-10-30T12:43:03Z: collaborators build, test and prove on the test/stability
lane. Every rule has a planted violation fixture (exactly one issue with its rule id) and a clean
fixture (no issue). All rule data lives in ``validation/contracts/collaborator_lane.validation.yaml``;
the table-driven mutation test changes every ``parameters`` key of every rule row in turn and asserts
the verdict changes on at least one of that rule's fixtures.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any, cast

import pytest
import yaml

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.collaborator_lane.model_collaborator_lane_check_input import (
    ModelCollaboratorLaneCheckInput,
)
from omnibase_core.models.collaborator_lane.model_collaborator_lane_check_result import (
    ModelCollaboratorLaneCheckResult,
)
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.validation import validator_base
from omnibase_core.validation.checker_collaborator_lane import check_collaborator_lane
from omnibase_core.validation.validator_collaborator_lane import (
    ValidatorCollaboratorLane,
)

pytestmark = pytest.mark.unit

FIXTURES = (
    Path(__file__).resolve().parents[2]
    / "fixtures"
    / "validation"
    / "collaborator_lane"
)
CONTRACT_PATH = (
    Path(validator_base.__file__).parent
    / "contracts"
    / "collaborator_lane.validation.yaml"
)

# rule id -> (document name the rule selects on, violation fixture, clean fixtures)
CASES: dict[str, tuple[str, str, tuple[str, ...]]] = {
    "brief_on_dev_lane": (
        "lanes/x/lane-brief.txt",
        "violation_brief_on_dev_lane.txt",
        (
            "clean_brief_on_dev_lane.txt",
            "clean_brief_orchestrator_on_dev_lane.txt",
        ),
    ),
    "brief_without_collaborator_lane": (
        "lanes/x/lane-brief.txt",
        "violation_brief_without_collaborator_lane.txt",
        ("clean_brief_without_collaborator_lane.txt",),
    ),
    "proof_rule_on_dev_lane": (
        "lanes/x/rules.md",
        "violation_proof_rule_on_dev_lane.txt",
        ("clean_proof_rule_on_dev_lane.txt",),
    ),
    "placement_on_dev_lane": (
        "config/lab/x.yaml",
        "violation_placement_on_dev_lane.yaml",
        ("clean_placement_on_dev_lane.yaml",),
    ),
    "placement_unreadable": (
        "config/lab/x.yaml",
        "violation_placement_unreadable.txt",
        ("clean_placement_on_dev_lane.yaml",),
    ),
}
JSON_BRIEF = (
    "lanes/x/job.json",
    "violation_brief_on_dev_lane.json",
    "clean_brief_on_dev_lane.json",
)
JSON_BRIEF_NO_LANE = "violation_brief_without_collaborator_lane.json"


def _contract_data() -> dict[str, Any]:
    return cast(
        "dict[str, Any]", yaml.safe_load(CONTRACT_PATH.read_text("utf-8"))["validation"]
    )


def _contract(data: dict[str, Any] | None = None) -> ModelValidatorSubcontract:
    return ModelValidatorSubcontract.model_validate(data or _contract_data())


def _run(
    name: str, fixture: str, contract: ModelValidatorSubcontract
) -> ModelCollaboratorLaneCheckResult:
    return check_collaborator_lane(
        ModelCollaboratorLaneCheckInput(
            source_name=name,
            text=(FIXTURES / fixture).read_text("utf-8"),
            contract=contract,
        )
    )


def _codes(result: ModelCollaboratorLaneCheckResult) -> list[str]:
    return sorted(str(issue.code) for issue in result.issues)


@pytest.mark.parametrize("rule_id", sorted(CASES))
def test_violation_fixture_yields_exactly_one_issue_with_its_rule_id(
    rule_id: str,
) -> None:
    name, violation, _ = CASES[rule_id]
    result = _run(name, violation, _contract())
    assert _codes(result) == [rule_id]
    assert result.exit_code == 1


@pytest.mark.parametrize("rule_id", sorted(CASES))
def test_clean_fixture_yields_no_issue(rule_id: str) -> None:
    name, _, cleans = CASES[rule_id]
    for clean in cleans:
        result = _run(name, clean, _contract())
        assert _codes(result) == [], clean
        assert result.exit_code == 0


def test_json_brief_is_judged_outside_its_pasted_standing_block() -> None:
    name, violation, clean = JSON_BRIEF
    assert _codes(_run(name, violation, _contract())) == ["brief_on_dev_lane"]
    assert _codes(_run(name, clean, _contract())) == []


def test_json_brief_without_a_run_lane_is_refused_even_when_the_block_names_one() -> (
    None
):
    assert _codes(_run(JSON_BRIEF[0], JSON_BRIEF_NO_LANE, _contract())) == [
        "brief_without_collaborator_lane"
    ]


def test_message_cites_the_ruling_and_the_dev_lane_target() -> None:
    name, violation, _ = CASES["brief_on_dev_lane"]
    (issue,) = _run(name, violation, _contract()).issues
    assert "RULING 2026-10-30T12:43:03Z" in issue.message
    assert "dev lane" in issue.message


def test_a_document_no_rule_selects_is_not_judged() -> None:
    _, violation, _ = CASES["brief_on_dev_lane"]
    assert _codes(_run("notes/unrelated.txt", violation, _contract())) == []


@pytest.mark.parametrize("rule_id", sorted(CASES))
def test_disabled_rule_does_not_fire(rule_id: str) -> None:
    data = copy.deepcopy(_contract_data())
    for rule in data["rules"]:
        if rule["rule_id"] == rule_id:
            rule["enabled"] = False
    name, violation, _ = CASES[rule_id]
    assert rule_id not in _codes(_run(name, violation, _contract(data)))


def _mutations(value: object, key: str) -> list[object]:
    if isinstance(value, list):
        return [["zzz-never"]]
    if key.endswith("_pattern"):
        return ["(?!)", "(?=)"]
    return ["zzz-never"]


def test_every_parameters_key_changes_a_verdict_parameters() -> None:
    """Configuration: each parameters entry is load-bearing, none is dead data."""
    base = _contract_data()
    dead: list[str] = []
    for index, rule in enumerate(base["rules"]):
        rule_id = rule["rule_id"]
        name, violation, cleans = CASES[rule_id]
        fixtures = [(name, violation), *[(name, clean) for clean in cleans]]
        if rule_id.startswith("brief_"):
            fixtures += [
                (JSON_BRIEF[0], JSON_BRIEF[1]),
                (JSON_BRIEF[0], JSON_BRIEF[2]),
                (JSON_BRIEF[0], JSON_BRIEF_NO_LANE),
            ]
        baseline = [_codes(_run(n, f, _contract(base))) for n, f in fixtures]
        for key, value in rule["parameters"].items():
            if key in {"message", "source_pattern"}:
                continue
            changed = False
            for mutant in _mutations(value, key):
                data = copy.deepcopy(base)
                data["rules"][index]["parameters"][key] = mutant
                try:
                    verdicts = [
                        _codes(_run(n, f, _contract(data))) for n, f in fixtures
                    ]
                except ModelOnexError:
                    changed = True
                    break
                if verdicts != baseline:
                    changed = True
                    break
            if not changed:
                dead.append(f"{rule_id}.{key}")
    assert dead == []


def test_source_pattern_selects_the_documents_a_rule_judges() -> None:
    data = copy.deepcopy(_contract_data())
    data["rules"][0]["parameters"]["source_pattern"] = "(?!)"
    name, violation, _ = CASES["brief_on_dev_lane"]
    assert _codes(_run(name, violation, _contract(data))) == []


@pytest.mark.parametrize(
    "broken",
    ["absent_rule", "missing_parameter", "bad_regex", "empty_lane_keys"],
)
def test_invalid_contract_fails_to_load(broken: str) -> None:
    data = copy.deepcopy(_contract_data())
    if broken == "absent_rule":
        data["rules"] = data["rules"][1:]
    elif broken == "missing_parameter":
        del data["rules"][0]["parameters"]["dev_lane_pattern"]
    elif broken == "bad_regex":
        data["rules"][0]["parameters"]["dev_lane_pattern"] = "("
    else:
        data["rules"][3]["parameters"]["lane_keys"] = []
    name, violation, _ = CASES["brief_on_dev_lane"]
    with pytest.raises(ModelOnexError):
        _run(name, violation, _contract(data))


def test_generic_validator_reports_a_planted_violation_by_file(tmp_path: Path) -> None:
    target = tmp_path / "config" / "lab"
    target.mkdir(parents=True)
    planted = target / "placement.yaml"
    planted.write_text(
        (FIXTURES / "violation_placement_on_dev_lane.yaml").read_text("utf-8"), "utf-8"
    )
    clean = target / "clean.yaml"
    clean.write_text(
        (FIXTURES / "clean_placement_on_dev_lane.yaml").read_text("utf-8"), "utf-8"
    )
    result = ValidatorCollaboratorLane().validate(tmp_path)
    assert result.is_valid is False
    assert {Path(str(issue.file_path)).name for issue in result.issues} == {
        "placement.yaml"
    }
    assert [issue.code for issue in result.issues] == ["placement_on_dev_lane"]
