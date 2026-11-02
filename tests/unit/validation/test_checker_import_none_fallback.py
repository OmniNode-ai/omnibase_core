# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the ``import_none_fallback`` rule in the generic validator format (OMN-22005, plan task T2.4, replacing OMN-10819).

An ImportError handler that assigns a symbol to None is refused; a raise, a real fallback, another exception and the annotated line are admitted. The checker is pure; the validator reads a module and holds it to its entry in a per-file
shrink-only baseline; every name, marker and remediation text is a ``parameters`` entry of a rule
row of ``import_none_fallback.validation.yaml``. These tests load that contract, so the values that gate the
repository are the values under test.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
import yaml

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.event_bus import event_bus_inmemory
from omnibase_core.event_bus.event_bus_inmemory import EventBusInmemory
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.event_bus.model_event_message import ModelEventMessage
from omnibase_core.models.validation.model_validator_run_event import (
    ModelValidatorRunEvent,
)
from omnibase_core.nodes.node_validation_report_write_effect import (
    handler_validator_runtime_overlay,
)
from omnibase_core.nodes.node_validation_report_write_effect.handler_validator_runtime_overlay import (
    HandlerValidatorRuntimeOverlay,
)
from omnibase_core.nodes.node_validation_report_write_effect.runtime_validator_run import (
    build_validator_container,
    main,
)
from omnibase_core.topics import TopicBase
from omnibase_core.validation.checker_detector_common import parse_baseline
from omnibase_core.validation.checker_import_none_fallback import (
    RULE_IMPORT_NONE_FALLBACK,
    check_import_none_fallback,
)
from omnibase_core.validation.validator_import_none_fallback import (
    ValidatorImportNoneFallback,
)
from tests.unit.validation._detector_reference import import_none_fallback_lines

pytestmark = pytest.mark.unit

_ROOT = Path(__file__).resolve().parents[3]
_CONTRACT = (
    _ROOT
    / "src/omnibase_core/validation/contracts/import_none_fallback.validation.yaml"
)
_FIXTURES = _ROOT / "tests/fixtures/validation/import_none_fallback"
_BASELINE = _ROOT / ".onex_ratchets/import_none_fallback_baseline.yaml"
_NODE = Path(handler_validator_runtime_overlay.__file__).resolve().parent
_INMEMORY = _NODE / "overlays/validator_runtime.inmemory.overlay.yaml"
_HANDLER = HandlerValidatorRuntimeOverlay()
_RUN_TOPIC = _HANDLER.settings().run_topic
_FIXTURE_PATH = Path("src/pkg/subject.py")

# fixture -> the lines the rule reports in it (red first: each row is a planted violation)
_VIOLATIONS: dict[str, list[int]] = {
    "violation_import_error": [4],
    "violation_module_not_found_tuple": [4],
    "violation_multi_target": [4, 4],
}
_PRIMARY = "violation_import_error"
_ADMITTED = [
    "annotated_import_fallback_ok",
    "clean_other_exception",
    "clean_raise",
    "clean_real_fallback",
]


def _contract() -> ModelValidatorSubcontract:
    data = yaml.safe_load(_CONTRACT.read_text(encoding="utf-8"))
    return ModelValidatorSubcontract.model_validate(data["validation"])


def _rules(
    contract: ModelValidatorSubcontract | None = None,
) -> dict[str, ModelValidatorRule]:
    return {r.rule_id: r for r in (contract or _contract()).rules}


def _marker() -> str:
    params = _rules()[RULE_IMPORT_NONE_FALLBACK].parameters or {}
    return str(params["comment_prefix"]) + str(params["annotation_marker"])


def _source(name: str) -> str:
    return (_FIXTURES / f"{name}.py.txt").read_text(encoding="utf-8")


def _lines(
    source: str, rules: dict[str, ModelValidatorRule] | None = None
) -> list[int]:
    issues = check_import_none_fallback(_FIXTURE_PATH, source, rules or _rules())
    return [i.line_number or 0 for i in issues]


@pytest.mark.parametrize(("name", "expected"), sorted(_VIOLATIONS.items()))
def test_import_none_fallback_refuses_the_planted_violation(
    name: str, expected: list[int]
) -> None:
    assert _lines(_source(name)) == expected


@pytest.mark.parametrize("name", _ADMITTED)
def test_import_none_fallback_admits_the_annotated_and_clean_forms(name: str) -> None:
    assert _lines(_source(name)) == []


def test_import_none_fallback_fixture_set_is_complete() -> None:
    on_disk = {p.name.removesuffix(".py.txt") for p in _FIXTURES.glob("*.py.txt")}
    assert on_disk == set(_VIOLATIONS) | set(_ADMITTED)


