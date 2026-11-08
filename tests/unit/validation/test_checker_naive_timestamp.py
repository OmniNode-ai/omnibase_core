# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the ``naive_timestamp`` rules in the generic validator format (OMN-23186).

A request or reading model field typed with a naive datetime and a strptime on a request field outside a ValueError handler are refused; an AwareDatetime field, a guarded or literal strptime and the annotated lines are admitted.

The checker is pure; the validator reads a module and holds it to its entry in a per-file shrink-only
baseline; every name, marker and remediation text is a ``parameters`` entry of a rule row of
``naive_timestamp.validation.yaml``. These tests load that contract, so the values that gate the repository are the
values under test.
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
from omnibase_core.validation.checker_naive_timestamp import (
    RULE_NAIVE_DATETIME_FIELD,
    RULE_UNGUARDED_STRPTIME,
    check_naive_timestamp,
)
from omnibase_core.validation.validator_naive_timestamp import (
    ValidatorNaiveTimestamp,
)
from tests.unit.validation._time_boundary_bus import ROOT, run_on_bus

pytestmark = pytest.mark.unit

_CONTRACT = (
    ROOT / "src/omnibase_core/validation/contracts/naive_timestamp.validation.yaml"
)
_FIXTURES = ROOT / "tests/fixtures/validation/naive_timestamp"
_BASELINE = ROOT / ".onex_ratchets/naive_timestamp_baseline.yaml"
_FIXTURE_PATH = Path("src/pkg/subject.py")


def _contract() -> ModelValidatorSubcontract:
    data = yaml.safe_load(_CONTRACT.read_text(encoding="utf-8"))
    return ModelValidatorSubcontract.model_validate(data["validation"])


def _rules() -> dict[str, ModelValidatorRule]:
    return {r.rule_id: r for r in _contract().rules}


def _source(name: str) -> str:
    return (_FIXTURES / f"{name}.py.txt").read_text(encoding="utf-8")


def _found(
    source: str, rules: dict[str, ModelValidatorRule] | None = None
) -> list[tuple[int, str]]:
    issues = check_naive_timestamp(_FIXTURE_PATH, source, rules or _rules())
    return [(i.line_number or 0, i.rule_name or "") for i in issues]


def _mutated(rule_id: str, key: str, value: object) -> dict[str, ModelValidatorRule]:
    rules = _rules()
    row = rules[rule_id]
    rules[rule_id] = row.model_copy(
        update={"parameters": {**(row.parameters or {}), key: value}}
    )
    return rules


def _validator(tmp_path: Path, baseline: dict[str, int]) -> ValidatorNaiveTimestamp:
    return ValidatorNaiveTimestamp(
        root=tmp_path, baseline=baseline, baseline_path="baseline.txt"
    )


def _plant(tmp_path: Path, name: str, fixture: str) -> Path:
    target = tmp_path / "pkg" / f"{name}.py"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(_source(fixture), encoding="utf-8")
    return target


_N = RULE_NAIVE_DATETIME_FIELD
_S = RULE_UNGUARDED_STRPTIME
_VIOLATIONS: dict[str, list[tuple[int, str]]] = {
    "violation_naive_request_field": [(7, _N)],
    "violation_naive_fact_and_optional": [(8, _N), (9, _N)],
    "violation_unguarded_strptime": [(5, _S)],
    "violation_strptime_guarded_for_other_error": [(6, _S)],
}
_PRIMARY_FIXTURE = "violation_naive_request_field"
_PRIMARY_RULE = _N
_PRIMARY = {_N: "violation_naive_request_field", _S: "violation_unguarded_strptime"}
_ADMITTED = [
    "annotated_naive_ok",
    "annotated_strptime_ok",
    "clean_aware_field",
    "clean_guarded_strptime",
]
_ANNOTATED = {_N: "annotated_naive_ok", _S: "annotated_strptime_ok"}
_COMMON = {"comment_prefix", "annotation_marker", "reason", "remediation"}
_ROWS = {
    _N: {"class_name_patterns", "naive_types"} | _COMMON,
    _S: {"parse_methods", "request_roots", "guard_exceptions"} | _COMMON,
}
_LIST_KEYS = {
    (_N, "class_name_patterns"),
    (_N, "naive_types"),
    (_S, "parse_methods"),
    (_S, "request_roots"),
}
_REQUIRED = {
    (_N, "class_name_patterns"),
    (_N, "naive_types"),
    (_S, "parse_methods"),
    (_S, "request_roots"),
    (_S, "guard_exceptions"),
    (_N, "reason"),
    (_S, "remediation"),
}


