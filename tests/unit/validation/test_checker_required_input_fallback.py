# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the ``required_input_fallback`` rule in the generic validator format (OMN-24538).

A node whose contract declares an input ``required`` must not answer that input's absence with a
made-up value: a ``get`` with a default, a three-argument ``getattr``, an ``or`` over a literal, or
an ``except`` whose body returns a literal (an unreadable receipt counted as no lane, a bad overlay
falling back to a default model, a required field defaulted) all let the handler carry on as if the
input had arrived. The red rows are fixture handlers planted with those shapes; the control rows are
the honest forms -- a ``get`` without a default, a typed raise -- which the rule admits. The checker
is pure; the validator finds the node's contract, reads the inputs it marks required and holds the
module to its entry in a per-file shrink-only baseline. A module that does not parse and a contract
that cannot be read or parsed raise instead of being judged clean. These tests load
``required_input_fallback.validation.yaml``, so the values that gate the repository are the values
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
from omnibase_core.validation.checker_required_input_fallback import (
    RULE_REQUIRED_INPUT_FALLBACK,
    check_required_input_fallback,
    required_inputs,
)
from omnibase_core.validation.validator_required_input_fallback import (
    ValidatorRequiredInputFallback,
)

pytestmark = pytest.mark.unit

_ROOT = Path(__file__).resolve().parents[3]
_CONTRACT = (
    _ROOT
    / "src/omnibase_core/validation/contracts/required_input_fallback.validation.yaml"
)
_FIXTURES = _ROOT / "tests/fixtures/validation/required_input_fallback"
_FIXTURE_PATH = Path("src/pkg/handlers/node_x/handler.py")
_REQUIRED = ("lane", "model")
_NODE_CONTRACT = "inputs:\n  lane:\n    required: true\n  model:\n    required: true\n"

# fixture -> the lines the rule reports in it (red first: each row is a planted violation)
_VIOLATIONS: dict[str, list[int]] = {
    "violation_get_default_lane": [2],
    "violation_get_default_model": [2],
    "violation_getattr_default": [2],
    "violation_or_literal_default": [2],
    "violation_subscript_or_default": [2],
    "violation_except_returns_none": [5],
    "violation_bare_except_returns_none": [5],
    "violation_except_returns_empty_list": [5],
}
_PRIMARY = "violation_get_default_lane"
_CONTROL = "clean_get_no_default"
_ADMITTED = [
    "annotated_failopen_ok",
    "clean_bare_return_in_except",
    "clean_getattr_two_args",
    "clean_get_no_default",
    "clean_optional_input_defaulted",
    "clean_or_non_literal",
    "clean_raises_typed_error",
]


def _contract() -> ModelValidatorSubcontract:
    data = yaml.safe_load(_CONTRACT.read_text(encoding="utf-8"))
    return ModelValidatorSubcontract.model_validate(data["validation"])


def _rules() -> dict[str, ModelValidatorRule]:
    return {r.rule_id: r for r in _contract().rules}


def _source(name: str) -> str:
    return (_FIXTURES / f"{name}.py.txt").read_text(encoding="utf-8")


def _lines(
    source: str,
    required: tuple[str, ...] = _REQUIRED,
    rules: dict[str, ModelValidatorRule] | None = None,
) -> list[int]:
    issues = check_required_input_fallback(
        _FIXTURE_PATH, source, required, rules or _rules()
    )
    return [i.line_number or 0 for i in issues]


# --- the contract: it loads, and every value it gates on is a parameters entry ---


def test_required_input_fallback_the_contract_loads(tmp_path: Path) -> None:
    contract = _contract()
    assert contract.validator_id == RULE_REQUIRED_INPUT_FALLBACK
    assert {r.rule_id for r in contract.rules} == {
        RULE_REQUIRED_INPUT_FALLBACK,
        "baseline_ratchet",
    }
    assert contract.target_patterns == ["**/handlers/**/*.py", "**/handler*.py"]
    # the load probe reads every parameter of the enabled rows and formats every baseline message
    assert ValidatorRequiredInputFallback(root=tmp_path, baseline={})


# --- the checker: planted violations, admitted controls ---


@pytest.mark.parametrize(("name", "expected"), sorted(_VIOLATIONS.items()))
def test_required_input_fallback_refuses_a_made_up_default_for_a_required_input(
    name: str, expected: list[int]
) -> None:
    assert _lines(_source(name)) == expected