def test_import_none_fallback_message_carries_the_rows_reason_line_and_remediation() -> (
    None
):
    rules = _rules()
    issue = check_import_none_fallback(_FIXTURE_PATH, _source(_PRIMARY), rules)[0]
    params = rules[RULE_IMPORT_NONE_FALLBACK].parameters or {}
    assert str(params["reason"]) in issue.message
    assert str(params["remediation"]) in issue.message
    assert issue.code == RULE_IMPORT_NONE_FALLBACK
    assert issue.file_path == _FIXTURE_PATH


def test_import_none_fallback_unparseable_source_is_judged_clean() -> None:
    assert _lines("def broken(:\n") == []


def test_import_none_fallback_disabled_row_is_not_run() -> None:
    rules = _rules()
    rules[RULE_IMPORT_NONE_FALLBACK] = rules[RULE_IMPORT_NONE_FALLBACK].model_copy(
        update={"enabled": False}
    )
    assert _lines(_source(_PRIMARY), rules) == []


def _mutated(key: str, value: object) -> dict[str, ModelValidatorRule]:
    rules = _rules()
    row = rules[RULE_IMPORT_NONE_FALLBACK]
    rules[RULE_IMPORT_NONE_FALLBACK] = row.model_copy(
        update={"parameters": {**(row.parameters or {}), key: value}}
    )
    return rules


def test_import_none_fallback_every_parameter_key_is_exercised_by_the_table() -> None:
    keys = set(_rules()[RULE_IMPORT_NONE_FALLBACK].parameters or {})
    assert keys == {"import_errors", "comment_prefix", "annotation_marker"} | {
        "reason",
        "remediation",
    }


@pytest.mark.parametrize(
    "key", ["import_errors", "comment_prefix", "annotation_marker"]
)
def test_import_none_fallback_mutating_a_pattern_parameter_changes_the_verdict(
    key: str,
) -> None:
    violation = _source(_PRIMARY)
    annotated = _source("annotated_import_fallback_ok")
    if key in ("annotation_marker", "comment_prefix"):
        assert _lines(annotated) == []
        assert _lines(annotated, _mutated(key, "zzz-marker")) != []
    else:
        assert _lines(violation) != []
        assert _lines(violation, _mutated(key, ["zzz"])) == []


@pytest.mark.parametrize("key", ["reason", "remediation"])
def test_import_none_fallback_mutating_a_text_parameter_changes_the_message(
    key: str,
) -> None:
    source = _source(_PRIMARY)
    issues = check_import_none_fallback(
        _FIXTURE_PATH, source, _mutated(key, "zzz-text")
    )
    assert issues and "zzz-text" in issues[0].message


@pytest.mark.parametrize("key", ["import_errors", "reason", "remediation"])
def test_import_none_fallback_a_missing_parameter_fails_the_load(key: str) -> None:
    row = _rules()[RULE_IMPORT_NONE_FALLBACK]
    stripped = {k: v for k, v in (row.parameters or {}).items() if k != key}
    rules = _rules()
    rules[RULE_IMPORT_NONE_FALLBACK] = row.model_copy(update={"parameters": stripped})
    with pytest.raises(ModelOnexError):
        check_import_none_fallback(_FIXTURE_PATH, "", rules)


def _validator(tmp_path: Path, baseline: dict[str, int]) -> ValidatorImportNoneFallback:
    return ValidatorImportNoneFallback(
        root=tmp_path, baseline=baseline, baseline_path="baseline.txt"
    )


def _plant(tmp_path: Path, name: str, fixture: str) -> Path:
    target = tmp_path / "pkg" / f"{name}.py"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(_source(fixture), encoding="utf-8")
    return target


def test_import_none_fallback_a_new_finding_in_a_clean_file_is_refused(
    tmp_path: Path,
) -> None:
    target = _plant(tmp_path, "clean_file", _PRIMARY)
    result = _validator(tmp_path, {}).validate([target])
    assert not result.is_valid
    assert [i.rule_name for i in result.issues] == [RULE_IMPORT_NONE_FALLBACK]


def test_import_none_fallback_a_baselined_file_at_its_entry_passes(
    tmp_path: Path,
) -> None:
    fixture = _PRIMARY
    target = _plant(tmp_path, "old_file", fixture)
    entry = {"pkg/old_file.py": len(_VIOLATIONS[fixture])}
    assert _validator(tmp_path, entry).validate([target]).is_valid


def test_import_none_fallback_a_finding_added_to_a_baselined_file_is_refused(
    tmp_path: Path,
) -> None:
    target = _plant(tmp_path, "old_file", _PRIMARY)
    target.write_text(_source(_PRIMARY) * 2, encoding="utf-8")
    result = _validator(tmp_path, {"pkg/old_file.py": 1}).validate([target])
    assert not result.is_valid
    assert {i.rule_name for i in result.issues} == {
        RULE_IMPORT_NONE_FALLBACK,
        "baseline_ratchet",
    }


def test_import_none_fallback_a_fixed_finding_must_lower_the_entry(
    tmp_path: Path,
) -> None:
    target = _plant(tmp_path, "old_file", sorted(_ADMITTED)[0])
    result = _validator(tmp_path, {"pkg/old_file.py": 1}).validate([target])
    assert [i.rule_name for i in result.issues] == ["baseline_ratchet"]