@pytest.mark.parametrize(("name", "expected"), sorted(_VIOLATIONS.items()))
def test_naive_timestamp_refuses_the_planted_violation(
    name: str, expected: list[tuple[int, str]]
) -> None:
    assert _found(_source(name)) == expected


@pytest.mark.parametrize("name", _ADMITTED)
def test_naive_timestamp_control_admits_the_aware_guarded_and_annotated_forms(
    name: str,
) -> None:
    assert _found(_source(name)) == []


def test_naive_timestamp_the_guard_exceptions_are_a_parameter() -> None:
    source = _source("clean_guarded_strptime")
    assert _found(source) == []
    assert _found(source, _mutated(_S, "guard_exceptions", ["zzz"])) != []


def test_naive_timestamp_fixture_set_is_complete() -> None:
    on_disk = {p.name.removesuffix(".py.txt") for p in _FIXTURES.glob("*.py.txt")}
    assert on_disk == set(_VIOLATIONS) | set(_ADMITTED)


def test_naive_timestamp_unparseable_source_is_judged_clean() -> None:
    assert _found("def broken(:\n") == []


@pytest.mark.parametrize("rule_id", sorted(_ROWS))
def test_naive_timestamp_disabled_row_is_not_run(rule_id: str) -> None:
    rules = _rules()
    rules[rule_id] = rules[rule_id].model_copy(update={"enabled": False})
    assert [
        f for f in _found(_source(_PRIMARY[rule_id]), rules) if f[1] == rule_id
    ] == []


@pytest.mark.parametrize("rule_id", sorted(_ROWS))
def test_naive_timestamp_message_carries_the_rows_reason_line_and_remediation(
    rule_id: str,
) -> None:
    rules = _rules()
    issues = check_naive_timestamp(_FIXTURE_PATH, _source(_PRIMARY[rule_id]), rules)
    issue = next(i for i in issues if i.rule_name == rule_id)
    params = rules[rule_id].parameters or {}
    assert str(params["reason"]) in issue.message
    assert str(params["remediation"]) in issue.message
    assert issue.code == rule_id
    assert issue.file_path == _FIXTURE_PATH


@pytest.mark.parametrize("rule_id", sorted(_ROWS))
def test_naive_timestamp_every_parameter_key_is_exercised_by_the_table(
    rule_id: str,
) -> None:
    keys = set(_rules()[rule_id].parameters or {})
    assert keys == _ROWS[rule_id]


@pytest.mark.parametrize(("rule_id", "key"), sorted(_LIST_KEYS))
def test_naive_timestamp_emptying_a_name_list_changes_the_verdict(
    rule_id: str, key: str
) -> None:
    source = _source(_PRIMARY[rule_id])
    assert any(f[1] == rule_id for f in _found(source))
    assert [
        f for f in _found(source, _mutated(rule_id, key, ["zzz"])) if f[1] == rule_id
    ] == []


@pytest.mark.parametrize(("rule_id", "annotated"), sorted(_ANNOTATED.items()))
def test_naive_timestamp_mutating_the_annotation_marker_changes_the_verdict(
    rule_id: str, annotated: str
) -> None:
    assert _found(_source(annotated)) == []
    mutated = _mutated(rule_id, "annotation_marker", "zzz-marker")
    assert any(f[1] == rule_id for f in _found(_source(annotated), mutated))


@pytest.mark.parametrize(
    ("rule_id", "key"),
    sorted({(r, k) for r in _ROWS for k in ("reason", "remediation")}),
)
def test_naive_timestamp_mutating_a_text_parameter_changes_the_message(
    rule_id: str, key: str
) -> None:
    issues = check_naive_timestamp(
        _FIXTURE_PATH, _source(_PRIMARY[rule_id]), _mutated(rule_id, key, "zzz-text")
    )
    assert any(i.rule_name == rule_id and "zzz-text" in i.message for i in issues)


@pytest.mark.parametrize(("rule_id", "key"), sorted(_REQUIRED))
def test_naive_timestamp_a_missing_parameter_fails_the_load(
    rule_id: str, key: str
) -> None:
    row = _rules()[rule_id]
    stripped = {k: v for k, v in (row.parameters or {}).items() if k != key}
    rules = _rules()
    rules[rule_id] = row.model_copy(update={"parameters": stripped})
    with pytest.raises(ModelOnexError):
        check_naive_timestamp(_FIXTURE_PATH, "", rules)


