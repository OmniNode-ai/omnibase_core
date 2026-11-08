# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the ``fixed_tmp_atomic_write`` rule in the generic validator format (OMN-23188).

A write-then-rename whose temporary path is the target path plus a fixed suffix is refused; a temporary file made with mkstemp, NamedTemporaryFile, a pid or a uuid, a backup rotation and the annotated line are admitted. The checker is pure; the validator reads a module and holds it to its entry in a per-file
shrink-only baseline; every name, marker and remediation text is a ``parameters`` entry of a rule
row of ``fixed_tmp_atomic_write.validation.yaml``. These tests load that contract, so the values that gate the
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
from omnibase_core.validation.checker_fixed_tmp_atomic_write import (
    RULE_FIXED_TMP_ATOMIC_WRITE,
    check_fixed_tmp_atomic_write,
)
from omnibase_core.validation.validator_fixed_tmp_atomic_write import (
    ValidatorFixedTmpAtomicWrite,
)

pytestmark = pytest.mark.unit

_ROOT = Path(__file__).resolve().parents[3]
_CONTRACT = (
    _ROOT
    / "src/omnibase_core/validation/contracts/fixed_tmp_atomic_write.validation.yaml"
)
_FIXTURES = _ROOT / "tests/fixtures/validation/fixed_tmp_atomic_write"
_BASELINE = _ROOT / ".onex_ratchets/fixed_tmp_atomic_write_baseline.yaml"
_NODE = Path(handler_validator_runtime_overlay.__file__).resolve().parent
_INMEMORY = _NODE / "overlays/validator_runtime.inmemory.overlay.yaml"
_HANDLER = HandlerValidatorRuntimeOverlay()
_RUN_TOPIC = _HANDLER.settings().run_topic
_FIXTURE_PATH = Path("src/pkg/subject.py")

# fixture -> the lines the rule reports in it (red first: each row is a planted violation)
_VIOLATIONS: dict[str, list[int]] = {
    "violation_fixed_name_in_target_dir": [7],
    "violation_method_replace_fstring": [7],
    "violation_self_attribute": [9],
    "violation_string_concat": [8],
    "violation_with_suffix_tmp": [8],
}
_PRIMARY = "violation_with_suffix_tmp"
_CONTROL = "clean_mkstemp_in_target_dir"
_ADMITTED = [
    "annotated_fixed_tmp_ok",
    "clean_backup_rotation",
    "clean_mkstemp_in_target_dir",
    "clean_named_temporary_file",
    "clean_pid_suffix",
    "clean_temporary_path_is_a_parameter",
    "clean_uuid_suffix",
]
_PARAMETERS = {
    "rename_functions",
    "rename_methods",
    "derived_attributes",
    "neutral_names",
    "path_derivations",
    "comment_prefix",
    "annotation_marker",
    "reason",
    "remediation",
}


def _contract() -> ModelValidatorSubcontract:
    data = yaml.safe_load(_CONTRACT.read_text(encoding="utf-8"))
    return ModelValidatorSubcontract.model_validate(data["validation"])


def _rules(
    contract: ModelValidatorSubcontract | None = None,
) -> dict[str, ModelValidatorRule]:
    return {r.rule_id: r for r in (contract or _contract()).rules}


def _source(name: str) -> str:
    return (_FIXTURES / f"{name}.py.txt").read_text(encoding="utf-8")


def _lines(
    source: str, rules: dict[str, ModelValidatorRule] | None = None
) -> list[int]:
    issues = check_fixed_tmp_atomic_write(_FIXTURE_PATH, source, rules or _rules())
    return [i.line_number or 0 for i in issues]


@pytest.mark.parametrize(("name", "expected"), sorted(_VIOLATIONS.items()))
def test_fixed_tmp_atomic_write_refuses_the_planted_violation(
    name: str, expected: list[int]
) -> None:
    assert _lines(_source(name)) == expected


