# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the ``effect_node_bypass`` rows in the generic validator format (OMN-24432).

A GitHub command line or a GitHub API address outside an effect node package is a bypass of the node that
owns that call. The checker is pure; the validator holds the whole run's count to the shrink-only count file
``config/effect_node_bypass_ratchet.yaml``, so a new bypass raises the count above the file and fails on its
first run, and the file may neither be raised nor left above the count. Every executable, substring, pattern, path pattern and text is a ``parameters`` entry
of a row of ``effect_node_bypass.validation.yaml``, and these tests load that contract, so the values that
gate the repository are the values under test.
"""

from __future__ import annotations

import asyncio
import json
import subprocess
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
from omnibase_core.validation.checker_effect_node_bypass import (
    check_count_ratchet,
    check_effect_node_bypass,
)
from omnibase_core.validation.validator_effect_node_bypass import (
    ValidatorEffectNodeBypass,
)
from omnibase_core.validators.no_unguarded_git_subprocess import scrub_git_location_env

pytestmark = pytest.mark.unit

_ROOT = Path(__file__).resolve().parents[3]
_CONTRACT = (
    _ROOT / "src/omnibase_core/validation/contracts/effect_node_bypass.validation.yaml"
)
_RATCHET = _ROOT / "config/effect_node_bypass_ratchet.yaml"
_NODE = Path(handler_validator_runtime_overlay.__file__).resolve().parent
_INMEMORY = _NODE / "overlays/validator_runtime.inmemory.overlay.yaml"
_RUN_TOPIC = HandlerValidatorRuntimeOverlay().settings().run_topic
_ELSEWHERE = Path("src/pkg/adapters/merge_adapter.py")
_EFFECT = Path("src/pkg/nodes/node_merge_effect/handler_merge.py")
_PLANTED_CLI = (
    "import subprocess\n\n"
    "def merge(n: int) -> None:\n"
    '    subprocess.run(["gh", "pr", "merge", str(n)], check=True)\n'
)
_PLANTED_API = 'URL = f"https://api.github.com/repos/{{repo}}/pulls"\n'
_PLANTED_SHELL = 'PR_BODY="$(gh pr view "$1" --json body)"\n'
_RULE_IDS = ("github_cli", "github_api")


def _contract() -> ModelValidatorSubcontract:
    data = yaml.safe_load(_CONTRACT.read_text(encoding="utf-8"))
    return ModelValidatorSubcontract.model_validate(data["validation"])


def _rules(
    contract: ModelValidatorSubcontract | None = None,
) -> dict[str, ModelValidatorRule]:
    return {r.rule_id: r for r in (contract or _contract()).rules}


def _found(path: Path, source: str) -> list[tuple[str, int]]:
    return [
        (i.rule_name or "", i.line_number or 0)
        for i in check_effect_node_bypass(path, source, _rules())
    ]


def test_effect_node_bypass_planted_calls_fail_outside_an_effect_node() -> None:
    assert _found(_ELSEWHERE, _PLANTED_CLI) == [("github_cli", 4)]
    assert _found(_ELSEWHERE, _PLANTED_API) == [("github_api", 1)]
    assert _found(Path("scripts/merge.sh"), _PLANTED_SHELL) == [("github_cli", 1)]


def test_effect_node_bypass_planted_call_fails_in_the_validator_run(
    tmp_path: Path,
) -> None:
    target = tmp_path / _ELSEWHERE
    target.parent.mkdir(parents=True)
    target.write_text(_PLANTED_CLI, encoding="utf-8")

    exit_code = main(
        ValidatorEffectNodeBypass,
        [str(target), "--report-json", str(tmp_path / "report.json")],
        build_validator_container,
    )

    assert exit_code == 1


def test_effect_node_bypass_the_effect_node_twin_differs_only_by_path() -> None:
    assert _found(_ELSEWHERE, _PLANTED_CLI) == [("github_cli", 4)]
    assert _found(_EFFECT, _PLANTED_CLI) == []
    assert _found(_EFFECT, _PLANTED_API) == []


def test_effect_node_bypass_effect_node_passes_in_the_validator_run(
    tmp_path: Path,
) -> None:
    target = tmp_path / _EFFECT
    target.parent.mkdir(parents=True)
    target.write_text(_PLANTED_CLI, encoding="utf-8")

    exit_code = main(
        ValidatorEffectNodeBypass,
        [str(target), "--report-json", str(tmp_path / "report.json")],
        build_validator_container,
    )

    assert exit_code == 0


@pytest.mark.parametrize(
    "source",
    [
        '"""Merges with gh pr merge, see api.github.com."""\n\nVALUE = 1\n',
        "# gh pr merge is run by the node\nVALUE = 1\n",
        "def f(command: str) -> bool:\n    return command == 'gh'\n",
        "def f() -> list[str]:\n    return ['gh']\n",
        "VALUE = 1\n",
        "def broken(:\n    gh pr merge\n",
    ],
)
def test_effect_node_bypass_admits_prose_comparisons_and_unrelated_modules(
    source: str,
) -> None:
    assert _found(_ELSEWHERE, source) == []


def test_effect_node_bypass_admits_a_shell_comment() -> None:
    assert _found(Path("scripts/note.sh"), "# gh pr merge is the node's job\n") == []


def test_effect_node_bypass_reads_a_command_string_and_a_variable_command() -> None:
    assert _found(_ELSEWHERE, 'import os\n\nos.system("gh pr merge 1")\n') == [
        ("github_cli", 3)
    ]
    assert _found(_ELSEWHERE, 'base = ["gh", "pr", "merge", "1"]\n') == [
        ("github_cli", 1)
    ]


def test_effect_node_bypass_the_contract_names_the_surfaces_and_the_ratchet_row() -> (
    None
):
    assert [r.rule_id for r in _contract().rules] == [*_RULE_IDS, "count_ratchet"]
    assert ValidatorEffectNodeBypass().validator_id == "effect_node_bypass"


@pytest.mark.parametrize("key", ["command_executables", "string_substrings"])
def test_effect_node_bypass_mutating_a_surface_changes_the_verdict(key: str) -> None:
    mutated = _contract()
    for row in mutated.rules:
        if row.rule_id in _RULE_IDS and row.parameters is not None:
            row.parameters[key] = []
    source = _PLANTED_CLI if key == "command_executables" else _PLANTED_API
    assert check_effect_node_bypass(_ELSEWHERE, source, _rules(mutated)) == ()


def test_effect_node_bypass_a_new_surface_is_a_new_row_and_no_code() -> None:
    contract = _contract()
    row = _rules(contract)["github_cli"]
    assert row.parameters is not None
    parameters = dict(row.parameters)
    parameters["command_executables"] = ["tool"]
    parameters["text_line_patterns"] = [r"^tool\s"]
    extra = row.model_copy(update={"rule_id": "tool_cli", "parameters": parameters})
    rules = {**_rules(contract), "tool_cli": extra}
    issues = check_effect_node_bypass(_ELSEWHERE, 'cmd = ["tool", "run"]\n', rules)
    assert [i.rule_name for i in issues] == ["tool_cli"]


@pytest.mark.parametrize(
    "key",
    [
        "command_executables",
        "string_substrings",
        "text_line_patterns",
        "allowed_path_patterns",
        "comment_prefix",
        "reason",
        "remediation",
    ],
)
def test_effect_node_bypass_a_missing_parameter_fails_the_load(key: str) -> None:
    rules = _rules()
    row = rules["github_cli"]
    assert row.parameters is not None
    stripped = {k: v for k, v in row.parameters.items() if k != key}
    rules["github_cli"] = row.model_copy(update={"parameters": stripped})
    with pytest.raises(ModelOnexError):
        check_effect_node_bypass(_ELSEWHERE, "", rules)


def test_effect_node_bypass_a_pattern_that_does_not_compile_fails_the_load() -> None:
    rules = _rules()
    row = rules["github_cli"]
    assert row.parameters is not None
    rules["github_cli"] = row.model_copy(
        update={"parameters": {**row.parameters, "text_line_patterns": ["("]}}
    )
    with pytest.raises(ModelOnexError):
        check_effect_node_bypass(_ELSEWHERE, "", rules)


def _git_checkout_with_base_ref(root: Path) -> None:
    """A checkout whose base branch ref exists: the count file is judged against its merge base."""
    for args in (
        ["init", "-q"],
        [
            "-c",
            "user.name=t",
            "-c",
            "user.email=t@t",
            "commit",
            "-q",
            "--allow-empty",
            "-m",
            "base",
        ],
        ["update-ref", "refs/remotes/origin/dev", "HEAD"],
    ):
        subprocess.run(
            ["git", *args], cwd=root, env=scrub_git_location_env(), check=True
        )


def _validator(tmp_path: Path, ratchet: int | None) -> ValidatorEffectNodeBypass:
    if ratchet is not None and not (tmp_path / ".git").exists():
        _git_checkout_with_base_ref(tmp_path)
    return ValidatorEffectNodeBypass(
        root=tmp_path, ratchet=ratchet, ratchet_path=Path("config/ratchet.yaml")
    )


def _plant(tmp_path: Path, name: str, source: str) -> Path:
    target = tmp_path / "pkg" / f"{name}.py"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(source, encoding="utf-8")
    return target


def test_effect_node_bypass_with_no_count_file_every_bypass_is_a_finding(
    tmp_path: Path,
) -> None:
    _plant(tmp_path, "one", _PLANTED_CLI)
    _plant(tmp_path, "two", _PLANTED_API)
    result = _validator(tmp_path, None).validate([tmp_path])
    assert not result.is_valid
    assert sorted(i.rule_name or "" for i in result.issues) == [
        "github_api",
        "github_cli",
    ]


def test_effect_node_bypass_a_baselined_tree_at_its_count_passes(
    tmp_path: Path,
) -> None:
    _plant(tmp_path, "one", _PLANTED_CLI)
    _plant(tmp_path, "two", _PLANTED_API)
    assert _validator(tmp_path, 2).validate([tmp_path]).is_valid


def test_effect_node_bypass_a_new_bypass_in_a_clean_file_above_the_count_is_refused(
    tmp_path: Path,
) -> None:
    _plant(tmp_path, "one", _PLANTED_CLI)
    _plant(tmp_path, "two", _PLANTED_API)
    result = _validator(tmp_path, 1).validate([tmp_path])
    assert not result.is_valid
    assert result.issues[0].rule_name == "count_ratchet"
    assert "2 bypasses found" in result.issues[0].message
    assert len(result.issues) == 3


def test_effect_node_bypass_a_removed_call_must_lower_the_entry(
    tmp_path: Path,
) -> None:
    _plant(tmp_path, "one", _PLANTED_CLI)
    result = _validator(tmp_path, 2).validate([tmp_path])
    assert [i.rule_name for i in result.issues if i.rule_name == "count_ratchet"] == [
        "count_ratchet"
    ]
    assert not result.is_valid
    assert "lower it to 1" in result.issues[0].message


def test_effect_node_bypass_the_count_file_may_not_be_raised_against_the_base() -> None:
    rules = _rules()
    raised = check_count_ratchet(3, 3, 2, Path("config/ratchet.yaml"), rules)
    assert [i.rule_name for i in raised] == ["count_ratchet"]
    assert "base revision holds 2" in raised[0].message
    assert check_count_ratchet(2, 2, 2, Path("config/ratchet.yaml"), rules) == ()
    assert check_count_ratchet(1, 1, 2, Path("config/ratchet.yaml"), rules) == ()
    assert check_count_ratchet(1, 1, None, Path("config/ratchet.yaml"), rules) == ()


def test_effect_node_bypass_a_raised_count_file_is_refused_against_the_base_revision(
    tmp_path: Path,
) -> None:
    ratchet = tmp_path / "config/ratchet.yaml"
    ratchet.parent.mkdir(parents=True)
    ratchet.write_text("max_bypasses: 1\n", encoding="utf-8")
    _plant(tmp_path, "one", _PLANTED_CLI)
    _plant(tmp_path, "two", _PLANTED_API)
    for args in (
        ["init", "-q"],
        ["add", "-A"],
        ["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "base"],
        ["update-ref", "refs/remotes/origin/dev", "HEAD"],
    ):
        subprocess.run(
            ["git", *args],
            cwd=tmp_path,
            env=scrub_git_location_env(),
            check=True,
        )
    ratchet.write_text("max_bypasses: 2\n", encoding="utf-8")
    result = ValidatorEffectNodeBypass(
        root=tmp_path, ratchet=2, ratchet_path=Path("config/ratchet.yaml")
    ).validate([tmp_path])
    assert not result.is_valid
    assert "base revision holds 1" in result.issues[0].message


def test_effect_node_bypass_files_under_tests_are_not_judged(tmp_path: Path) -> None:
    target = tmp_path / "tests" / "test_subject.py"
    target.parent.mkdir(parents=True)
    target.write_text(_PLANTED_CLI, encoding="utf-8")
    assert _validator(tmp_path, 0).validate([tmp_path]).is_valid


@pytest.mark.parametrize("text", ["", "---\n", "max_bypasses: -1\n", "other: 1\n"])
def test_effect_node_bypass_a_damaged_count_file_fails_the_load(
    tmp_path: Path, text: str
) -> None:
    damaged = tmp_path / "ratchet.yaml"
    damaged.write_text(text, encoding="utf-8")
    with pytest.raises(ModelOnexError):
        ValidatorEffectNodeBypass.with_baseline_file(damaged)


def test_effect_node_bypass_the_count_file_header_names_the_burn_down_ticket() -> None:
    header = "\n".join(
        line
        for line in _RATCHET.read_text(encoding="utf-8").splitlines()
        if line.startswith("#")
    )
    assert "OMN-24432" in header
    assert "shrink-only" in header


def test_effect_node_bypass_the_checked_in_baseline_count_equals_the_findings_of_the_tree() -> (
    None
):
    held = parse_baseline(_RATCHET.read_text(encoding="utf-8"))["max_bypasses"]
    assert held > 0, "the count file holds the inventory of bypasses that predate it"
    # base_ref HEAD: this test is about the count equalling the findings, not about a base branch a
    # shallow checkout may not carry.
    held_run = ValidatorEffectNodeBypass.with_baseline_file(
        _RATCHET, base_ref="HEAD"
    ).validate([_ROOT])
    assert held_run.is_valid
    assert f"{held} bypasses" in held_run.summary


def _listen() -> tuple[EventBusInmemory, dict[str, list[ModelEventMessage]]]:
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
    return bus, listened


def test_effect_node_bypass_bus_error_chain_a_planted_call_puts_a_run_and_a_triggered_event(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bus, listened = _listen()
    monkeypatch.setattr(event_bus_inmemory, "EventBusInmemory", lambda: bus)
    monkeypatch.chdir(_ROOT)
    target = _plant(tmp_path, "planted", _PLANTED_CLI)
    report = tmp_path / "report.json"

    exit_code = main(
        ValidatorEffectNodeBypass,
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
    assert listened["triggered"][0].key == b"effect_node_bypass"


def test_effect_node_bypass_bus_golden_chain_a_clean_run_puts_one_run_event_and_no_triggered_event(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bus, listened = _listen()
    monkeypatch.setattr(event_bus_inmemory, "EventBusInmemory", lambda: bus)
    monkeypatch.chdir(_ROOT)
    target = _plant(tmp_path, "clean", "VALUE = 1\n")

    exit_code = main(
        ValidatorEffectNodeBypass,
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