def test_required_input_fallback_control_admits_the_handler_that_reads_the_input() -> (
    None
):
    assert _lines(_source(_CONTROL)) == []


@pytest.mark.parametrize("name", _ADMITTED)
def test_required_input_fallback_admits_the_annotated_and_honest_forms(
    name: str,
) -> None:
    assert _lines(_source(name)) == []


def test_required_input_fallback_the_same_default_is_admitted_when_nothing_is_required() -> (
    None
):
    assert _lines(_source(_PRIMARY), required=()) == []


def test_required_input_fallback_fixture_set_is_complete() -> None:
    on_disk = {p.name.removesuffix(".py.txt") for p in _FIXTURES.glob("*.py.txt")}
    assert on_disk == set(_VIOLATIONS) | set(_ADMITTED)


def test_required_input_fallback_message_carries_the_reason_shape_and_remediation() -> (
    None
):
    params = _rules()[RULE_REQUIRED_INPUT_FALLBACK].parameters or {}
    issues = check_required_input_fallback(
        _FIXTURE_PATH, _source(_PRIMARY), _REQUIRED, _rules()
    )
    message = issues[0].message
    assert str(params["reason"]) in message
    assert 'request.get("lane", ...)' in message
    assert "lane, model" in message
    assert 'return request.get("lane", "dev")' in message
    assert str(params["remediation"]) in message


def test_required_input_fallback_unparseable_source_raises_instead_of_being_judged_clean() -> (
    None
):
    with pytest.raises(ModelOnexError):
        _lines("def broken(:\n")


def test_required_input_fallback_disabled_row_is_not_run() -> None:
    rules = _rules()
    rules[RULE_REQUIRED_INPUT_FALLBACK] = rules[
        RULE_REQUIRED_INPUT_FALLBACK
    ].model_copy(update={"enabled": False})
    assert _lines(_source(_PRIMARY), rules=rules) == []


def _mutated(key: str, value: object) -> dict[str, ModelValidatorRule]:
    rules = _rules()
    row = rules[RULE_REQUIRED_INPUT_FALLBACK]
    rules[RULE_REQUIRED_INPUT_FALLBACK] = row.model_copy(
        update={"parameters": {**(row.parameters or {}), key: value}}
    )
    return rules


def test_required_input_fallback_every_parameter_key_is_exercised_by_the_table() -> (
    None
):
    assert set(_rules()[RULE_REQUIRED_INPUT_FALLBACK].parameters or {}) == {
        "contract_file",
        "get_methods",
        "getattr_names",
        "comment_prefix",
        "annotation_marker",
        "reason",
        "remediation",
    }


@pytest.mark.parametrize(
    ("key", "name"),
    [
        ("get_methods", "violation_get_default_lane"),
        ("getattr_names", "violation_getattr_default"),
    ],
)
def test_required_input_fallback_mutating_a_name_list_parameter_changes_the_verdict(
    key: str, name: str
) -> None:
    assert _lines(_source(name)) != []
    assert _lines(_source(name), rules=_mutated(key, ["zzz"])) == []


def test_required_input_fallback_mutating_the_annotation_marker_changes_the_verdict() -> (
    None
):
    annotated = _source("annotated_failopen_ok")
    assert _lines(annotated) == []
    assert _lines(annotated, rules=_mutated("annotation_marker", "zzz-marker")) != []


@pytest.mark.parametrize("key", ["reason", "remediation"])
def test_required_input_fallback_mutating_a_text_parameter_changes_the_message(
    key: str,
) -> None:
    issues = check_required_input_fallback(
        _FIXTURE_PATH, _source(_PRIMARY), _REQUIRED, _mutated(key, "zzz-text")
    )
    assert issues and "zzz-text" in issues[0].message


@pytest.mark.parametrize(
    "key",
    [
        "contract_file",
        "get_methods",
        "getattr_names",
        "comment_prefix",
        "annotation_marker",
        "reason",
        "remediation",
    ],
)
def test_required_input_fallback_a_missing_parameter_fails_the_load(key: str) -> None:
    row = _rules()[RULE_REQUIRED_INPUT_FALLBACK]
    stripped = {k: v for k, v in (row.parameters or {}).items() if k != key}
    rules = _rules()
    rules[RULE_REQUIRED_INPUT_FALLBACK] = row.model_copy(
        update={"parameters": stripped}
    )
    with pytest.raises(ModelOnexError):
        check_required_input_fallback(_FIXTURE_PATH, "", _REQUIRED, rules)


