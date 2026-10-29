# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the pure design-record checker and generic validator (OMN-21509, task T-P1b).

The verdict cases reproduce the ones the merged omnimarket check was tested with
(OMN-21460). All rule data lives in ``validation/contracts/design_record.validation.yaml``.
Mutation cases prove that every contract parameter changes the checker output.
"""

from __future__ import annotations

import ast
import copy
import json
from collections.abc import Callable
from pathlib import Path
from string import Formatter
from typing import Any

import pytest
import yaml

from omnibase_core.enums import EnumSeverity
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.design_record import model_design_record_rules as rules_module
from omnibase_core.models.design_record.model_design_record_check_input import (
    ModelDesignRecordCheckInput,
)
from omnibase_core.models.design_record.model_design_record_check_result import (
    ModelDesignRecordCheckResult,
)
from omnibase_core.validation import checker_design_record as checker_module
from omnibase_core.validation import validator_base
from omnibase_core.validation.checker_design_record import check_design_record
from omnibase_core.validation.validator_design_record import ValidatorDesignRecord

pytestmark = pytest.mark.unit

FIXTURES = (
    Path(__file__).resolve().parents[2] / "fixtures" / "validation" / "design_record"
)
CONTRACT_PATH = (
    Path(validator_base.__file__).parent / "contracts" / "design_record.validation.yaml"
)

HEAD = """\
Intended state: the queue drains within one hour.
Live check command: onex run-node node_queue_probe
Live check failing reading: depth 40 before the build.
"""
HEADER = "| Failure mode | How | Detected by | Severity | Detector |\n| -- | -- | -- | -- | -- |\n"

RULE_IDS = {
    "record_missing",
    "intended_state_missing",
    "live_check_command_missing",
    "failure_mode_table_missing",
    "failure_mode_table_empty",
    "row_without_detector_or_gap",
    "severity_out_of_range",
}


def _check(
    text: str, contract: ModelValidatorSubcontract | None = None
) -> ModelDesignRecordCheckResult:
    return check_design_record(
        ModelDesignRecordCheckInput(
            text=text, contract=contract or ValidatorDesignRecord().contract
        )
    )


def _codes(result: ModelDesignRecordCheckResult) -> set[str | None]:
    return {issue.code for issue in result.issues}


def _contract_with(
    mutate: Callable[[dict[str, dict[str, Any]]], None],
) -> ModelValidatorSubcontract:
    """The committed contract with `mutate` applied to its rules, by rule id."""
    data = yaml.safe_load(CONTRACT_PATH.read_text("utf-8"))["validation"]
    rules = {rule["rule_id"]: copy.deepcopy(rule) for rule in data["rules"]}
    mutate(rules)
    data["rules"] = list(rules.values())
    return ModelValidatorSubcontract.model_validate(data)


def test_empty_failure_mode_table_is_refused_naming_the_part() -> None:
    result = _check(HEAD + HEADER)
    assert "failure_mode_table_empty" in _codes(result)
    assert any(
        (i.context or {}).get("part") == "failure-mode table" for i in result.issues
    )
    assert result.failure_mode_rows == 0


def test_missing_table_is_refused() -> None:
    assert "failure_mode_table_missing" in _codes(_check(HEAD))


def test_row_with_no_detector_and_no_gap_is_refused() -> None:
    result = _check(HEAD + HEADER + "| stalls | lock | none | 2 | |\n")
    assert _codes(result) == {"row_without_detector_or_gap"}
    assert result.rows_without_detector_or_gap == 1
    assert (result.issues[0].context or {}).get("row") == "1"


def test_row_with_gap_mark_or_detector_is_accepted() -> None:
    body = (
        HEAD
        + HEADER
        + "| stalls | lock | none | 2 | GAP |\n| dup | race | probe | 1 | test_x.py |\n"
    )
    result = _check(body)
    assert result.issues == ()
    assert result.failure_mode_rows == 2
    assert result.rows_without_detector_or_gap == 0


def test_no_live_check_command_is_refused() -> None:
    body = HEAD.replace("Live check command: onex run-node node_queue_probe\n", "")
    result = _check(body + HEADER + "| a | b | c | 1 | GAP |\n")
    assert _codes(result) == {"live_check_command_missing"}
    assert result.live_check_command_present is False


def test_no_intended_state_is_refused() -> None:
    body = HEAD.replace("Intended state: the queue drains within one hour.\n", "")
    result = _check(body + HEADER + "| a | b | c | 1 | GAP |\n")
    assert _codes(result) == {"intended_state_missing"}


def test_body_without_a_record_is_refused() -> None:
    result = _check("# A plan\n\nNothing here.\n")
    assert _codes(result) == {"record_missing"}


def test_section_11_3_fixture_passes() -> None:
    result = _check((FIXTURES / "section_11_3_design_record.txt").read_text("utf-8"))
    assert result.issues == ()
    assert result.exit_code == 0
    assert result.failure_mode_rows == 3
    assert result.live_check_command_present is True
    assert result.live_check_failing_reading is True


def test_any_issue_sets_exit_code_nonzero_and_none_sets_zero() -> None:
    good = HEAD + HEADER + "| a | b | c | 1 | GAP |\n"
    assert _check(good).exit_code == 0
    assert _check(HEAD + HEADER).exit_code != 0
    assert _check("nothing").exit_code != 0


def test_issue_count_matches_issues() -> None:
    result = _check(HEAD + HEADER + "| a | b | c | 9 | |\n")
    assert result.record_issue_count == len(result.issues) == 2


def test_every_issue_is_an_error_naming_its_rule() -> None:
    result = _check(HEAD + HEADER + "| a | b | c | 9 | |\n")
    assert {i.rule_name for i in result.issues} == _codes(result)
    assert all(i.severity == EnumSeverity.ERROR for i in result.issues)


def test_committed_contract_holds_every_rule_table() -> None:
    contract = ValidatorDesignRecord().contract
    assert contract.validator_id == "design_record"
    assert {rule.rule_id for rule in contract.rules} == RULE_IDS
    by_id = {rule.rule_id: rule.parameters or {} for rule in contract.rules}
    assert by_id["severity_out_of_range"]["severity_levels"] == ["1", "2", "3"]
    assert "tbd" in by_id["row_without_detector_or_gap"]["empty_detector_values"]


def test_removing_an_empty_detector_entry_changes_the_verdict() -> None:
    body = HEAD + HEADER + "| a | b | c | 1 | tbd |\n"
    assert _codes(_check(body)) == {"row_without_detector_or_gap"}

    def drop_tbd(rules: dict[str, dict[str, Any]]) -> None:
        params = rules["row_without_detector_or_gap"]["parameters"]
        params["empty_detector_values"].remove("tbd")

    assert _check(body, _contract_with(drop_tbd)).issues == ()


def test_changing_the_gap_pattern_changes_the_verdict() -> None:
    body = HEAD + HEADER + "| a | b | GAP | 1 | none |\n"
    assert _check(body).issues == ()

    def other_mark(rules: dict[str, dict[str, Any]]) -> None:
        rules["row_without_detector_or_gap"]["parameters"]["gap_pattern"] = r"\bHOLE\b"

    assert _codes(_check(body, _contract_with(other_mark))) == {
        "row_without_detector_or_gap"
    }
    hole = HEAD + HEADER + "| a | b | HOLE | 1 | none |\n"
    assert _codes(_check(hole)) == {"row_without_detector_or_gap"}
    assert _check(hole, _contract_with(other_mark)).issues == ()


def test_severity_four_refused_under_committed_and_accepted_under_fixture() -> None:
    body = HEAD + HEADER + "| a | b | c | 4 | probe |\n"
    assert _codes(_check(body)) == {"severity_out_of_range"}

    def add_four(rules: dict[str, dict[str, Any]]) -> None:
        rules["severity_out_of_range"]["parameters"]["severity_levels"].append("4")

    assert _check(body, _contract_with(add_four)).issues == ()


def test_removing_a_severity_level_changes_the_verdict() -> None:
    body = HEAD + HEADER + "| a | b | c | 3 | probe |\n"
    assert _check(body).issues == ()

    def drop_three(rules: dict[str, dict[str, Any]]) -> None:
        rules["severity_out_of_range"]["parameters"]["severity_levels"].remove("3")

    assert _codes(_check(body, _contract_with(drop_three))) == {"severity_out_of_range"}


def test_a_disabled_rule_reports_no_issue_but_keeps_the_fact() -> None:
    body = HEAD + HEADER + "| a | b | c | 1 | none |\n"

    def disable(rules: dict[str, dict[str, Any]]) -> None:
        rules["row_without_detector_or_gap"]["enabled"] = False

    result = _check(body, _contract_with(disable))
    assert result.issues == ()
    assert result.exit_code == 0
    assert result.rows_without_detector_or_gap == 1


def test_a_contract_missing_a_rule_fails_closed() -> None:
    def drop(rules: dict[str, dict[str, Any]]) -> None:
        del rules["severity_out_of_range"]

    with pytest.raises(ModelOnexError, match="severity_out_of_range"):
        _check(HEAD + HEADER, _contract_with(drop))


def test_checker_module_is_pure() -> None:
    tree = ast.parse(Path(checker_module.__file__).read_text("utf-8"))
    imported = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        node.module.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    assert not imported & {
        "os",
        "pathlib",
        "subprocess",
        "socket",
        "time",
        "datetime",
        "random",
        "urllib",
        "logging",
    }


@pytest.mark.parametrize(
    "name", ["section_11_3_design_record.txt", "violation_severity_out_of_range.txt"]
)
def test_results_are_byte_identical_direct_and_via_validator(
    name: str, tmp_path: Path
) -> None:
    # Exercise file validation outside the contract's fixture exclusion.
    path = tmp_path / name
    path.write_text((FIXTURES / name).read_text("utf-8"), encoding="utf-8")
    validator = ValidatorDesignRecord()
    direct = _check(path.read_text("utf-8"), validator.contract)
    fields = {"code", "message", "severity", "context"}
    expected = json.dumps(
        [issue.model_dump(mode="json", include=fields) for issue in direct.issues]
    )
    assert (
        json.dumps(
            [
                issue.model_dump(mode="json", include=fields)
                for issue in _check(path.read_text("utf-8")).issues
            ]
        )
        == expected
    )
    assert (
        json.dumps(
            [
                issue.model_dump(mode="json", include=fields)
                for issue in validator.validate_file(path).issues
            ]
        )
        == expected
    )


def test_file_validator_reports_issues_at_the_file(tmp_path: Path) -> None:
    good = tmp_path / "good_design_record.md"
    good.write_text((FIXTURES / "section_11_3_design_record.txt").read_text("utf-8"))
    bad = tmp_path / "bad_design_record.md"
    bad.write_text(HEAD + HEADER)
    validator = ValidatorDesignRecord()
    assert validator.validate_file(good).is_valid
    result = validator.validate_file(bad)
    assert not result.is_valid
    assert {issue.file_path for issue in result.issues} == {bad}
    assert {issue.code for issue in result.issues} == {"failure_mode_table_empty"}


@pytest.mark.parametrize("rule_id", sorted(RULE_IDS))
def test_each_violation_fixture_has_exactly_its_one_issue(rule_id: str) -> None:
    result = _check((FIXTURES / f"violation_{rule_id}.txt").read_text("utf-8"))
    assert len(result.issues) == 1
    assert result.issues[0].code == rule_id


@pytest.mark.parametrize("rule_id", sorted(RULE_IDS))
def test_each_clean_fixture_exercises_the_rule_compliantly(rule_id: str) -> None:
    result = _check((FIXTURES / f"clean_{rule_id}.txt").read_text("utf-8"))
    assert result.issues == ()


# Explicit cases make a newly added parameter fail the coverage assertion.
PARAMETER_CASES = [
    ("record_missing", "intended_state_label", "clean_record_missing.txt"),
    ("record_missing", "live_check_command_label", "clean_record_missing.txt"),
    (
        "record_missing",
        "live_check_failing_label",
        "mutation_live_check_failing_label.txt",
    ),
    (
        "failure_mode_table_missing",
        "mode_column",
        "clean_failure_mode_table_missing.txt",
    ),
    (
        "failure_mode_table_missing",
        "severity_column",
        "clean_failure_mode_table_missing.txt",
    ),
    (
        "failure_mode_table_missing",
        "detector_column",
        "clean_failure_mode_table_missing.txt",
    ),
    (
        "row_without_detector_or_gap",
        "empty_detector_values",
        "violation_row_without_detector_or_gap.txt",
    ),
    (
        "row_without_detector_or_gap",
        "gap_pattern",
        "clean_row_without_detector_or_gap.txt",
    ),
    ("severity_out_of_range", "severity_levels", "violation_severity_out_of_range.txt"),
    ("record_missing", "message", "violation_record_missing.txt"),
    ("record_missing", "part", "violation_record_missing.txt"),
    ("intended_state_missing", "message", "violation_intended_state_missing.txt"),
    ("intended_state_missing", "part", "violation_intended_state_missing.txt"),
    (
        "live_check_command_missing",
        "message",
        "violation_live_check_command_missing.txt",
    ),
    ("live_check_command_missing", "part", "violation_live_check_command_missing.txt"),
    (
        "failure_mode_table_missing",
        "message",
        "violation_failure_mode_table_missing.txt",
    ),
    ("failure_mode_table_missing", "part", "violation_failure_mode_table_missing.txt"),
    ("failure_mode_table_empty", "message", "violation_failure_mode_table_empty.txt"),
    ("failure_mode_table_empty", "part", "violation_failure_mode_table_empty.txt"),
    (
        "row_without_detector_or_gap",
        "message",
        "violation_row_without_detector_or_gap.txt",
    ),
    (
        "row_without_detector_or_gap",
        "part",
        "violation_row_without_detector_or_gap.txt",
    ),
    ("severity_out_of_range", "message", "violation_severity_out_of_range.txt"),
    ("severity_out_of_range", "part", "violation_severity_out_of_range.txt"),
]


def test_parameter_mutation_table_covers_every_contract_parameter() -> None:
    expected = {
        (rule.rule_id, key)
        for rule in ValidatorDesignRecord().contract.rules
        for key in (rule.parameters or {})
    }
    actual = [(rule_id, key) for rule_id, key, _ in PARAMETER_CASES]
    assert len(actual) == len(set(actual))
    assert set(actual) == expected


@pytest.mark.parametrize(("rule_id", "key", "fixture"), PARAMETER_CASES)
def test_every_contract_parameter_changes_the_full_issues_json(
    rule_id: str, key: str, fixture: str
) -> None:
    body = (FIXTURES / fixture).read_text("utf-8")

    def mutate(rules: dict[str, dict[str, Any]]) -> None:
        params = rules[rule_id]["parameters"]
        value = params[key]
        if key == "gap_pattern":
            params[key] = r"\bHOLE\b"
        elif key == "empty_detector_values":
            params[key] = [entry for entry in value if entry != "tbd"]
        elif isinstance(value, list):
            params[key] = [*value, "4"]
        else:
            assert isinstance(value, str)
            params[key] = value + "__mutation__"

    def issues_json(contract: ModelValidatorSubcontract) -> str:
        return json.dumps(
            [issue.model_dump(mode="json") for issue in _check(body, contract).issues]
        )

    assert issues_json(_contract_with(mutate)) != issues_json(
        ValidatorDesignRecord().contract
    )


@pytest.mark.parametrize("rule_id", sorted(RULE_IDS))
@pytest.mark.parametrize("key", ["message", "part"])
@pytest.mark.parametrize("value", [None, 42, ["wrong"], True])
def test_required_diagnostics_fail_closed(
    rule_id: str, key: str, value: object
) -> None:
    def mutate(rules: dict[str, dict[str, Any]]) -> None:
        if value is None:
            del rules[rule_id]["parameters"][key]
        else:
            rules[rule_id]["parameters"][key] = value
        rules[rule_id]["enabled"] = False

    with pytest.raises(ModelOnexError, match=rf"{rule_id}:.*{key}.*string"):
        _check(HEAD + HEADER, _contract_with(mutate))


@pytest.mark.parametrize("module", [checker_module, rules_module])
def test_checker_and_rules_hold_no_rule_data_or_diagnostic_literals(
    module: Any,
) -> None:
    tree = ast.parse(Path(module.__file__).read_text("utf-8"))
    literals = [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    ]
    assert not set(literals) & {"tbd", "n/a", "todo", "GAP", "severity", "detector"}
    for rule in ValidatorDesignRecord().contract.rules:
        params = rule.parameters or {}
        message = params["message"]
        assert isinstance(message, str)
        # Check fixed wording even when a template has been split into an f-string.
        wording = [
            text
            for text, _, _, _ in Formatter().parse(message)
            if len(text.strip()) > 12
        ]
        assert not any(text in literal for text in wording for literal in literals)
        assert params["part"] not in literals


@pytest.mark.parametrize("clean", [False, True])
def test_validator_discovers_design_record_in_directory(
    tmp_path: Path, clean: bool
) -> None:
    path = tmp_path / "x_design_record.md"
    name = (
        "clean_failure_mode_table_empty.txt"
        if clean
        else "violation_failure_mode_table_empty.txt"
    )
    path.write_text((FIXTURES / name).read_text("utf-8"), encoding="utf-8")
    validator = ValidatorDesignRecord()
    result = validator.validate(tmp_path)
    assert result.is_valid is clean
    if clean:
        assert result.issues == []
    else:
        assert len(result.issues) == 1
        assert result.issues[0].file_path == path
        assert result.issues[0].code == "failure_mode_table_empty"


@pytest.mark.parametrize(
    ("rule_id", "message", "part"),
    [
        (
            "record_missing",
            "no design record found: no intended state, live check or failure-mode table",
            "design record",
        ),
        (
            "intended_state_missing",
            "the record has no 'Intended state:' sentence",
            "intended state",
        ),
        (
            "live_check_command_missing",
            "the record has no 'Live check command:' line",
            "live check command",
        ),
        (
            "failure_mode_table_missing",
            "the record has no failure-mode table (a table with mode, severity and detector columns)",
            "failure-mode table",
        ),
        (
            "failure_mode_table_empty",
            "the failure-mode table has no rows",
            "failure-mode table",
        ),
        (
            "row_without_detector_or_gap",
            "row 1 has no detector and no GAP mark",
            "failure-mode table",
        ),
        (
            "severity_out_of_range",
            "row 1 severity '4' is not one of 1, 2, 3",
            "failure-mode table",
        ),
    ],
)
def test_original_diagnostic_wording_is_preserved(
    rule_id: str, message: str, part: str
) -> None:
    result = _check((FIXTURES / f"violation_{rule_id}.txt").read_text("utf-8"))
    assert len(result.issues) == 1
    assert result.issues[0].message == message
    assert (result.issues[0].context or {})["part"] == part
