# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the ``declared_timeout`` rule in the generic validator format (OMN-23187, validators plan).

A node whose contract or overlay declares a time limit must pass a limit to every blocking subprocess
or network call its handler makes. The red rows are a fixture handler with a declared limit and a bare
``subprocess.run``; the control rows are a handler that passes the declared limit, which the rule admits.
The checker is pure; the validator finds the node's contract, reads its declared limit and holds the module
to its entry in a per-file shrink-only baseline. These tests load ``declared_timeout.validation.yaml``, so
the values that gate the repository are the values under test.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.validation.checker_declared_timeout import (
    RULE_DECLARED_TIMEOUT,
    check_declared_timeout,
    declared_timeout_keys,
)
from omnibase_core.validation.checker_detector_common import parse_baseline
from omnibase_core.validation.validator_declared_timeout import (
    ValidatorDeclaredTimeout,
)

pytestmark = pytest.mark.unit

_ROOT = Path(__file__).resolve().parents[3]
_CONTRACT = (
    _ROOT / "src/omnibase_core/validation/contracts/declared_timeout.validation.yaml"
)
_FIXTURES = _ROOT / "tests/fixtures/validation/declared_timeout"
_BASELINE = _ROOT / ".onex_ratchets/declared_timeout_baseline.yaml"
_FIXTURE_PATH = Path("src/pkg/nodes/node_x/handler.py")
_DECLARED = ("descriptor.timeout_ms",)

# fixture -> the lines the rule reports in it (red first: each row is a planted violation)
_VIOLATIONS: dict[str, list[int]] = {
    "violation_bare_subprocess_run": [5],
    "violation_timeout_none": [5],
    "violation_aliased_import": [5],
    "violation_network_call": [5],
}
_PRIMARY = "violation_bare_subprocess_run"
_CONTROL = "clean_passes_declared_timeout"
_ADMITTED = [
    "clean_passes_declared_timeout",
    "clean_kwargs_expansion",
    "annotated_timeout_ok",
    "clean_non_blocking_name",
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
    declared: tuple[str, ...] = _DECLARED,
    rules: dict[str, ModelValidatorRule] | None = None,
) -> list[int]:
    issues = check_declared_timeout(_FIXTURE_PATH, source, declared, rules or _rules())
    return [i.line_number or 0 for i in issues]


@pytest.mark.parametrize(("name", "expected"), sorted(_VIOLATIONS.items()))
def test_declared_timeout_refuses_a_call_with_no_limit_while_one_is_declared(
    name: str, expected: list[int]
) -> None:
    assert _lines(_source(name)) == expected


def test_declared_timeout_control_admits_the_handler_that_passes_the_limit() -> None:
    assert _lines(_source(_CONTROL)) == []


@pytest.mark.parametrize("name", _ADMITTED)
def test_declared_timeout_admits_the_limited_annotated_and_non_blocking_forms(
    name: str,
) -> None:
    assert _lines(_source(name)) == []


def test_declared_timeout_the_same_bare_call_is_admitted_when_nothing_is_declared() -> (
    None
):
    assert _lines(_source(_PRIMARY), declared=()) == []


def test_declared_timeout_fixture_set_is_complete() -> None:
    on_disk = {p.name.removesuffix(".py.txt") for p in _FIXTURES.glob("*.py.txt")}
    assert on_disk == set(_VIOLATIONS) | set(_ADMITTED)


def test_declared_timeout_message_carries_the_reason_call_declaration_and_remediation() -> (
    None
):
    params = _rules()[RULE_DECLARED_TIMEOUT].parameters or {}
    issues = check_declared_timeout(
        _FIXTURE_PATH, _source(_PRIMARY), _DECLARED, _rules()
    )
    message = issues[0].message
    assert str(params["reason"]) in message
    assert "subprocess.run" in message
    assert "descriptor.timeout_ms" in message
    assert "subprocess.run(" in message
    assert str(params["remediation"]) in message


def test_declared_timeout_unparseable_source_is_judged_clean() -> None:
    assert _lines("def broken(:\n") == []


def test_declared_timeout_disabled_row_is_not_run() -> None:
    rules = _rules()
    rules[RULE_DECLARED_TIMEOUT] = rules[RULE_DECLARED_TIMEOUT].model_copy(
        update={"enabled": False}
    )
    assert _lines(_source(_PRIMARY), rules=rules) == []
    assert declared_timeout_keys(("timeout_ms: 5\n",), rules) == ()