def test_naive_timestamp_a_new_finding_in_a_clean_file_is_refused(
    tmp_path: Path,
) -> None:
    target = _plant(tmp_path, "clean_file", _PRIMARY_FIXTURE)
    result = _validator(tmp_path, {}).validate([target])
    assert not result.is_valid
    assert {i.rule_name for i in result.issues} == {_PRIMARY_RULE}


def test_naive_timestamp_a_baselined_file_at_its_entry_passes(tmp_path: Path) -> None:
    target = _plant(tmp_path, "old_file", _PRIMARY_FIXTURE)
    entry = {"pkg/old_file.py": len(_VIOLATIONS[_PRIMARY_FIXTURE])}
    assert _validator(tmp_path, entry).validate([target]).is_valid


def test_naive_timestamp_a_finding_added_to_a_baselined_file_is_refused(
    tmp_path: Path,
) -> None:
    target = _plant(tmp_path, "old_file", _PRIMARY_FIXTURE)
    target.write_text(_source(_PRIMARY_FIXTURE) * 2, encoding="utf-8")
    result = _validator(
        tmp_path, {"pkg/old_file.py": len(_VIOLATIONS[_PRIMARY_FIXTURE])}
    ).validate([target])
    assert not result.is_valid
    assert {i.rule_name for i in result.issues} == {_PRIMARY_RULE, "baseline_ratchet"}


def test_naive_timestamp_a_fixed_finding_must_lower_the_entry(tmp_path: Path) -> None:
    target = _plant(tmp_path, "old_file", sorted(_ADMITTED)[0])
    result = _validator(tmp_path, {"pkg/old_file.py": 1}).validate([target])
    assert [i.rule_name for i in result.issues] == ["baseline_ratchet"]


def test_naive_timestamp_a_baseline_entry_for_a_missing_file_is_refused(
    tmp_path: Path,
) -> None:
    (tmp_path / "baseline.txt").write_text("pkg/gone.py 1\n", encoding="utf-8")
    result = _validator(tmp_path, {"pkg/gone.py": 1}).validate(
        [tmp_path / "baseline.txt"]
    )
    assert [i.rule_name for i in result.issues] == ["baseline_ratchet"]


def test_naive_timestamp_files_under_tests_are_not_judged(tmp_path: Path) -> None:
    target = tmp_path / "tests" / "test_subject.py"
    target.parent.mkdir(parents=True)
    target.write_text(_source(_PRIMARY_FIXTURE), encoding="utf-8")
    assert _validator(tmp_path, {}).validate([target]).is_valid


def test_naive_timestamp_the_source_tree_holds_no_finding() -> None:
    rules = _rules()
    found = {
        path.relative_to(ROOT).as_posix(): len(
            check_naive_timestamp(
                path.relative_to(ROOT), path.read_text(encoding="utf-8"), rules
            )
        )
        for path in sorted(ROOT.glob("src/**/*.py"))
    }
    assert {p: n for p, n in found.items() if n} == {}
    assert ValidatorNaiveTimestamp(baseline={}).validator_id == "naive_timestamp"


def test_naive_timestamp_core_adds_no_baseline_file_because_the_tree_holds_no_finding() -> (
    None
):
    assert not _BASELINE.exists()


def test_naive_timestamp_bus_a_run_puts_one_run_event_and_one_triggered_event_on_the_bus(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = _plant(tmp_path, "planted", _PRIMARY_FIXTURE)
    exit_code, runs, triggered, report_id = run_on_bus(
        ValidatorNaiveTimestamp, target, tmp_path / "report.json", monkeypatch
    )
    assert exit_code == 1
    assert [run.report_ref for run in runs] == [report_id]
    assert len(triggered) == 1
    assert triggered[0].key == b"naive_timestamp"


def test_naive_timestamp_bus_a_clean_run_puts_one_run_event_and_no_triggered_event(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = _plant(tmp_path, "clean", sorted(_ADMITTED)[0])
    exit_code, runs, triggered, _ = run_on_bus(
        ValidatorNaiveTimestamp, target, tmp_path / "report.json", monkeypatch
    )
    assert exit_code == 0
    assert len(runs) == 1
    assert triggered == []
