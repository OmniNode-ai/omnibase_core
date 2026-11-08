# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the ``time_bound_truncation`` rules in the generic validator format (OMN-23186).

A function that cuts a duration to whole seconds and then compares it to a limit is refused; the exact compare, a truncation used only for display, a scaled value and the annotated line are admitted.

The checker is pure; the validator reads a module and holds it to its entry in a per-file shrink-only
baseline; every name, marker and remediation text is a ``parameters`` entry of a rule row of
``time_bound_truncation.validation.yaml``. These tests load that contract, so the values that gate the repository are the
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
from omnibase_core.validation.checker_time_bound_truncation import (
    RULE_TIME_BOUND_TRUNCATION,
    check_time_bound_truncation,
)
from omnibase_core.validation.validator_time_bound_truncation import (
    ValidatorTimeBoundTruncation,
)
from tests.unit.validation._time_boundary_bus import ROOT, run_on_bus

pytestmark = pytest.mark.unit

_CONTRACT = (
    ROOT
    / "src/omnibase_core/validation/contracts/time_bound_truncation.validation.yaml"
)
_FIXTURES = ROOT / "tests/fixtures/validation/time_bound_truncation"
_BASELINE = ROOT / ".onex_ratchets/time_bound_truncation_baseline.yaml"
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
    issues = check_time_bound_truncation(_FIXTURE_PATH, source, rules or _rules())
    return [(i.line_number or 0, i.rule_name or "") for i in issues]


def _mutated(rule_id: str, key: str, value: object) -> dict[str, ModelValidatorRule]:
    rules = _rules()
    row = rules[rule_id]
    rules[rule_id] = row.model_copy(
        update={"parameters": {**(row.parameters or {}), key: value}}
    )
    return rules


def _validator(
    tmp_path: Path, baseline: dict[str, int]
) -> ValidatorTimeBoundTruncation:
    return ValidatorTimeBoundTruncation(
        root=tmp_path, baseline=baseline, baseline_path="baseline.txt"
    )


def _plant(tmp_path: Path, name: str, fixture: str) -> Path:
    target = tmp_path / "pkg" / f"{name}.py"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(_source(fixture), encoding="utf-8")
    return target


# fixture -> (line, rule) the rule reports in it (red first: each row is a planted violation)
_T = "time_bound_truncation"
_VIOLATIONS: dict[str, list[tuple[int, str]]] = {
    "violation_probe_age": [(10, _T)],
    "violation_direct_compare": [(2, _T)],
    "violation_floor_forms": [(5, _T), (10, _T)],
}
_PRIMARY_FIXTURE = "violation_probe_age"
_PRIMARY_RULE = RULE_TIME_BOUND_TRUNCATION
_PRIMARY = {RULE_TIME_BOUND_TRUNCATION: "violation_probe_age"}
_ADMITTED = [
    "annotated_truncation_ok",
    "clean_exact_compare",
    "clean_scaled_value",
    "clean_truncated_for_display",
]
_ANNOTATED = {RULE_TIME_BOUND_TRUNCATION: "annotated_truncation_ok"}
_ROWS = {
    RULE_TIME_BOUND_TRUNCATION: {
        "truncating_calls",
        "truncating_operators",
        "duration_methods",
        "comment_prefix",
        "annotation_marker",
        "reason",
        "remediation",
    }
}
_LIST_KEYS = {
    (RULE_TIME_BOUND_TRUNCATION, "truncating_calls"),
    (RULE_TIME_BOUND_TRUNCATION, "duration_methods"),
}
_REQUIRED = {
    (RULE_TIME_BOUND_TRUNCATION, k)
    for k in (
        "truncating_calls",
        "truncating_operators",
        "duration_methods",
        "reason",
        "remediation",
    )
}


@pytest.mark.parametrize(("name", "expected"), sorted(_VIOLATIONS.items()))
def test_time_bound_truncation_refuses_the_planted_violation(
    name: str, expected: list[tuple[int, str]]
) -> None:
    assert _found(_source(name)) == expected


@pytest.mark.parametrize("name", _ADMITTED)
def test_time_bound_truncation_control_admits_the_exact_compare_and_annotated_forms(
    name: str,
) -> None:
    assert _found(_source(name)) == []