def _mutated(key: str, value: object) -> dict[str, ModelValidatorRule]:
    rules = _rules()
    row = rules[RULE_DECLARED_TIMEOUT]
    rules[RULE_DECLARED_TIMEOUT] = row.model_copy(
        update={"parameters": {**(row.parameters or {}), key: value}}
    )
    return rules


def test_declared_timeout_every_parameter_key_is_exercised_by_the_table() -> None:
    assert set(_rules()[RULE_DECLARED_TIMEOUT].parameters or {}) == {
        "contract_file",
        "overlay_globs",
        "declaring_key_pattern",
        "blocking_calls",
        "timeout_keyword",
        "comment_prefix",
        "annotation_marker",
        "reason",
        "remediation",
    }


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("blocking_calls", ["zzz.call"]),
        ("timeout_keyword", "zzz_limit"),
    ],
)
def test_declared_timeout_mutating_a_pattern_parameter_changes_the_verdict(
    key: str, value: object
) -> None:
    assert _lines(_source(_PRIMARY)) != []
    assert _lines(_source(_PRIMARY), rules=_mutated(key, value)) == (
        [] if key == "blocking_calls" else _lines(_source(_PRIMARY))
    )
    # the control passes timeout=, so renaming the keyword makes it a violation
    if key == "timeout_keyword":
        assert _lines(_source(_CONTROL), rules=_mutated(key, value)) != []


def test_declared_timeout_mutating_the_annotation_marker_changes_the_verdict() -> None:
    annotated = _source("annotated_timeout_ok")
    assert _lines(annotated) == []
    assert _lines(annotated, rules=_mutated("annotation_marker", "zzz-marker")) != []


@pytest.mark.parametrize("key", ["reason", "remediation"])
def test_declared_timeout_mutating_a_text_parameter_changes_the_message(
    key: str,
) -> None:
    issues = check_declared_timeout(
        _FIXTURE_PATH, _source(_PRIMARY), _DECLARED, _mutated(key, "zzz-text")
    )
    assert issues and "zzz-text" in issues[0].message


@pytest.mark.parametrize(
    "key", ["blocking_calls", "timeout_keyword", "reason", "remediation"]
)
def test_declared_timeout_a_missing_parameter_fails_the_load(key: str) -> None:
    row = _rules()[RULE_DECLARED_TIMEOUT]
    stripped = {k: v for k, v in (row.parameters or {}).items() if k != key}
    rules = _rules()
    rules[RULE_DECLARED_TIMEOUT] = row.model_copy(update={"parameters": stripped})
    with pytest.raises(ModelOnexError):
        check_declared_timeout(_FIXTURE_PATH, "", _DECLARED, rules)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("timeout_ms: 5000\n", ["timeout_ms"]),
        ("descriptor:\n  timeout_seconds: 30\n", ["descriptor.timeout_seconds"]),
        ("steps:\n  - default_timeout_s: 2\n", ["steps[0].default_timeout_s"]),
        ("must_not_timeout: true\n", []),
        ("timeout_ms: null\n", []),
        ("timeout_behavior: fail\n", []),
        ("not: [valid\n", []),
    ],
)
def test_declared_timeout_keys_read_only_numeric_limits(
    text: str, expected: list[str]
) -> None:
    assert list(declared_timeout_keys((text,), _rules())) == expected


def test_declared_timeout_a_changed_declaring_pattern_changes_what_is_declared() -> (
    None
):
    rules = _mutated("declaring_key_pattern", "zzz")
    assert declared_timeout_keys(("timeout_ms: 5\n",), rules) == ()


# --- the validator: finds the node's contract, holds the module to its baseline entry ---


def _validator(tmp_path: Path, baseline: dict[str, int]) -> ValidatorDeclaredTimeout:
    return ValidatorDeclaredTimeout(
        root=tmp_path, baseline=baseline, baseline_path="baseline.txt"
    )


def _node(
    tmp_path: Path,
    fixture: str,
    contract: str | None = "descriptor:\n  timeout_ms: 30000\n",
    overlay: str | None = None,
) -> Path:
    node = tmp_path / "src" / "pkg" / "nodes" / "node_x"
    node.mkdir(parents=True, exist_ok=True)
    if contract is not None:
        (node / "contract.yaml").write_text(contract, encoding="utf-8")
    if overlay is not None:
        (node / "overlays").mkdir(exist_ok=True)
        (node / "overlays" / "x.inmemory.overlay.yaml").write_text(
            overlay, encoding="utf-8"
        )
    target = node / "handler.py"
    target.write_text(_source(fixture), encoding="utf-8")
    return target