@pytest.mark.parametrize("name", _ADMITTED)
def test_fixed_tmp_atomic_write_admits_the_annotated_and_clean_forms(name: str) -> None:
    assert _lines(_source(name)) == []


def test_fixed_tmp_atomic_write_the_mkstemp_control_is_admitted_and_its_fixed_twin_refused() -> (
    None
):
    control = _source(_CONTROL)
    assert _lines(control) == []
    fixed = control.replace(
        'fd, tmp = tempfile.mkstemp(dir=os.path.dirname(target), suffix=".tmp")',
        'tmp = target + ".tmp"\n    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT)',
    )
    assert fixed != control
    assert _lines(fixed) != []


def test_fixed_tmp_atomic_write_fixture_set_is_complete() -> None:
    on_disk = {p.name.removesuffix(".py.txt") for p in _FIXTURES.glob("*.py.txt")}
    assert on_disk == set(_VIOLATIONS) | set(_ADMITTED)


def test_fixed_tmp_atomic_write_message_carries_the_rows_reason_line_and_remediation() -> (
    None
):
    rules = _rules()
    issue = check_fixed_tmp_atomic_write(_FIXTURE_PATH, _source(_PRIMARY), rules)[0]
    params = rules[RULE_FIXED_TMP_ATOMIC_WRITE].parameters or {}
    assert str(params["reason"]) in issue.message
    assert str(params["remediation"]) in issue.message
    assert issue.code == RULE_FIXED_TMP_ATOMIC_WRITE
    assert issue.file_path == _FIXTURE_PATH


def test_fixed_tmp_atomic_write_unparseable_source_is_judged_clean() -> None:
    assert _lines("def broken(:\n") == []


def test_fixed_tmp_atomic_write_a_nested_function_is_read_in_its_own_scope() -> None:
    source = (
        "import os\n\n\n"
        "def outer(path):\n"
        "    tmp = path + '.tmp'\n\n"
        "    def inner(path, tmp):\n"
        "        os.replace(tmp, path)\n\n"
        "    return inner\n"
    )
    assert _lines(source) == []


def test_fixed_tmp_atomic_write_a_later_unique_assignment_wins() -> None:
    source = (
        "import os\n\n\n"
        "def publish(path):\n"
        "    tmp = path + '.tmp'\n"
        "    tmp = tmp + str(os.getpid())\n"
        "    os.replace(tmp, path)\n"
    )
    assert _lines(source) == []


def test_fixed_tmp_atomic_write_a_str_replace_call_is_not_a_rename() -> None:
    assert _lines("def f(path):\n    return path.replace('a', 'b')\n") == []


def test_fixed_tmp_atomic_write_disabled_row_is_not_run() -> None:
    rules = _rules()
    rules[RULE_FIXED_TMP_ATOMIC_WRITE] = rules[RULE_FIXED_TMP_ATOMIC_WRITE].model_copy(
        update={"enabled": False}
    )
    assert _lines(_source(_PRIMARY), rules) == []


def _mutated(key: str, value: object) -> dict[str, ModelValidatorRule]:
    rules = _rules()
    row = rules[RULE_FIXED_TMP_ATOMIC_WRITE]
    rules[RULE_FIXED_TMP_ATOMIC_WRITE] = row.model_copy(
        update={"parameters": {**(row.parameters or {}), key: value}}
    )
    return rules


def test_fixed_tmp_atomic_write_every_parameter_key_is_exercised_by_the_table() -> None:
    keys = set(_rules()[RULE_FIXED_TMP_ATOMIC_WRITE].parameters or {})
    assert keys == _PARAMETERS


def test_fixed_tmp_atomic_write_mutating_rename_functions_changes_the_verdict() -> None:
    source = _source("violation_string_concat")
    assert _lines(source) != []
    assert _lines(source, _mutated("rename_functions", ["zzz.move"])) == []


def test_fixed_tmp_atomic_write_mutating_rename_methods_changes_the_verdict() -> None:
    source = _source("violation_method_replace_fstring")
    assert _lines(source) != []
    assert _lines(source, _mutated("rename_methods", ["zzz"])) == []


