# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the ``id_from_stamp`` rule in the generic validator format (OMN-23189, gate OMN-21433 AC-4).

An id or key built from a seconds-only ``strftime`` stamp with no nonce is refused; the same stamp with a
nonce appended, a sub-second stamp, a display stamp and the annotated line are admitted. The checker is
pure; the validator reads a module and holds it to its entry in a per-file shrink-only baseline; every
name, directive, list, marker and remediation text is a ``parameters`` entry of a rule row of
``id_from_stamp.validation.yaml``. These tests load that contract, so the values that gate the repository
are the values under test.
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
from omnibase_core.validation.checker_id_from_stamp import (
    RULE_ID_FROM_STAMP,
    check_id_from_stamp,
)
from omnibase_core.validation.validator_id_from_stamp import ValidatorIdFromStamp

pytestmark = pytest.mark.unit

_ROOT = Path(__file__).resolve().parents[3]
_CONTRACT = (
    _ROOT / "src/omnibase_core/validation/contracts/id_from_stamp.validation.yaml"
)
_FIXTURES = _ROOT / "tests/fixtures/validation/id_from_stamp"
_NODE = Path(handler_validator_runtime_overlay.__file__).resolve().parent
_INMEMORY = _NODE / "overlays/validator_runtime.inmemory.overlay.yaml"
_HANDLER = HandlerValidatorRuntimeOverlay()
_RUN_TOPIC = _HANDLER.settings().run_topic
_FIXTURE_PATH = Path("src/pkg/subject.py")
_STAMP = 'started.strftime("%Y%m%dT%H%M%SZ")'

# fixture -> the lines the rule reports in it (red first: each row is a planted violation)
_VIOLATIONS: dict[str, list[int]] = {
    "violation_run_id_keyword": [7],
    "violation_stamp_name_in_f_string": [6],
    "violation_dict_key_and_attribute": [6, 7],
    "violation_format_held_in_constant": [7],
    "violation_through_string_calls": [3],
}
# the run_id line of the omnimarket work-ledger copy entry point as it stood at dev 566d7ead09
_PRIMARY = "violation_run_id_keyword"
_ADMITTED = [
    "annotated_nonce_ok",
    "clean_display_stamp",
    "clean_helper_builds_the_id",
    "clean_nonce_appended",
    "clean_subsecond_stamp",
]


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
    issues = check_id_from_stamp(_FIXTURE_PATH, source, rules or _rules())
    return [i.line_number or 0 for i in issues]


@pytest.mark.parametrize(("name", "expected"), sorted(_VIOLATIONS.items()))
def test_id_from_stamp_refuses_the_planted_violation(
    name: str, expected: list[int]
) -> None:
    assert _lines(_source(name)) == expected


@pytest.mark.parametrize("name", _ADMITTED)
def test_id_from_stamp_admits_the_annotated_and_clean_forms(name: str) -> None:
    assert _lines(_source(name)) == []


def test_id_from_stamp_fixture_set_is_complete() -> None:
    on_disk = {p.name.removesuffix(".py.txt") for p in _FIXTURES.glob("*.py.txt")}
    assert on_disk == set(_VIOLATIONS) | set(_ADMITTED)


def test_id_from_stamp_message_carries_the_rows_reason_line_and_remediation() -> None:
    rules = _rules()
    issue = check_id_from_stamp(_FIXTURE_PATH, _source(_PRIMARY), rules)[0]
    params = rules[RULE_ID_FROM_STAMP].parameters or {}
    assert str(params["reason"]) in issue.message
    assert str(params["remediation"]) in issue.message
    assert issue.code == RULE_ID_FROM_STAMP
    assert issue.file_path == _FIXTURE_PATH


def test_id_from_stamp_the_run_id_line_of_the_work_ledger_copy_entry_is_refused() -> (
    None
):
    """AC1: the ``run_id`` line as it stood at omnimarket dev 566d7ead09 is red."""
    source = f"def main(started):\n    return ModelCopyRequest(run_id={_STAMP}, started_at=started)\n"
    assert _lines(source) == [2]


def test_id_from_stamp_control_the_same_stamp_plus_a_nonce_is_admitted() -> None:
    """AC2: the passing control, an id built from the same stamp plus a nonce."""
    source = (
        "import uuid\n\n\ndef main(started):\n"
        f'    return ModelCopyRequest(run_id=f"{{{_STAMP}}}-{{uuid.uuid4().hex[:8]}}", started_at=started)\n'
    )
    assert _lines(source) == []