def test_declared_timeout_validator_refuses_a_bare_call_in_a_node_that_declares_a_limit(
    tmp_path: Path,
) -> None:
    result = _validator(tmp_path, {}).validate([_node(tmp_path, _PRIMARY)])
    assert not result.is_valid
    assert [i.line_number for i in result.issues] == [5]


def test_declared_timeout_validator_control_admits_the_call_that_passes_the_limit(
    tmp_path: Path,
) -> None:
    assert _validator(tmp_path, {}).validate([_node(tmp_path, _CONTROL)]).is_valid


def test_declared_timeout_validator_reads_the_limit_from_an_overlay(
    tmp_path: Path,
) -> None:
    target = _node(
        tmp_path, _PRIMARY, contract="descriptor: {}\n", overlay="timeout_seconds: 9\n"
    )
    assert not _validator(tmp_path, {}).validate([target]).is_valid


def test_declared_timeout_validator_admits_a_node_that_declares_no_limit(
    tmp_path: Path,
) -> None:
    target = _node(tmp_path, _PRIMARY, contract="descriptor: {}\n")
    assert _validator(tmp_path, {}).validate([target]).is_valid


def test_declared_timeout_validator_admits_a_module_with_no_node_contract(
    tmp_path: Path,
) -> None:
    target = _node(tmp_path, _PRIMARY, contract=None)
    assert _validator(tmp_path, {}).validate([target]).is_valid


def test_declared_timeout_a_baselined_file_at_its_entry_passes(
    tmp_path: Path,
) -> None:
    target = _node(tmp_path, _PRIMARY)
    key = target.relative_to(tmp_path).as_posix()
    assert _validator(tmp_path, {key: 1}).validate([target]).is_valid


def test_declared_timeout_a_finding_added_to_a_baselined_file_is_refused(
    tmp_path: Path,
) -> None:
    target = _node(tmp_path, _PRIMARY)
    target.write_text(
        target.read_text(encoding="utf-8")
        + "\n\ndef again(request):\n    return subprocess.run(['ls'])\n",
        encoding="utf-8",
    )
    key = target.relative_to(tmp_path).as_posix()
    assert not _validator(tmp_path, {key: 1}).validate([target]).is_valid


def test_declared_timeout_a_fixed_finding_must_lower_the_entry(tmp_path: Path) -> None:
    target = _node(tmp_path, _CONTROL)
    key = target.relative_to(tmp_path).as_posix()
    assert not _validator(tmp_path, {key: 1}).validate([target]).is_valid


def test_declared_timeout_a_baseline_entry_for_a_missing_file_is_refused(
    tmp_path: Path,
) -> None:
    baseline = tmp_path / "baseline.txt"
    baseline.write_text("src/pkg/nodes/node_x/gone.py: 1\n", encoding="utf-8")
    assert (
        not _validator(tmp_path, {"src/pkg/nodes/node_x/gone.py": 1})
        .validate([baseline])
        .is_valid
    )


def test_declared_timeout_files_under_tests_are_not_judged(tmp_path: Path) -> None:
    node = tmp_path / "src" / "pkg" / "nodes" / "node_x" / "tests"
    node.mkdir(parents=True)
    (node.parent / "contract.yaml").write_text("timeout_ms: 5\n", encoding="utf-8")
    target = node / "test_handler.py"
    target.write_text(_source(_PRIMARY), encoding="utf-8")
    assert _validator(tmp_path, {}).validate([target]).is_valid


def test_declared_timeout_baseline_header_names_the_burn_down_ticket_and_a_zero_target() -> (
    None
):
    header = [
        line
        for line in _BASELINE.read_text(encoding="utf-8").splitlines()
        if line.startswith("#")
    ]
    assert any("Burn-down ticket: OMN-23187" in line for line in header)
    assert any("Zero target:" in line for line in header)


def test_declared_timeout_the_checked_in_baseline_equals_the_findings_of_the_tree() -> (
    None
):
    baseline = parse_baseline(_BASELINE.read_text(encoding="utf-8"))
    assert baseline
    validator = ValidatorDeclaredTimeout(baseline={})
    found: dict[str, int] = {}
    for key in baseline:
        path = _ROOT / key
        assert path.is_file(), key
        issues = validator._judge(Path(key), path.read_text(encoding="utf-8"), _rules())
        found[key] = len(issues)
    assert found == baseline


@pytest.mark.parametrize("text", ["", "[]", "not: [valid", "a: b"])
def test_declared_timeout_a_damaged_baseline_holds_no_entries(text: str) -> None:
    assert parse_baseline(text) == {}