def test_time_bound_truncation_flooring_to_a_whole_second_needs_the_floor_operator_row() -> (
    None
):
    source = _source("violation_floor_forms")
    assert len(_found(source)) == 2
    assert len(_found(source, _mutated(_T, "truncating_operators", ["zzz"]))) == 1


def test_time_bound_truncation_fixture_set_is_complete() -> None:
    on_disk = {p.name.removesuffix(".py.txt") for p in _FIXTURES.glob("*.py.txt")}
    assert on_disk == set(_VIOLATIONS) | set(_ADMITTED)


def test_time_bound_truncation_unparseable_source_is_judged_clean() -> None:
    assert _found("def broken(:\n") == []


@pytest.mark.parametrize("rule_id", sorted(_ROWS))
def test_time_bound_truncation_disabled_row_is_not_run(rule_id: str) -> None:
    rules = _rules()
    rules[rule_id] = rules[rule_id].model_copy(update={"enabled": False})
    assert [
        f for f in _found(_source(_PRIMARY[rule_id]), rules) if f[1] == rule_id
    ] == []


@pytest.mark.parametrize("rule_id", sorted(_ROWS))
def test_time_bound_truncation_message_carries_the_rows_reason_line_and_remediation(
    rule_id: str,
) -> None:
    rules = _rules()
    issues = check_time_bound_truncation(
        _FIXTURE_PATH, _source(_PRIMARY[rule_id]), rules
    )
    issue = next(i for i in issues if i.rule_name == rule_id)
    params = rules[rule_id].parameters or {}
    assert str(params["reason"]) in issue.message
    assert str(params["remediation"]) in issue.message
    assert issue.code == rule_id
    assert issue.file_path == _FIXTURE_PATH


@pytest.mark.parametrize("rule_id", sorted(_ROWS))
def test_time_bound_truncation_every_parameter_key_is_exercised_by_the_table(
    rule_id: str,
) -> None:
    keys = set(_rules()[rule_id].parameters or {})
    assert keys == _ROWS[rule_id]


@pytest.mark.parametrize(("rule_id", "key"), sorted(_LIST_KEYS))
def test_time_bound_truncation_emptying_a_name_list_changes_the_verdict(
    rule_id: str, key: str
) -> None:
    source = _source(_PRIMARY[rule_id])
    assert any(f[1] == rule_id for f in _found(source))
    assert [
        f for f in _found(source, _mutated(rule_id, key, ["zzz"])) if f[1] == rule_id
    ] == []


@pytest.mark.parametrize(("rule_id", "annotated"), sorted(_ANNOTATED.items()))
def test_time_bound_truncation_mutating_the_annotation_marker_changes_the_verdict(
    rule_id: str, annotated: str
) -> None:
    assert _found(_source(annotated)) == []
    mutated = _mutated(rule_id, "annotation_marker", "zzz-marker")
    assert any(f[1] == rule_id for f in _found(_source(annotated), mutated))


@pytest.mark.parametrize(
    ("rule_id", "key"),
    sorted({(r, k) for r in _ROWS for k in ("reason", "remediation")}),
)
def test_time_bound_truncation_mutating_a_text_parameter_changes_the_message(
    rule_id: str, key: str
) -> None:
    issues = check_time_bound_truncation(
        _FIXTURE_PATH, _source(_PRIMARY[rule_id]), _mutated(rule_id, key, "zzz-text")
    )
    assert any(i.rule_name == rule_id and "zzz-text" in i.message for i in issues)


@pytest.mark.parametrize(("rule_id", "key"), sorted(_REQUIRED))
def test_time_bound_truncation_a_missing_parameter_fails_the_load(
    rule_id: str, key: str
) -> None:
    row = _rules()[rule_id]
    stripped = {k: v for k, v in (row.parameters or {}).items() if k != key}
    rules = _rules()
    rules[rule_id] = row.model_copy(update={"parameters": stripped})
    with pytest.raises(ModelOnexError):
        check_time_bound_truncation(_FIXTURE_PATH, "", rules)


