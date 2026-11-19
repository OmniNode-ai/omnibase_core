# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the ``unread_outcome_declared`` rule in the generic validator format (OMN-24538).

A node contract whose ``io_operations`` declare an external read must carry an ``unread_outcome``
mapping naming what a failed or absent read yields and the test that holds the handler to it. The red
rows are contracts planted with the shapes the evidence found: a projection reader that cached a day it
could not read as complete, and a receipt reader that counted an unreadable receipt as no lane; the
control rows declare the outcome and name a test that exists, which the rule admits. The checker is
pure (the test file is reached through a resolver the validator supplies); the validator reads the
contract, resolves the named test under its root and holds the contract to its entry in a per-file
shrink-only baseline. A contract that does not parse is a finding, never clean. These tests load
``unread_outcome_declared.validation.yaml``, so the values that gate the repository are the values
under test.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
import yaml

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.validation.checker_unread_outcome_declared import (
    RULE_UNREAD_OUTCOME_DECLARED,
    check_unread_outcome_declared,
)
from omnibase_core.validation.validator_unread_outcome_declared import (
    ValidatorUnreadOutcomeDeclared,
)

pytestmark = pytest.mark.unit

_ROOT = Path(__file__).resolve().parents[3]
_CONTRACT = (
    _ROOT
    / "src/omnibase_core/validation/contracts/unread_outcome_declared.validation.yaml"
)
_FIXTURES = _ROOT / "tests/fixtures/validation/unread_outcome_declared"
_FIXTURE_PATH = Path("src/pkg/nodes/node_x/contract.yaml")
_PRIMARY = "violation_receipt_unreadable_counts_as_no_lane"
_CONTROL = "clean_declares_unread_outcome"
_TEST_FILE = "tests/unit/test_projection_day_reader.py"
_TEST_FUNCTION = "test_projection_refuses_unreadable_day"

# fixture -> the lines the rule reports in it, one entry per finding (red first: each row is planted)
_VIOLATIONS: dict[str, list[int]] = {
    "violation_entry_not_a_mapping": [2, 2],
    "violation_io_operations_not_a_list": [2],
    "violation_not_a_mapping": [1],
    "violation_outcome_empty_mapping": [2, 2],
    "violation_projection_reader_unreadable_day_cached_complete": [5],
    "violation_receipt_unreadable_counts_as_no_lane": [5],
    "violation_returns_empty": [3],
    "violation_test_file_absent": [2],
    "violation_test_function_absent": [2],
    "violation_test_malformed": [2],
    "violation_yaml_unparseable": [2],
}
_ADMITTED = [
    "clean_annotated_failopen_ok",
    "clean_declares_unread_outcome",
    "clean_no_external_read",
    "clean_no_io_operations",
]


def _contract() -> ModelValidatorSubcontract:
    data = yaml.safe_load(_CONTRACT.read_text(encoding="utf-8"))
    return ModelValidatorSubcontract.model_validate(data["validation"])


def _rules() -> dict[str, ModelValidatorRule]:
    return {r.rule_id: r for r in _contract().rules}


def _source(name: str) -> str:
    return (_FIXTURES / f"{name}.yaml.txt").read_text(encoding="utf-8")


def _resolve(relative: str) -> str | None:
    """The named test exists only for the control's own test file, with the function it names."""
    return (
        f"def {_TEST_FUNCTION}() -> None:\n    pass\n"
        if relative == _TEST_FILE
        else None
    )


def _lines(
    source: str, rules: dict[str, ModelValidatorRule] | None = None
) -> list[int]:
    issues = check_unread_outcome_declared(
        _FIXTURE_PATH, source, _resolve, rules or _rules()
    )
    return [i.line_number or 0 for i in issues]


# --- the contract: it loads, and every value it gates on is a parameters entry ---


def test_unread_outcome_declared_the_contract_loads(tmp_path: Path) -> None:
    contract = _contract()
    assert contract.validator_id == RULE_UNREAD_OUTCOME_DECLARED
    assert {r.rule_id for r in contract.rules} == {
        RULE_UNREAD_OUTCOME_DECLARED,
        "baseline_ratchet",
    }
    assert contract.target_patterns == ["**/contract.yaml"]
    # the load probe reads every parameter of the enabled rows and formats every baseline message
    assert ValidatorUnreadOutcomeDeclared(root=tmp_path, baseline={})