def test_id_from_stamp_unparseable_source_is_judged_clean() -> None:
    assert _lines("def broken(:\n") == []


def test_id_from_stamp_disabled_row_is_not_run() -> None:
    rules = _rules()
    rules[RULE_ID_FROM_STAMP] = rules[RULE_ID_FROM_STAMP].model_copy(
        update={"enabled": False}
    )
    assert _lines(_source(_PRIMARY), rules) == []


def _mutated(key: str, value: object) -> dict[str, ModelValidatorRule]:
    rules = _rules()
    row = rules[RULE_ID_FROM_STAMP]
    rules[RULE_ID_FROM_STAMP] = row.model_copy(
        update={"parameters": {**(row.parameters or {}), key: value}}
    )
    return rules


def test_id_from_stamp_every_parameter_key_is_exercised_by_the_table() -> None:
    keys = set(_rules()[RULE_ID_FROM_STAMP].parameters or {})
    assert keys == {
        "id_name_patterns",
        "stamp_method",
        "second_directives",
        "subsecond_directives",
        "nonce_calls",
        "nonce_name_fragments",
        "passthrough_calls",
        "comment_prefix",
        "annotation_marker",
        "reason",
        "remediation",
    }


# parameter -> (fixture it changes the verdict of, the value that breaks the rule it carries)
_BREAKS: dict[str, tuple[str, object]] = {
    "id_name_patterns": (_PRIMARY, ["^zzz$"]),
    "stamp_method": (_PRIMARY, "zzz"),
    "second_directives": (_PRIMARY, ["%zzz"]),
    "passthrough_calls": ("violation_through_string_calls", ["zzz"]),
}


@pytest.mark.parametrize("key", sorted(_BREAKS))
def test_id_from_stamp_mutating_a_pattern_parameter_changes_the_verdict(
    key: str,
) -> None:
    fixture, broken = _BREAKS[key]
    assert _lines(_source(fixture)) != []
    assert _lines(_source(fixture), _mutated(key, broken)) == []


def test_id_from_stamp_mutating_the_subsecond_directives_refuses_the_subsecond_stamp() -> (
    None
):
    source = _source("clean_subsecond_stamp")
    assert _lines(source) == []
    assert _lines(source, _mutated("subsecond_directives", ["%zzz"])) != []


# parameter -> a control that only that list admits
_NONCE_CONTROLS: dict[str, str] = {
    "nonce_calls": (
        "import secrets\n\n\ndef main(started):\n"
        f'    return make(run_id=f"{{{_STAMP}}}-{{secrets.randbits(32)}}")\n'
    ),
    "nonce_name_fragments": (
        "def main(started, nonce):\n"
        f'    return make(run_id=f"{{{_STAMP}}}-{{nonce}}")\n'
    ),
}


@pytest.mark.parametrize("key", sorted(_NONCE_CONTROLS))
def test_id_from_stamp_mutating_a_nonce_list_turns_the_control_red(key: str) -> None:
    """The named injected break: a nonce list that no longer names the nonce refuses the control."""
    source = _NONCE_CONTROLS[key]
    assert _lines(source) == []
    assert _lines(source, _mutated(key, ["zzz"])) != []


@pytest.mark.parametrize("key", ["comment_prefix", "annotation_marker"])
def test_id_from_stamp_mutating_the_annotation_parameter_refuses_the_annotated_line(
    key: str,
) -> None:
    annotated = _source("annotated_nonce_ok")
    assert _lines(annotated) == []
    assert _lines(annotated, _mutated(key, "zzz-marker")) != []


@pytest.mark.parametrize("key", ["reason", "remediation"])
def test_id_from_stamp_mutating_a_text_parameter_changes_the_message(key: str) -> None:
    source = _source(_PRIMARY)
    issues = check_id_from_stamp(_FIXTURE_PATH, source, _mutated(key, "zzz-text"))
    assert issues and "zzz-text" in issues[0].message


@pytest.mark.parametrize(
    "key",
    [
        "id_name_patterns",
        "stamp_method",
        "second_directives",
        "subsecond_directives",
        "nonce_calls",
        "nonce_name_fragments",
        "passthrough_calls",
        "reason",
        "remediation",
    ],
)
def test_id_from_stamp_a_missing_parameter_fails_the_load(key: str) -> None:
    row = _rules()[RULE_ID_FROM_STAMP]
    stripped = {k: v for k, v in (row.parameters or {}).items() if k != key}
    rules = _rules()
    rules[RULE_ID_FROM_STAMP] = row.model_copy(update={"parameters": stripped})
    with pytest.raises(ModelOnexError):
        check_id_from_stamp(_FIXTURE_PATH, "", rules)