def test_time_bound_truncation_a_new_finding_in_a_clean_file_is_refused(
    tmp_path: Path,
) -> None:
    target = _plant(tmp_path, "clean_file", _PRIMARY_FIXTURE)
    result = _validator(tmp_path, {}).validate([target])
    assert not result.is_valid
    assert {i.rule_name for i in result.issues} == {_PRIMARY_RULE}


def test_time_bound_truncation_a_baselined_file_at_its_entry_passes(
    tmp_path: Path,
) -> None:
    target = _plant(tmp_path, "old_file", _PRIMARY_FIXTURE)
    entry = {"pkg/old_file.py": len(_VIOLATIONS[_PRIMARY_FIXTURE])}
    assert _validator(tmp_path, entry).validate([target]).is_valid


def test_time_bound_truncation_a_finding_added_to_a_baselined_file_is_refused(
    tmp_path: Path,
) -> None:
    target = _plant(tmp_path, "old_file", _PRIMARY_FIXTURE)
    target.write_text(_source(_PRIMARY_FIXTURE) * 2, encoding="utf-8")
    result = _validator(
        tmp_path, {"pkg/old_file.py": len(_VIOLATIONS[_PRIMARY_FIXTURE])}
    ).validate([target])
    assert not result.is_valid
    assert {i.rule_name for i in result.issues} == {_PRIMARY_RULE, "baseline_ratchet"}


def test_time_bound_truncation_a_fixed_finding_must_lower_the_entry(
    tmp_path: Path,
) -> None:
    target = _plant(tmp_path, "old_file", sorted(_ADMITTED)[0])
    result = _validator(tmp_path, {"pkg/old_file.py": 1}).validate([target])
    assert [i.rule_name for i in result.issues] == ["baseline_ratchet"]


def test_time_bound_truncation_a_baseline_entry_for_a_missing_file_is_refused(
    tmp_path: Path,
) -> None:
    (tmp_path / "baseline.txt").write_text("pkg/gone.py 1\n", encoding="utf-8")
    result = _validator(tmp_path, {"pkg/gone.py": 1}).validate(
        [tmp_path / "baseline.txt"]
    )
    assert [i.rule_name for i in result.issues] == ["baseline_ratchet"]


def test_time_bound_truncation_files_under_tests_are_not_judged(tmp_path: Path) -> None:
    target = tmp_path / "tests" / "test_subject.py"
    target.parent.mkdir(parents=True)
    target.write_text(_source(_PRIMARY_FIXTURE), encoding="utf-8")
    assert _validator(tmp_path, {}).validate([target]).is_valid


def test_time_bound_truncation_the_source_tree_holds_no_finding() -> None:
    rules = _rules()
    found = {
        path.relative_to(ROOT).as_posix(): len(
            check_time_bound_truncation(
                path.relative_to(ROOT), path.read_text(encoding="utf-8"), rules
            )
        )
        for path in sorted(ROOT.glob("src/**/*.py"))
    }
    assert {p: n for p, n in found.items() if n} == {}
    assert (
        ValidatorTimeBoundTruncation(baseline={}).validator_id
        == "time_bound_truncation"
    )


def test_time_bound_truncation_core_adds_no_baseline_file_because_the_tree_holds_no_finding() -> (
    None
):
    assert not _BASELINE.exists()


def test_time_bound_truncation_bus_a_run_puts_one_run_event_and_one_triggered_event_on_the_bus(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = _plant(tmp_path, "planted", _PRIMARY_FIXTURE)
    exit_code, runs, triggered, report_id = run_on_bus(
        ValidatorTimeBoundTruncation, target, tmp_path / "report.json", monkeypatch
    )
    assert exit_code == 1
    assert [run.report_ref for run in runs] == [report_id]
    assert len(triggered) == 1
    assert triggered[0].key == b"time_bound_truncation"


def test_time_bound_truncation_bus_a_clean_run_puts_one_run_event_and_no_triggered_event(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = _plant(tmp_path, "clean", sorted(_ADMITTED)[0])
    exit_code, runs, triggered, _ = run_on_bus(
        ValidatorTimeBoundTruncation, target, tmp_path / "report.json", monkeypatch
    )
    assert exit_code == 0
    assert len(runs) == 1
    assert triggered == []