# --- the checker: planted violations, admitted controls ---


@pytest.mark.parametrize(("name", "expected"), sorted(_VIOLATIONS.items()))
def test_unread_outcome_declared_refuses_an_external_read_with_no_declared_unread_outcome(
    name: str, expected: list[int]
) -> None:
    assert _lines(_source(name)) == expected


def test_unread_outcome_declared_control_admits_the_contract_that_declares_the_outcome() -> (
    None
):
    assert _lines(_source(_CONTROL)) == []


@pytest.mark.parametrize("name", _ADMITTED)
def test_unread_outcome_declared_admits_the_declared_and_the_annotated_forms(
    name: str,
) -> None:
    assert _lines(_source(name)) == []


def test_unread_outcome_declared_fixture_set_is_complete() -> None:
    on_disk = {p.name.removesuffix(".yaml.txt") for p in _FIXTURES.glob("*.yaml.txt")}
    assert on_disk == set(_VIOLATIONS) | set(_ADMITTED)


def test_unread_outcome_declared_a_missing_test_function_is_refused_where_the_file_exists() -> (
    None
):
    source = _source(_CONTROL).replace(_TEST_FUNCTION, "test_some_other_function")
    issues = check_unread_outcome_declared(_FIXTURE_PATH, source, _resolve, _rules())
    assert [i.message for i in issues if "defines no function" in i.message]


def test_unread_outcome_declared_message_carries_the_reason_the_finding_and_remediation() -> (
    None
):
    params = _rules()[RULE_UNREAD_OUTCOME_DECLARED].parameters or {}
    issues = check_unread_outcome_declared(
        _FIXTURE_PATH, _source(_PRIMARY), _resolve, _rules()
    )
    message = issues[0].message
    assert str(params["reason"]) in message
    assert "<repo-relative file>::<function>" in message
    assert "io_operations:" in message
    assert str(params["remediation"]) in message


def test_unread_outcome_declared_disabled_row_is_not_run() -> None:
    rules = _rules()
    rules[RULE_UNREAD_OUTCOME_DECLARED] = rules[
        RULE_UNREAD_OUTCOME_DECLARED
    ].model_copy(update={"enabled": False})
    assert _lines(_source(_PRIMARY), rules=rules) == []


def _mutated(key: str, value: object) -> dict[str, ModelValidatorRule]:
    rules = _rules()
    row = rules[RULE_UNREAD_OUTCOME_DECLARED]
    rules[RULE_UNREAD_OUTCOME_DECLARED] = row.model_copy(
        update={"parameters": {**(row.parameters or {}), key: value}}
    )
    return rules


_PARAMETER_KEYS = [
    "external_read_types",
    "io_operations",
    "operation_type",
    "unread_outcome",
    "returns",
    "test",
    "test_separator",
    "comment_prefix",
    "annotation_marker",
    "reason",
    "remediation",
]


def test_unread_outcome_declared_every_parameter_key_is_exercised_by_the_table() -> (
    None
):
    assert set(_rules()[RULE_UNREAD_OUTCOME_DECLARED].parameters or {}) == set(
        _PARAMETER_KEYS
    )


def test_unread_outcome_declared_mutating_the_read_types_changes_the_verdict() -> None:
    assert _lines(_source(_PRIMARY)) != []
    assert (
        _lines(_source(_PRIMARY), rules=_mutated("external_read_types", ["zzz"])) == []
    )


def test_unread_outcome_declared_mutating_the_annotation_marker_changes_the_verdict() -> (
    None
):
    annotated = _source("clean_annotated_failopen_ok")
    assert _lines(annotated) == []
    assert _lines(annotated, rules=_mutated("annotation_marker", "zzz-marker")) != []


@pytest.mark.parametrize("key", ["reason", "remediation"])
def test_unread_outcome_declared_mutating_a_text_parameter_changes_the_message(
    key: str,
) -> None:
    issues = check_unread_outcome_declared(
        _FIXTURE_PATH, _source(_PRIMARY), _resolve, _mutated(key, "zzz-text")
    )
    assert issues and "zzz-text" in issues[0].message