def test_fixed_tmp_atomic_write_mutating_derived_attributes_changes_the_verdict() -> (
    None
):
    source = _source("violation_fixed_name_in_target_dir")
    assert _lines(source) != []
    assert _lines(source, _mutated("derived_attributes", ["zzz"])) == []


def test_fixed_tmp_atomic_write_mutating_neutral_names_changes_the_verdict() -> None:
    source = (
        "import os\n\n\ndef f(path):\n    os.replace(os.fspath(path) + '.tmp', path)\n"
    )
    assert _lines(source) != []
    assert _lines(source, _mutated("neutral_names", ["zzz"])) == []


def test_fixed_tmp_atomic_write_mutating_path_derivations_changes_the_verdict() -> None:
    source = _source("violation_with_suffix_tmp")
    assert _lines(source) != []
    assert _lines(source, _mutated("path_derivations", ["zzz"])) == []


@pytest.mark.parametrize("key", ["comment_prefix", "annotation_marker"])
def test_fixed_tmp_atomic_write_mutating_the_marker_changes_the_verdict(
    key: str,
) -> None:
    annotated = _source("annotated_fixed_tmp_ok")
    assert _lines(annotated) == []
    assert _lines(annotated, _mutated(key, "zzz-marker")) != []


@pytest.mark.parametrize("key", ["reason", "remediation"])
def test_fixed_tmp_atomic_write_mutating_a_text_parameter_changes_the_message(
    key: str,
) -> None:
    source = _source(_PRIMARY)
    issues = check_fixed_tmp_atomic_write(
        _FIXTURE_PATH, source, _mutated(key, "zzz-text")
    )
    assert issues and "zzz-text" in issues[0].message


@pytest.mark.parametrize("key", sorted(_PARAMETERS))
def test_fixed_tmp_atomic_write_a_missing_parameter_fails_the_load(key: str) -> None:
    row = _rules()[RULE_FIXED_TMP_ATOMIC_WRITE]
    stripped = {k: v for k, v in (row.parameters or {}).items() if k != key}
    rules = _rules()
    rules[RULE_FIXED_TMP_ATOMIC_WRITE] = row.model_copy(update={"parameters": stripped})
    with pytest.raises(ModelOnexError):
        check_fixed_tmp_atomic_write(_FIXTURE_PATH, "", rules)


def _validator(
    tmp_path: Path, baseline: dict[str, int]
) -> ValidatorFixedTmpAtomicWrite:
    return ValidatorFixedTmpAtomicWrite(
        root=tmp_path, baseline=baseline, baseline_path="baseline.txt"
    )


def _plant(tmp_path: Path, name: str, fixture: str) -> Path:
    target = tmp_path / "pkg" / f"{name}.py"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(_source(fixture), encoding="utf-8")
    return target


def test_fixed_tmp_atomic_write_a_new_finding_in_a_clean_file_is_refused(
    tmp_path: Path,
) -> None:
    target = _plant(tmp_path, "clean_file", _PRIMARY)
    result = _validator(tmp_path, {}).validate([target])
    assert not result.is_valid
    assert [i.rule_name for i in result.issues] == [RULE_FIXED_TMP_ATOMIC_WRITE]


def test_fixed_tmp_atomic_write_the_mkstemp_control_passes_the_validator(
    tmp_path: Path,
) -> None:
    target = _plant(tmp_path, "control_file", _CONTROL)
    assert _validator(tmp_path, {}).validate([target]).is_valid


def test_fixed_tmp_atomic_write_a_baselined_file_at_its_entry_passes(
    tmp_path: Path,
) -> None:
    target = _plant(tmp_path, "old_file", _PRIMARY)
    entry = {"pkg/old_file.py": len(_VIOLATIONS[_PRIMARY])}
    assert _validator(tmp_path, entry).validate([target]).is_valid