# --- the contract reader: booleans only, and a damaged contract raises ---


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("inputs:\n  lane:\n    required: true\n", ["lane"]),
        ("inputs: {model: {type: str, required: true}}\n", ["model"]),
        ("inputs:\n  lane:\n    required: false\n", []),
        ('inputs:\n  lane:\n    required: "true"\n', []),
        ("inputs:\n  lane:\n    type: str\n", []),
        ("steps:\n  - inputs:\n      lane:\n        required: true\n", ["lane"]),
        (
            "a:\n  inputs:\n    lane:\n      required: true\nb:\n  inputs:\n    lane:\n      required: true\n",
            ["lane"],
        ),
        (
            "inputs:\n    lane:\n      required: true\n    model:\n      required: true\n",
            ["lane", "model"],
        ),
    ],
)
def test_required_input_fallback_required_inputs_reads_only_a_boolean_required(
    text: str, expected: list[str]
) -> None:
    assert list(required_inputs(text)) == expected


@pytest.mark.parametrize("text", ["", "not: [valid\n", "- one\n- two\n"])
def test_required_input_fallback_a_damaged_contract_raises(text: str) -> None:
    with pytest.raises(ModelOnexError) as excinfo:
        required_inputs(text)
    assert excinfo.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR


# --- the validator: finds the node's contract, holds the module to its baseline entry ---


def _validator(
    tmp_path: Path, baseline: dict[str, int]
) -> ValidatorRequiredInputFallback:
    return ValidatorRequiredInputFallback(
        root=tmp_path, baseline=baseline, baseline_path="baseline.txt"
    )


def _node(
    tmp_path: Path,
    fixture: str,
    contract: str | None = _NODE_CONTRACT,
) -> Path:
    node = tmp_path / "src" / "pkg" / "handlers" / "node_x"
    node.mkdir(parents=True, exist_ok=True)
    if contract is not None:
        (node / "contract.yaml").write_text(contract, encoding="utf-8")
    target = node / "handler.py"
    target.write_text(_source(fixture), encoding="utf-8")
    return target


def test_required_input_fallback_validator_refuses_a_default_in_a_node_that_requires_the_input(
    tmp_path: Path,
) -> None:
    result = _validator(tmp_path, {}).validate([_node(tmp_path, _PRIMARY)])
    assert not result.is_valid
    assert [i.line_number for i in result.issues] == [2]


def test_required_input_fallback_validator_control_admits_the_handler_that_reads_the_input(
    tmp_path: Path,
) -> None:
    assert _validator(tmp_path, {}).validate([_node(tmp_path, _CONTROL)]).is_valid


def test_required_input_fallback_validator_reads_the_flow_form_of_the_contract(
    tmp_path: Path,
) -> None:
    target = _node(
        tmp_path, _PRIMARY, contract="inputs: {lane: {type: str, required: true}}\n"
    )
    assert not _validator(tmp_path, {}).validate([target]).is_valid


def test_required_input_fallback_validator_admits_a_node_that_requires_nothing(
    tmp_path: Path,
) -> None:
    target = _node(tmp_path, _PRIMARY, contract="inputs:\n  lane:\n    type: str\n")
    assert _validator(tmp_path, {}).validate([target]).is_valid


def test_required_input_fallback_validator_admits_a_module_with_no_node_contract(
    tmp_path: Path,
) -> None:
    assert _validator(tmp_path, {}).validate([_node(tmp_path, _PRIMARY, None)]).is_valid


def test_required_input_fallback_validator_judges_the_nearest_ancestor_contract(
    tmp_path: Path,
) -> None:
    handlers = tmp_path / "src" / "pkg" / "handlers"
    node = handlers / "node_x"
    node.mkdir(parents=True)
    (handlers / "contract.yaml").write_text(
        "inputs:\n  lane:\n    required: true\n", encoding="utf-8"
    )
    (node / "contract.yaml").write_text(
        "inputs:\n  lane:\n    type: str\n", encoding="utf-8"
    )
    target = node / "handler.py"
    target.write_text(_source(_PRIMARY), encoding="utf-8")
    assert _validator(tmp_path, {}).validate([target]).is_valid


def test_required_input_fallback_validator_reads_a_contract_from_a_higher_directory(
    tmp_path: Path,
) -> None:
    handlers = tmp_path / "src" / "pkg" / "handlers"
    node = handlers / "node_x"
    node.mkdir(parents=True)
    (handlers / "contract.yaml").write_text(
        "inputs:\n  model:\n    required: true\n", encoding="utf-8"
    )
    target = node / "handler.py"
    target.write_text(_source("violation_get_default_model"), encoding="utf-8")
    assert not _validator(tmp_path, {}).validate([target]).is_valid