def test_import_none_fallback_a_baseline_entry_for_a_missing_file_is_refused(
    tmp_path: Path,
) -> None:
    (tmp_path / "baseline.txt").write_text("pkg/gone.py 1\n", encoding="utf-8")
    result = _validator(tmp_path, {"pkg/gone.py": 1}).validate(
        [tmp_path / "baseline.txt"]
    )
    assert [i.rule_name for i in result.issues] == ["baseline_ratchet"]


def test_import_none_fallback_files_under_tests_are_not_judged(tmp_path: Path) -> None:
    target = tmp_path / "tests" / "test_subject.py"
    target.parent.mkdir(parents=True)
    target.write_text(_source(_PRIMARY), encoding="utf-8")
    assert _validator(tmp_path, {}).validate([target]).is_valid


def test_import_none_fallback_baseline_header_names_the_burn_down_ticket_and_a_zero_target() -> (
    None
):
    header = [
        line
        for line in _BASELINE.read_text(encoding="utf-8").splitlines()
        if line.startswith("#")
    ]
    text = "\n".join(header)
    assert "Burn-down ticket: OMN-22005" in text
    assert "Zero target: 2026-11-16" in text


def test_import_none_fallback_the_checked_in_baseline_equals_the_findings_of_the_tree() -> (
    None
):
    held = parse_baseline(_BASELINE.read_text(encoding="utf-8"))
    validator = ValidatorImportNoneFallback(baseline={})
    found: dict[str, int] = {}
    for path in held:
        count = len(
            import_none_fallback_lines(
                (_ROOT / path).read_text(encoding="utf-8"), _marker()
            )
        )
        found[path] = count
    assert found == held
    assert validator.validator_id == "import_none_fallback"


def test_import_none_fallback_parity_with_the_removed_script_on_the_source_tree() -> (
    None
):
    rules = _rules()
    for path in sorted((_ROOT / "src").rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        try:
            expected = import_none_fallback_lines(source, _marker())
        except SyntaxError:
            expected = []
        assert _lines(source, rules) == expected, path


def test_import_none_fallback_bus_a_run_puts_one_run_event_and_one_triggered_event_on_the_bus(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    listened: dict[str, list[ModelEventMessage]] = {"run": [], "triggered": []}

    async def _on_run(message: ModelEventMessage) -> None:
        listened["run"].append(message)

    async def _on_triggered(message: ModelEventMessage) -> None:
        listened["triggered"].append(message)

    bus = EventBusInmemory()
    asyncio.run(bus.subscribe(_RUN_TOPIC, on_message=_on_run, group_id="listener"))
    asyncio.run(
        bus.subscribe(
            str(TopicBase.VALIDATOR_TRIGGERED),
            on_message=_on_triggered,
            group_id="listener",
        )
    )
    monkeypatch.setattr(event_bus_inmemory, "EventBusInmemory", lambda: bus)
    monkeypatch.chdir(_ROOT)
    target = _plant(tmp_path, "planted", _PRIMARY)
    report = tmp_path / "report.json"

    exit_code = main(
        ValidatorImportNoneFallback,
        [str(target), "--report-json", str(report), "--overlay", str(_INMEMORY)],
        build_validator_container,
    )

    assert exit_code == 1
    written = json.loads(report.read_text(encoding="utf-8"))
    runs = [
        ModelValidatorRunEvent.model_validate_json(m.value) for m in listened["run"]
    ]
    assert [run.report_ref for run in runs] == [written["report_id"]]
    assert len(listened["triggered"]) == 1
    assert listened["triggered"][0].key == b"import_none_fallback"


def test_import_none_fallback_bus_a_clean_run_puts_one_run_event_and_no_triggered_event(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    listened: dict[str, list[ModelEventMessage]] = {"run": [], "triggered": []}

    async def _on_run(message: ModelEventMessage) -> None:
        listened["run"].append(message)

    async def _on_triggered(message: ModelEventMessage) -> None:
        listened["triggered"].append(message)

    bus = EventBusInmemory()
    asyncio.run(bus.subscribe(_RUN_TOPIC, on_message=_on_run, group_id="listener"))
    asyncio.run(
        bus.subscribe(
            str(TopicBase.VALIDATOR_TRIGGERED),
            on_message=_on_triggered,
            group_id="listener",
        )
    )
    monkeypatch.setattr(event_bus_inmemory, "EventBusInmemory", lambda: bus)
    monkeypatch.chdir(_ROOT)
    target = _plant(tmp_path, "clean", sorted(_ADMITTED)[0])

    exit_code = main(
        ValidatorImportNoneFallback,
        [
            str(target),
            "--report-json",
            str(tmp_path / "report.json"),
            "--overlay",
            str(_INMEMORY),
        ],
        build_validator_container,
    )

    assert exit_code == 0
    assert len(listened["run"]) == 1
    assert listened["triggered"] == []