def test_fixed_tmp_atomic_write_a_finding_added_to_a_baselined_file_is_refused(
    tmp_path: Path,
) -> None:
    target = _plant(tmp_path, "old_file", _PRIMARY)
    target.write_text(_source(_PRIMARY) * 2, encoding="utf-8")
    result = _validator(tmp_path, {"pkg/old_file.py": 1}).validate([target])
    assert not result.is_valid
    assert {i.rule_name for i in result.issues} == {
        RULE_FIXED_TMP_ATOMIC_WRITE,
        "baseline_ratchet",
    }


def test_fixed_tmp_atomic_write_a_fixed_finding_must_lower_the_entry(
    tmp_path: Path,
) -> None:
    target = _plant(tmp_path, "old_file", _CONTROL)
    result = _validator(tmp_path, {"pkg/old_file.py": 1}).validate([target])
    assert [i.rule_name for i in result.issues] == ["baseline_ratchet"]


def test_fixed_tmp_atomic_write_a_baseline_entry_for_a_missing_file_is_refused(
    tmp_path: Path,
) -> None:
    (tmp_path / "baseline.txt").write_text("pkg/gone.py 1\n", encoding="utf-8")
    result = _validator(tmp_path, {"pkg/gone.py": 1}).validate(
        [tmp_path / "baseline.txt"]
    )
    assert [i.rule_name for i in result.issues] == ["baseline_ratchet"]


def test_fixed_tmp_atomic_write_files_under_tests_are_not_judged(
    tmp_path: Path,
) -> None:
    target = tmp_path / "tests" / "test_subject.py"
    target.parent.mkdir(parents=True)
    target.write_text(_source(_PRIMARY), encoding="utf-8")
    assert _validator(tmp_path, {}).validate([target]).is_valid


def test_fixed_tmp_atomic_write_baseline_header_names_the_burn_down_ticket_and_a_zero_target() -> (
    None
):
    header = [
        line
        for line in _BASELINE.read_text(encoding="utf-8").splitlines()
        if line.startswith("#")
    ]
    text = "\n".join(header)
    assert "Burn-down ticket: OMN-23188" in text
    assert "Zero target: 2026-11-22" in text


def test_fixed_tmp_atomic_write_the_checked_in_baseline_equals_the_findings_of_the_tree() -> (
    None
):
    held = parse_baseline(_BASELINE.read_text(encoding="utf-8"))
    rules = _rules()
    found: dict[str, int] = {}
    for path in sorted((_ROOT / "src").rglob("*.py")):
        relative = path.relative_to(_ROOT).as_posix()
        issues = check_fixed_tmp_atomic_write(
            Path(relative), path.read_text(encoding="utf-8"), rules
        )
        if issues:
            found[relative] = len(issues)
    scripts = _ROOT / "scripts"
    for path in sorted(scripts.rglob("*.py")) if scripts.is_dir() else []:
        relative = path.relative_to(_ROOT).as_posix()
        issues = check_fixed_tmp_atomic_write(
            Path(relative), path.read_text(encoding="utf-8"), rules
        )
        if issues:
            found[relative] = len(issues)
    assert found == held
    assert (
        ValidatorFixedTmpAtomicWrite(baseline={}).validator_id
        == "fixed_tmp_atomic_write"
    )


def test_fixed_tmp_atomic_write_bus_a_run_puts_one_run_event_and_one_triggered_event_on_the_bus(
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
        ValidatorFixedTmpAtomicWrite,
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
    assert listened["triggered"][0].key == b"fixed_tmp_atomic_write"


def test_fixed_tmp_atomic_write_bus_a_clean_run_puts_one_run_event_and_no_triggered_event(
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
    target = _plant(tmp_path, "clean", _CONTROL)

    exit_code = main(
        ValidatorFixedTmpAtomicWrite,
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


@pytest.mark.parametrize("text", ["", "---\n", "a: [1", "- a\n- b\n", "a: 1\na: 2\n"])
def test_fixed_tmp_atomic_write_a_damaged_baseline_holds_no_entries(text: str) -> None:
    assert parse_baseline(text) == {}