@pytest.mark.parametrize("key", _PARAMETER_KEYS)
def test_unread_outcome_declared_a_missing_parameter_fails_the_load(key: str) -> None:
    row = _rules()[RULE_UNREAD_OUTCOME_DECLARED]
    stripped = {k: v for k, v in (row.parameters or {}).items() if k != key}
    rules = _rules()
    rules[RULE_UNREAD_OUTCOME_DECLARED] = row.model_copy(
        update={"parameters": stripped}
    )
    with pytest.raises(ModelOnexError):
        check_unread_outcome_declared(_FIXTURE_PATH, "", _resolve, rules)


# --- the validator: resolves the named test under its root, holds the contract to its baseline ---


def _validator(
    tmp_path: Path, baseline: dict[str, int]
) -> ValidatorUnreadOutcomeDeclared:
    return ValidatorUnreadOutcomeDeclared(
        root=tmp_path, baseline=baseline, baseline_path="baseline.txt"
    )


def _node(tmp_path: Path, fixture: str, *, with_test: bool = True) -> Path:
    node = tmp_path / "src" / "pkg" / "nodes" / "node_x"
    node.mkdir(parents=True, exist_ok=True)
    target = node / "contract.yaml"
    target.write_text(_source(fixture), encoding="utf-8")
    if with_test:
        test = tmp_path / _TEST_FILE
        test.parent.mkdir(parents=True, exist_ok=True)
        test.write_text(
            f"def {_TEST_FUNCTION}() -> None:\n    pass\n", encoding="utf-8"
        )
    return target


def test_unread_outcome_declared_validator_refuses_a_read_with_no_declared_outcome(
    tmp_path: Path,
) -> None:
    result = _validator(tmp_path, {}).validate([_node(tmp_path, _PRIMARY)])
    assert not result.is_valid
    assert [i.line_number for i in result.issues] == [5]


def test_unread_outcome_declared_validator_control_admits_the_declared_outcome(
    tmp_path: Path,
) -> None:
    assert _validator(tmp_path, {}).validate([_node(tmp_path, _CONTROL)]).is_valid


def test_unread_outcome_declared_validator_refuses_a_test_file_that_is_not_in_the_tree(
    tmp_path: Path,
) -> None:
    target = _node(tmp_path, _CONTROL, with_test=False)
    result = _validator(tmp_path, {}).validate([target])
    assert not result.is_valid
    assert "does not exist" in result.issues[0].message


def test_unread_outcome_declared_validator_a_test_path_leaving_the_root_names_no_test(
    tmp_path: Path,
) -> None:
    target = _node(tmp_path, _CONTROL)
    target.write_text(
        _source(_CONTROL).replace(_TEST_FILE, "../outside.py"), encoding="utf-8"
    )
    result = _validator(tmp_path, {}).validate([target])
    assert not result.is_valid
    assert "does not exist" in result.issues[0].message


@pytest.mark.skipif(os.geteuid() == 0, reason="root reads a chmod 000 test file")
def test_unread_outcome_declared_validator_a_test_file_that_cannot_be_read_raises(
    tmp_path: Path,
) -> None:
    target = _node(tmp_path, _CONTROL)
    test = tmp_path / _TEST_FILE
    test.chmod(0o000)
    try:
        with pytest.raises(ModelOnexError) as excinfo:
            _validator(tmp_path, {}).validate([target])
    finally:
        test.chmod(0o644)
    assert excinfo.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR


def test_unread_outcome_declared_validator_admits_a_baselined_finding_and_refuses_growth(
    tmp_path: Path,
) -> None:
    target = _node(tmp_path, _PRIMARY)
    key = target.relative_to(tmp_path).as_posix()
    assert _validator(tmp_path, {key: 1}).validate([target]).is_valid
    grown = _node(tmp_path, "violation_entry_not_a_mapping")
    assert not _validator(tmp_path, {key: 1}).validate([grown]).is_valid


def test_unread_outcome_declared_validator_ignores_files_that_are_not_contracts(
    tmp_path: Path,
) -> None:
    other = tmp_path / "src" / "pkg" / "notes.yaml"
    other.parent.mkdir(parents=True)
    other.write_text(_source(_PRIMARY), encoding="utf-8")
    assert _validator(tmp_path, {}).validate([other]).is_valid