def test_required_input_fallback_validator_a_contract_that_does_not_parse_raises(
    tmp_path: Path,
) -> None:
    target = _node(tmp_path, _PRIMARY, contract="not: [valid\n")
    with pytest.raises(ModelOnexError) as excinfo:
        _validator(tmp_path, {}).validate([target])
    assert excinfo.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR


@pytest.mark.skipif(os.geteuid() == 0, reason="root reads a chmod 000 contract")
def test_required_input_fallback_validator_a_contract_that_cannot_be_read_raises(
    tmp_path: Path,
) -> None:
    target = _node(tmp_path, _PRIMARY)
    contract = target.parent / "contract.yaml"
    contract.chmod(0o000)
    try:
        with pytest.raises(ModelOnexError) as excinfo:
            _validator(tmp_path, {}).validate([target])
    finally:
        contract.chmod(0o644)
    assert excinfo.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR


def test_required_input_fallback_validator_a_changed_contract_file_name_changes_discovery(
    tmp_path: Path,
) -> None:
    target = _node(tmp_path, _PRIMARY)
    row = _rules()[RULE_REQUIRED_INPUT_FALLBACK]
    renamed = row.model_copy(
        update={"parameters": {**(row.parameters or {}), "contract_file": "zzz.yaml"}}
    )
    contract = _contract().model_copy(
        update={
            "rules": [
                renamed if r.rule_id == RULE_REQUIRED_INPUT_FALLBACK else r
                for r in _contract().rules
            ]
        }
    )
    validator = ValidatorRequiredInputFallback(
        contract=contract, root=tmp_path, baseline={}
    )
    assert validator.validate([target]).is_valid


# --- the baseline_ratchet rule: shrink-only per-file entries ---


def test_required_input_fallback_a_baselined_file_at_its_entry_passes(
    tmp_path: Path,
) -> None:
    target = _node(tmp_path, _PRIMARY)
    key = target.relative_to(tmp_path).as_posix()
    assert _validator(tmp_path, {key: 1}).validate([target]).is_valid


def test_required_input_fallback_a_finding_added_to_a_baselined_file_is_refused(
    tmp_path: Path,
) -> None:
    target = _node(tmp_path, _PRIMARY)
    target.write_text(
        target.read_text(encoding="utf-8")
        + '\n\ndef again(request):\n    return request.get("lane", "dev")\n',
        encoding="utf-8",
    )
    key = target.relative_to(tmp_path).as_posix()
    assert not _validator(tmp_path, {key: 1}).validate([target]).is_valid


def test_required_input_fallback_a_fixed_finding_must_lower_the_entry(
    tmp_path: Path,
) -> None:
    target = _node(tmp_path, _CONTROL)
    key = target.relative_to(tmp_path).as_posix()
    assert not _validator(tmp_path, {key: 1}).validate([target]).is_valid


def test_required_input_fallback_a_baseline_entry_for_a_missing_file_is_refused(
    tmp_path: Path,
) -> None:
    baseline = tmp_path / "baseline.txt"
    baseline.write_text("src/pkg/handlers/node_x/gone.py: 1\n", encoding="utf-8")
    assert (
        not _validator(tmp_path, {"src/pkg/handlers/node_x/gone.py": 1})
        .validate([baseline])
        .is_valid
    )


def test_required_input_fallback_files_under_tests_are_not_judged(
    tmp_path: Path,
) -> None:
    node = tmp_path / "src" / "pkg" / "handlers" / "node_x" / "tests"
    node.mkdir(parents=True)
    (node.parent / "contract.yaml").write_text(_NODE_CONTRACT, encoding="utf-8")
    target = node / "test_handler.py"
    target.write_text(_source(_PRIMARY), encoding="utf-8")
    assert _validator(tmp_path, {}).validate([target]).is_valid


def test_required_input_fallback_a_module_outside_the_handler_scope_is_not_judged(
    tmp_path: Path,
) -> None:
    node = tmp_path / "src" / "pkg" / "services" / "node_x"
    node.mkdir(parents=True)
    (node / "contract.yaml").write_text(_NODE_CONTRACT, encoding="utf-8")
    target = node / "service.py"
    target.write_text(_source(_PRIMARY), encoding="utf-8")
    assert _validator(tmp_path, {}).validate([target]).is_valid