def _validator(tmp_path: Path, baseline: dict[str, int]) -> ValidatorIdFromStamp:
    return ValidatorIdFromStamp(
        root=tmp_path, baseline=baseline, baseline_path="baseline.txt"
    )


def _plant(tmp_path: Path, name: str, fixture: str) -> Path:
    target = tmp_path / "pkg" / f"{name}.py"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(_source(fixture), encoding="utf-8")
    return target


def test_id_from_stamp_a_new_finding_in_a_clean_file_is_refused(
    tmp_path: Path,
) -> None:
    target = _plant(tmp_path, "clean_file", _PRIMARY)
    result = _validator(tmp_path, {}).validate([target])
    assert not result.is_valid
    assert [i.rule_name for i in result.issues] == [RULE_ID_FROM_STAMP]


def test_id_from_stamp_a_baselined_file_at_its_entry_passes(tmp_path: Path) -> None:
    fixture = _PRIMARY
    target = _plant(tmp_path, "old_file", fixture)
    entry = {"pkg/old_file.py": len(_VIOLATIONS[fixture])}
    assert _validator(tmp_path, entry).validate([target]).is_valid


def test_id_from_stamp_a_finding_added_to_a_baselined_file_is_refused(
    tmp_path: Path,
) -> None:
    target = _plant(tmp_path, "old_file", _PRIMARY)
    target.write_text(_source(_PRIMARY) * 2, encoding="utf-8")
    result = _validator(tmp_path, {"pkg/old_file.py": 1}).validate([target])
    assert not result.is_valid
    assert {i.rule_name for i in result.issues} == {
        RULE_ID_FROM_STAMP,
        "baseline_ratchet",
    }


def test_id_from_stamp_a_fixed_finding_must_lower_the_entry(tmp_path: Path) -> None:
    target = _plant(tmp_path, "old_file", sorted(_ADMITTED)[0])
    result = _validator(tmp_path, {"pkg/old_file.py": 1}).validate([target])
    assert [i.rule_name for i in result.issues] == ["baseline_ratchet"]


def test_id_from_stamp_a_baseline_entry_for_a_missing_file_is_refused(
    tmp_path: Path,
) -> None:
    (tmp_path / "baseline.txt").write_text("pkg/gone.py 1\n", encoding="utf-8")
    result = _validator(tmp_path, {"pkg/gone.py": 1}).validate(
        [tmp_path / "baseline.txt"]
    )
    assert [i.rule_name for i in result.issues] == ["baseline_ratchet"]


def test_id_from_stamp_files_under_tests_are_not_judged(tmp_path: Path) -> None:
    target = tmp_path / "tests" / "test_subject.py"
    target.parent.mkdir(parents=True)
    target.write_text(_source(_PRIMARY), encoding="utf-8")
    assert _validator(tmp_path, {}).validate([target]).is_valid


def test_id_from_stamp_the_tree_holds_no_finding_so_the_hook_passes_no_baseline() -> (
    None
):
    rules = _rules()
    found: dict[str, int] = {}
    for path in sorted(_ROOT.glob("src/**/*.py")) + sorted(
        _ROOT.glob("scripts/**/*.py")
    ):
        count = len(check_id_from_stamp(path, path.read_text(encoding="utf-8"), rules))
        if count:
            found[path.relative_to(_ROOT).as_posix()] = count
    assert found == {}
    assert not (_ROOT / ".onex_ratchets/id_from_stamp_baseline.yaml").exists()
    assert ValidatorIdFromStamp(baseline={}).validator_id == "id_from_stamp"


def test_id_from_stamp_bus_a_run_puts_one_run_event_and_one_triggered_event_on_the_bus(
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
        ValidatorIdFromStamp,
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
    assert listened["triggered"][0].key == b"id_from_stamp"


def test_id_from_stamp_bus_a_clean_run_puts_one_run_event_and_no_triggered_event(
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
        ValidatorIdFromStamp,
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
def test_id_from_stamp_a_damaged_baseline_holds_no_entries(text: str) -> None:
    assert parse_baseline(text) == {}
