# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Allowlist stack-shape validator (OMN-21891, one-runtime plan task T1).

The fixtures hold a stack of compose files and a data file naming the allowed services; every
rule value comes from the data file or the shipped contract, so a service name appears here only
as a fixture.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.validation import checker_stack_shape as checker
from omnibase_core.validation.validator_stack_shape import ValidatorStackShape
from omnibase_core.validators.no_unguarded_git_subprocess import scrub_git_location_env

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[3]
VALIDATION = ROOT / "src" / "omnibase_core" / "validation"
DATA_PATH = "config/validation/stack_shape.yaml"

LANES = (
    "dev",
    "stability",
    "collaborator",
    "dev-105",
    "dev-200",
    "dev-202",
    "prepr-a",
    "prepr-b",
)
PLANTED = ("projection-claude-hook-events-writer", "cost-estimator-web")


def _lane_file(lane: str) -> str:
    return f"docker/docker-compose.{lane}.yml"


def _compose(**services: dict[str, Any]) -> dict[str, Any]:
    return {"services": {name: dict(body) for name, body in services.items()}}


def _clean_compose() -> dict[str, Any]:
    return _compose(
        runtime={"image": "x"},
        postgres={"image": "p"},
        migrate={"image": "m", "restart": "no"},
    )


def _data(
    baseline: list[dict[str, str]] | None = None, **optional: Any
) -> dict[str, Any]:
    return {
        "runtime": {"services": ["runtime"], "max_replicas": 1},
        "dependencies": ["postgres"],
        "one_shots": ["migrate"],
        "lanes": {lane: {"compose_files": [_lane_file(lane)]} for lane in LANES},
        "baseline": baseline or [],
        **optional,
    }


def _write(root: Path, relative: str, document: object) -> None:
    target = root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t.invalid", *args],
        cwd=repo,
        env=scrub_git_location_env(),
        check=True,
        capture_output=True,
    )


def _stack(
    root: Path,
    data: dict[str, Any] | None = None,
    overrides: dict[str, dict[str, Any]] | None = None,
) -> Path:
    """Write a clean stack, with ``overrides`` replacing lane compose documents."""
    _write(root, DATA_PATH, data or _data())
    for lane in LANES:
        document = (overrides or {}).get(lane, _clean_compose())
        _write(root, _lane_file(lane), document)
    return root / DATA_PATH


def _issues(root: Path, base_ref: str | None = None) -> list[tuple[str, str]]:
    result = ValidatorStackShape(root=root, base_ref=base_ref).validate(
        [root / DATA_PATH]
    )
    return [(str(i.code), i.message) for i in result.issues]


def _codes(root: Path, base_ref: str | None = None) -> list[str]:
    return [code for code, _ in _issues(root, base_ref)]


def test_clean_stack_passes(tmp_path: Path) -> None:
    _stack(tmp_path)
    assert _issues(tmp_path) == []


@pytest.mark.parametrize("lane", LANES[:3])
@pytest.mark.parametrize(
    "form",
    [
        {"command": "python -m something"},
        {"command": ["python", "-m", "something"]},
        {"entrypoint": "python -m something", "command": "onex-runtime"},
        {"entrypoint": ["python", "-m", "something"]},
    ],
)
def test_planted_runtime_command_is_refused(
    tmp_path: Path, lane: str, form: dict[str, Any]
) -> None:
    _stack(
        tmp_path,
        data=_data(image_commands=[{"command": "onex-runtime", "reason": "runtime"}]),
        overrides={lane: _compose(runtime=form)},
    )
    issues = _issues(tmp_path)
    assert len(issues) == 1
    assert issues[0][0] == checker.RULE_IMAGE_COMMAND
    assert "runtime" in issues[0][1]
    assert "python -m something" in issues[0][1]
    assert _lane_file(lane) in issues[0][1]
    assert lane in issues[0][1]


@pytest.mark.parametrize(
    "form",
    [
        {"command": "onex-runtime --verbose"},
        {"command": ["onex-runtime", "--verbose", 1]},
        {"entrypoint": "onex-runtime", "command": "--verbose"},
        {"entrypoint": ["onex-runtime"], "command": ["--verbose"]},
        {"command": "'onex-runtime' --verbose"},
        {"entrypoint": [], "command": "onex-runtime"},
        {"entrypoint": None, "command": "onex-runtime"},
    ],
)
def test_allowed_runtime_command_passes(tmp_path: Path, form: dict[str, Any]) -> None:
    _stack(
        tmp_path,
        data=_data(image_commands=[{"command": "onex-runtime", "reason": "runtime"}]),
        overrides={"dev": _compose(runtime=form)},
    )
    assert _issues(tmp_path) == []


def test_all_commands_and_console_scripts_listed_pass(tmp_path: Path) -> None:
    _stack(
        tmp_path,
        data=_data(
            image_commands=[{"command": "onex-runtime", "reason": "runtime"}],
            console_scripts_file="pyproject.toml",
            console_scripts_allowed=[{"name": "onex-runtime", "reason": "runtime"}],
            developer_only=[{"name": "onex-dev", "reason": "development"}],
        ),
        overrides={
            lane: _compose(runtime={"command": "onex-runtime --verbose"})
            for lane in LANES
        },
    )
    (tmp_path / "pyproject.toml").write_text(
        '[project.scripts]\nonex-runtime = "pkg:main"\nonex-dev = "pkg:dev"\n',
        encoding="utf-8",
    )
    assert _issues(tmp_path) == []


def test_non_runtime_commands_are_not_refused(tmp_path: Path) -> None:
    _stack(
        tmp_path,
        data=_data([_entry("dev", "legacy")], image_commands=[]),
        overrides={
            "dev": _compose(
                runtime={},
                postgres={"command": "python -m something"},
                migrate={"command": "python -m something"},
                legacy={"command": "python -m something"},
            )
        },
    )
    assert _issues(tmp_path) == []


def test_absent_image_commands_does_not_check_commands(tmp_path: Path) -> None:
    _stack(
        tmp_path,
        overrides={"dev": _compose(runtime={"command": "python -m something"})},
    )
    assert _issues(tmp_path) == []


def test_empty_image_commands_refuses_every_command(tmp_path: Path) -> None:
    _stack(
        tmp_path,
        data=_data(image_commands=[]),
        overrides={"dev": _compose(runtime={"command": "onex-runtime"})},
    )
    codes = _codes(tmp_path)
    assert len(codes) == 1
    assert codes == [checker.RULE_IMAGE_COMMAND]


@pytest.mark.parametrize(
    "form", [{}, {"command": None}, {"command": []}, {"command": ""}]
)
def test_image_default_is_not_checked(tmp_path: Path, form: dict[str, Any]) -> None:
    _stack(
        tmp_path,
        data=_data(image_commands=[]),
        overrides={"dev": _compose(runtime=form)},
    )
    assert _issues(tmp_path) == []


def test_unbalanced_command_quotes_fall_back_to_whitespace(tmp_path: Path) -> None:
    _stack(
        tmp_path,
        data=_data(image_commands=[]),
        overrides={"dev": _compose(runtime={"command": 'python -m "something'})},
    )
    issues = _issues(tmp_path)
    assert len(issues) == 1
    assert issues[0][0] == checker.RULE_IMAGE_COMMAND
    assert 'python -m "something' in issues[0][1]


def test_planted_console_script_is_refused(tmp_path: Path) -> None:
    _stack(
        tmp_path,
        data=_data(console_scripts_file="pyproject.toml", console_scripts_allowed=[]),
    )
    (tmp_path / "pyproject.toml").write_text(
        '[project.scripts]\nplanted-script = "pkg:main"\n', encoding="utf-8"
    )
    issues = _issues(tmp_path)
    assert len(issues) == 1
    assert issues[0][0] == checker.RULE_CONSOLE_SCRIPT
    assert "planted-script" in issues[0][1]


@pytest.mark.parametrize("text", ['[project]\nname = "pkg"\n', ""])
def test_no_console_scripts_table_passes(tmp_path: Path, text: str) -> None:
    _stack(
        tmp_path,
        data=_data(console_scripts_file="pyproject.toml", console_scripts_allowed=[]),
    )
    (tmp_path / "pyproject.toml").write_text(text, encoding="utf-8")
    assert _issues(tmp_path) == []


@pytest.mark.parametrize(
    "text", [None, "[project.scripts", '[project]\nscripts = "bad"']
)
def test_missing_or_unreadable_console_scripts_fail(
    tmp_path: Path, text: str | None
) -> None:
    _stack(
        tmp_path,
        data=_data(console_scripts_file="pyproject.toml", console_scripts_allowed=[]),
    )
    if text is not None:
        (tmp_path / "pyproject.toml").write_text(text, encoding="utf-8")
    issues = _issues(tmp_path)
    assert len(issues) == 1
    assert issues[0][0] == checker.RULE_CONSOLE_SCRIPTS_UNREADABLE
    assert "pyproject.toml" in issues[0][1]


def test_console_scripts_target_judges_the_whole_stack(tmp_path: Path) -> None:
    _stack(
        tmp_path,
        data=_data(console_scripts_file="pyproject.toml", console_scripts_allowed=[]),
        overrides={"stability": _compose(runtime={}, intruder={})},
    )
    target = tmp_path / "pyproject.toml"
    target.write_text("", encoding="utf-8")
    result = ValidatorStackShape(root=tmp_path).validate([target])
    assert [i.code for i in result.issues] == [checker.RULE_NOT_ALLOWED]


@pytest.mark.parametrize(
    ("optional", "malformed"),
    [
        ({"image_commands": [{"command": "onex-runtime"}]}, "reason"),
        ({"image_commands": [{"command": "onex-runtime", "reason": " "}]}, "reason"),
        ({"image_commands": [{"command": "", "reason": "runtime"}]}, "command"),
        ({"image_commands": [{"command": 1, "reason": "runtime"}]}, "command"),
        ({"image_commands": ["onex-runtime"]}, "image_commands"),
        ({"image_commands": None}, "image_commands"),
        ({"image_commands": {}}, "image_commands"),
        ({"image_commands": [{"command": "x", "reason": "r"}] * 2}, "duplicate"),
        ({"console_scripts_file": "pyproject.toml"}, "console_scripts_allowed"),
        ({"console_scripts_allowed": []}, "console_scripts_file"),
        ({"developer_only": []}, "console_scripts_file"),
        (
            {"console_scripts_file": "", "console_scripts_allowed": []},
            "console_scripts_file",
        ),
        (
            {"console_scripts_file": None, "console_scripts_allowed": []},
            "console_scripts_file",
        ),
        (
            {"console_scripts_file": 1, "console_scripts_allowed": []},
            "console_scripts_file",
        ),
        (
            {"console_scripts_file": "pyproject.toml", "console_scripts_allowed": None},
            "console_scripts_allowed",
        ),
        (
            {
                "console_scripts_file": "pyproject.toml",
                "console_scripts_allowed": [{"name": "x"}],
            },
            "reason",
        ),
        (
            {
                "console_scripts_file": "pyproject.toml",
                "console_scripts_allowed": [{"name": "x", "reason": "r"}] * 2,
            },
            "duplicate",
        ),
        (
            {
                "console_scripts_file": "pyproject.toml",
                "console_scripts_allowed": [{"name": "x", "reason": "r"}],
                "developer_only": [{"name": "x", "reason": "r"}],
            },
            "developer_only",
        ),
        (
            {
                "console_scripts_file": "pyproject.toml",
                "console_scripts_allowed": [],
                "developer_only": [{"name": "x", "reason": " "}],
            },
            "reason",
        ),
        (
            {
                "console_scripts_file": "pyproject.toml",
                "console_scripts_allowed": [],
                "developer_only": [{"name": "x", "reason": "r"}] * 2,
            },
            "duplicate",
        ),
    ],
)
def test_malformed_command_and_script_data_fail(
    tmp_path: Path, optional: dict[str, Any], malformed: str
) -> None:
    data = _data(**optional)
    with pytest.raises(ModelOnexError, match=malformed):
        checker.parse_stack_shape_data(yaml.safe_dump(data))
    _stack(tmp_path, data=data)
    assert _codes(tmp_path) == [checker.RULE_DATA_INVALID]


@pytest.mark.parametrize("planted", PLANTED)
@pytest.mark.parametrize("lane", LANES)
def test_planted_service_is_refused_by_name_on_every_lane(
    tmp_path: Path, lane: str, planted: str
) -> None:
    document = _clean_compose()
    document["services"][planted] = {"image": "x", "profiles": ["main"]}
    _stack(tmp_path, overrides={lane: document})
    issues = _issues(tmp_path)
    assert [code for code, _ in issues] == [checker.RULE_NOT_ALLOWED]
    message = issues[0][1]
    assert planted in message
    assert _lane_file(lane) in message


def test_both_planted_copies_are_each_reported(tmp_path: Path) -> None:
    document = _clean_compose()
    for planted in PLANTED:
        document["services"][planted] = {"image": "x"}
    _stack(tmp_path, overrides={"dev": document})
    messages = [m for c, m in _issues(tmp_path) if c == checker.RULE_NOT_ALLOWED]
    assert len(messages) == 2
    for planted in PLANTED:
        assert any(planted in m for m in messages)


def test_a_compose_file_target_judges_the_whole_stack(tmp_path: Path) -> None:
    document = _clean_compose()
    document["services"]["intruder"] = {"image": "x"}
    _stack(tmp_path, overrides={"stability": document})
    result = ValidatorStackShape(root=tmp_path).validate([tmp_path / _lane_file("dev")])
    assert [i.code for i in result.issues] == [checker.RULE_NOT_ALLOWED]


def test_a_file_outside_the_stack_is_not_judged(tmp_path: Path) -> None:
    _stack(tmp_path)
    stray = tmp_path / "docker" / "docker-compose.stray.yml"
    _write(tmp_path, "docker/docker-compose.stray.yml", _compose(rogue={}))
    assert ValidatorStackShape(root=tmp_path).validate([stray]).issues == []


def test_every_allowed_kind_passes(tmp_path: Path) -> None:
    document = _compose(runtime={}, postgres={}, migrate={}, baselined={})
    _stack(
        tmp_path,
        data=_data(
            [{"file": _lane_file("dev"), "service": "baselined", "ticket": "OMN-1"}]
        ),
        overrides={"dev": document},
    )
    assert _issues(tmp_path) == []


def test_baseline_entry_is_per_file(tmp_path: Path) -> None:
    document = _compose(runtime={}, baselined={})
    _stack(
        tmp_path,
        data=_data(
            [{"file": _lane_file("dev"), "service": "baselined", "ticket": "OMN-1"}]
        ),
        overrides={"dev": document, "stability": document},
    )
    assert _codes(tmp_path) == [checker.RULE_NOT_ALLOWED]


@pytest.mark.parametrize(
    "form",
    [
        {"replicas": 2},
        {"scale": 2},
        {"deploy": {"replicas": 2}},
        {"replicas": "2"},
        {"replicas": "${RUNTIME_REPLICAS:-2}"},
        {"replicas": 1, "scale": 3},
    ],
)
def test_replicas_of_the_runtime_service_above_the_limit_fail(
    tmp_path: Path, form: dict[str, Any]
) -> None:
    document = _compose(runtime={"image": "x", **form})
    _stack(tmp_path, overrides={"dev": document})
    issues = _issues(tmp_path)
    assert [code for code, _ in issues] == [checker.RULE_REPLICAS]
    assert "runtime" in issues[0][1]


@pytest.mark.parametrize(
    "form",
    [{}, {"replicas": 1}, {"scale": 1}, {"deploy": {"replicas": 1}}, {"deploy": {}}],
)
def test_replicas_within_the_limit_pass(tmp_path: Path, form: dict[str, Any]) -> None:
    _stack(tmp_path, overrides={"dev": _compose(runtime={"image": "x", **form})})
    assert _issues(tmp_path) == []


def test_replicas_limit_comes_from_the_data_file(tmp_path: Path) -> None:
    data = _data()
    data["runtime"] = {"services": ["runtime"], "max_replicas": 3}
    _stack(
        tmp_path,
        data=data,
        overrides={"dev": _compose(runtime={"replicas": 3})},
    )
    assert _issues(tmp_path) == []


def test_unreadable_replica_count_fails(tmp_path: Path) -> None:
    _stack(tmp_path, overrides={"dev": _compose(runtime={"replicas": "${R}"})})
    assert _codes(tmp_path) == [checker.RULE_REPLICAS]


def test_missing_lane_compose_file_fails(tmp_path: Path) -> None:
    _stack(tmp_path)
    (tmp_path / _lane_file("dev-105")).unlink()
    issues = _issues(tmp_path)
    assert [c for c, _ in issues] == [checker.RULE_FILE_MISSING]
    assert _lane_file("dev-105") in issues[0][1]


def test_a_service_list_without_services_key_fails_loudly(tmp_path: Path) -> None:
    _stack(tmp_path, overrides={"dev": {"version": "3"}})
    assert _codes(tmp_path) == [checker.RULE_FILE_UNREADABLE]


def test_a_repeated_nested_key_reads_as_its_last_value(tmp_path: Path) -> None:
    _stack(tmp_path)
    (tmp_path / _lane_file("dev")).write_text(
        "services:\n  runtime:\n    healthcheck:\n      interval: 1s\n      interval: 2s\n",
        encoding="utf-8",
    )
    assert _issues(tmp_path) == []


def test_a_compose_file_that_is_not_a_mapping_is_unreadable(tmp_path: Path) -> None:
    _stack(tmp_path)
    (tmp_path / _lane_file("dev")).write_text("- runtime\n", encoding="utf-8")
    assert _codes(tmp_path) == [checker.RULE_FILE_UNREADABLE]


# --- baseline: current-state rules --------------------------------------------------------------


def test_baseline_entry_for_a_missing_service_fails(tmp_path: Path) -> None:
    _stack(
        tmp_path,
        data=_data([{"file": _lane_file("dev"), "service": "gone", "ticket": "OMN-1"}]),
    )
    issues = _issues(tmp_path)
    assert [c for c, _ in issues] == [checker.RULE_BASELINE]
    assert "gone" in issues[0][1]


def test_baseline_entry_without_ticket_fails(tmp_path: Path) -> None:
    document = _compose(runtime={}, baselined={})
    _stack(
        tmp_path,
        data=_data([{"file": _lane_file("dev"), "service": "baselined", "ticket": ""}]),
        overrides={"dev": document},
    )
    assert checker.RULE_BASELINE in _codes(tmp_path)


def test_baseline_entry_for_an_unlisted_file_fails(tmp_path: Path) -> None:
    _stack(
        tmp_path,
        data=_data([{"file": "docker/nowhere.yml", "service": "x", "ticket": "OMN-1"}]),
    )
    assert _codes(tmp_path) == [checker.RULE_BASELINE]


# --- baseline: merge-base ratchet ----------------------------------------------------------------


def _committed_stack(
    root: Path,
    base_baseline: list[dict[str, str]] | None,
    head_baseline: list[dict[str, str]],
    head_overrides: dict[str, dict[str, Any]],
) -> None:
    """Commit a base stack (``base_baseline`` None: no data file yet), then write the head."""
    _git(root, "init", "-q")
    _git(root, "commit", "-q", "--allow-empty", "-m", "empty")
    if base_baseline is not None:
        base_overrides = {
            lane: _compose(
                runtime={},
                **{
                    e["service"]: {}
                    for e in base_baseline
                    if e["file"] == _lane_file(lane)
                },
            )
            for lane in LANES
        }
        _stack(root, data=_data(base_baseline), overrides=base_overrides)
        _git(root, "add", ".")
        _git(root, "commit", "-q", "-m", "base")
    _stack(root, data=_data(head_baseline), overrides=head_overrides)


def _entry(lane: str, service: str) -> dict[str, str]:
    return {"file": _lane_file(lane), "service": service, "ticket": "OMN-1"}


def test_new_service_plus_new_baseline_entry_is_refused(tmp_path: Path) -> None:
    _committed_stack(
        tmp_path,
        base_baseline=[],
        head_baseline=[_entry("dev", "newcomer")],
        head_overrides={"dev": _compose(runtime={}, newcomer={})},
    )
    issues = _issues(tmp_path)
    assert [c for c, _ in issues] == [checker.RULE_BASELINE]
    assert "newcomer" in issues[0][1]


def test_unchanged_baseline_passes_against_the_base(tmp_path: Path) -> None:
    _committed_stack(
        tmp_path,
        base_baseline=[_entry("dev", "legacy")],
        head_baseline=[_entry("dev", "legacy")],
        head_overrides={"dev": _compose(runtime={}, legacy={})},
    )
    assert _issues(tmp_path) == []


def test_shrinking_the_baseline_passes(tmp_path: Path) -> None:
    _committed_stack(
        tmp_path,
        base_baseline=[_entry("dev", "legacy"), _entry("dev", "older")],
        head_baseline=[_entry("dev", "legacy")],
        head_overrides={"dev": _compose(runtime={}, legacy={})},
    )
    assert _issues(tmp_path) == []


def test_first_install_has_no_base_baseline_to_grow_from(tmp_path: Path) -> None:
    _committed_stack(
        tmp_path,
        base_baseline=None,
        head_baseline=[_entry("dev", "legacy")],
        head_overrides={"dev": _compose(runtime={}, legacy={})},
    )
    assert _issues(tmp_path) == []


def test_baseline_base_ref_comes_from_the_caller(tmp_path: Path) -> None:
    _committed_stack(
        tmp_path,
        base_baseline=[],
        head_baseline=[_entry("dev", "newcomer")],
        head_overrides={"dev": _compose(runtime={}, newcomer={})},
    )
    assert _codes(tmp_path, base_ref="HEAD") == [checker.RULE_BASELINE]
    assert _codes(tmp_path, base_ref="no-such-ref") == []


def test_baseline_entry_follows_a_moved_compose_file(tmp_path: Path) -> None:
    _committed_stack(
        tmp_path,
        base_baseline=[_entry("dev", "legacy")],
        head_baseline=[_entry("dev", "legacy")],
        head_overrides={"dev": _compose(runtime={}, legacy={})},
    )
    _git(tmp_path, "mv", _lane_file("dev"), "docker/docker-compose.dev-renamed.yml")
    data = _data(
        [{**_entry("dev", "legacy"), "file": "docker/docker-compose.dev-renamed.yml"}]
    )
    data["lanes"]["dev"] = {"compose_files": ["docker/docker-compose.dev-renamed.yml"]}
    _write(tmp_path, DATA_PATH, data)
    assert _issues(tmp_path) == []


# --- generic format ------------------------------------------------------------------------------


def test_no_rule_value_lives_in_code_or_contract() -> None:
    contract = (VALIDATION / "contracts" / "stack_shape.validation.yaml").read_text(
        encoding="utf-8"
    )
    code = "".join(
        (VALIDATION / name).read_text(encoding="utf-8")
        for name in ("checker_stack_shape.py", "validator_stack_shape.py")
    )
    for name in (
        *PLANTED,
        "onex-runtime",
        "postgres",
        "redpanda",
        "planted-script",
        "onex-dev",
    ):
        assert name not in code
        assert name not in contract


def test_checker_is_pure() -> None:
    source = (VALIDATION / "checker_stack_shape.py").read_text(encoding="utf-8")
    for token in ("subprocess", "open(", "read_text", "os.environ", "os.getenv"):
        assert token not in source


def _contract() -> ModelValidatorSubcontract:
    return ValidatorStackShape(root=ROOT).contract


def test_data_parser_preserves_reasons_and_positional_defaults() -> None:
    data = checker.parse_stack_shape_data(
        yaml.safe_dump(
            _data(
                image_commands=[{"command": "onex-runtime", "reason": "runtime"}],
                console_scripts_file="pyproject.toml",
                console_scripts_allowed=[{"name": "onex-runtime", "reason": "runtime"}],
                developer_only=[{"name": "onex-dev", "reason": "development"}],
            )
        )
    )
    assert data.image_commands == {"onex-runtime": "runtime"}
    assert data.console_scripts_file == "pyproject.toml"
    assert data.console_scripts_allowed == {"onex-runtime": "runtime"}
    assert data.developer_only == {"onex-dev": "development"}
    legacy = type(data)(
        data.runtime_services,
        data.max_replicas,
        data.dependencies,
        data.one_shots,
        data.lanes,
        data.baseline,
    )
    other = checker.parse_stack_shape_data(yaml.safe_dump(_data()))
    assert legacy.image_commands is None
    assert legacy.console_scripts_file is None
    assert legacy.console_scripts_allowed == legacy.developer_only == {}
    assert legacy.console_scripts_allowed is not other.console_scripts_allowed
    assert legacy.developer_only is not other.developer_only


@pytest.mark.parametrize(
    "rule_id",
    [
        checker.RULE_IMAGE_COMMAND,
        checker.RULE_CONSOLE_SCRIPT,
        checker.RULE_CONSOLE_SCRIPTS_UNREADABLE,
    ],
)
def test_new_rules_can_be_disabled(tmp_path: Path, rule_id: str) -> None:
    _stack(
        tmp_path,
        data=_data(
            image_commands=[],
            console_scripts_file="pyproject.toml",
            console_scripts_allowed=[],
        ),
        overrides={"dev": _compose(runtime={"command": "python -m something"})},
    )
    if rule_id != checker.RULE_CONSOLE_SCRIPTS_UNREADABLE:
        (tmp_path / "pyproject.toml").write_text(
            '[project.scripts]\nplanted-script = "pkg:main"\n', encoding="utf-8"
        )
    contract = _contract()
    rows = [
        row.model_copy(update={"enabled": False}) if row.rule_id == rule_id else row
        for row in contract.rules
    ]
    result = ValidatorStackShape(
        contract.model_copy(update={"rules": rows}), root=tmp_path
    ).validate([tmp_path / DATA_PATH])
    codes = [i.code for i in result.issues]
    assert rule_id not in codes
    expected = (
        checker.RULE_CONSOLE_SCRIPT
        if rule_id == checker.RULE_IMAGE_COMMAND
        else checker.RULE_IMAGE_COMMAND
    )
    assert codes == [expected]


def test_command_keys_and_message_come_from_the_contract() -> None:
    rules = {row.rule_id: row for row in _contract().rules}
    row = rules[checker.RULE_IMAGE_COMMAND]
    rules[row.rule_id] = row.model_copy(
        update={
            "parameters": {
                "command_keys": ["launch"],
                "message": "{service}|{path}|{lanes}|{key}|{command}",
            }
        }
    )
    data = checker.parse_stack_shape_data(yaml.safe_dump(_data(image_commands=[])))
    services = {
        "runtime": {"launch": ["python", "-m", "something"], "command": "ignored"}
    }
    issues = checker.check_compose(data, "stack.yml", services, ["custom"], rules)
    assert [i.message for i in issues] == [
        "runtime|stack.yml|custom|launch|python -m something"
    ]


def test_script_table_path_targets_messages_and_order_come_from_the_contract() -> None:
    rules = {row.rule_id: row for row in _contract().rules}
    unreadable = rules[checker.RULE_CONSOLE_SCRIPTS_UNREADABLE]
    rules[unreadable.rule_id] = unreadable.model_copy(
        update={
            "parameters": {
                **(unreadable.parameters or {}),
                "table_path": ["custom", "entries"],
            }
        }
    )
    row = rules[checker.RULE_CONSOLE_SCRIPT]
    rules[row.rule_id] = row.model_copy(
        update={"parameters": {"message": "{script}|{target}|{path}"}}
    )
    scripts = checker.console_scripts(
        '[custom.entries]\nz = 1\na = "pkg:main"\n', rules
    )
    assert scripts == {"z": "1", "a": "pkg:main"}
    data = checker.parse_stack_shape_data(
        yaml.safe_dump(
            _data(console_scripts_file="scripts.toml", console_scripts_allowed=[])
        )
    )
    issues = checker.check_console_scripts(data, "scripts.toml", scripts, rules)
    assert [i.message for i in issues] == [
        "a|pkg:main|scripts.toml",
        "z|1|scripts.toml",
    ]
    legacy = checker.parse_stack_shape_data(yaml.safe_dump(_data()))
    assert checker.check_console_scripts(legacy, "scripts.toml", scripts, rules) == ()
    with pytest.raises(ModelOnexError, match=r"custom\.entries"):
        checker.console_scripts('custom = "bad"', rules)


@pytest.mark.parametrize(
    ("rule_id", "key"),
    [
        (checker.RULE_NOT_ALLOWED, "message"),
        (checker.RULE_REPLICAS, "message"),
        (checker.RULE_BASELINE, "growth_message"),
        (checker.RULE_IMAGE_COMMAND, "message"),
        (checker.RULE_IMAGE_COMMAND, "command_keys"),
        (checker.RULE_CONSOLE_SCRIPT, "message"),
        (checker.RULE_CONSOLE_SCRIPTS_UNREADABLE, "message"),
        (checker.RULE_CONSOLE_SCRIPTS_UNREADABLE, "table_path"),
    ],
)
def test_a_missing_contract_parameter_fails_at_load(rule_id: str, key: str) -> None:
    contract = _contract()
    rows = []
    for row in contract.rules:
        if row.rule_id == rule_id:
            params = {k: v for k, v in (row.parameters or {}).items() if k != key}
            row = row.model_copy(update={"parameters": params})
        rows.append(row)
    with pytest.raises(ModelOnexError):
        ValidatorStackShape(contract.model_copy(update={"rules": rows}), root=ROOT)


def test_malformed_data_file_fails_loudly(tmp_path: Path) -> None:
    _stack(tmp_path, data={"runtime": "not-a-mapping"})
    assert _codes(tmp_path) == [checker.RULE_DATA_INVALID]


def test_compose_merge_tags_are_directives_not_data(tmp_path: Path) -> None:
    _stack(tmp_path)
    (tmp_path / _lane_file("dev")).write_text(
        "services:\n"
        "  runtime:\n"
        "    ports: !override\n"
        "      - '1:1'\n"
        "    volumes: !reset []\n"
        "  postgres: !reset null\n"
        "  removed-one: !reset null\n",
        encoding="utf-8",
    )
    assert _issues(tmp_path) == []


def test_a_service_with_an_empty_body_is_still_a_service(tmp_path: Path) -> None:
    _stack(tmp_path)
    (tmp_path / _lane_file("dev")).write_text(
        "services:\n  runtime: {}\n  intruder:\n", encoding="utf-8"
    )
    issues = _issues(tmp_path)
    assert [c for c, _ in issues] == [checker.RULE_NOT_ALLOWED]
    assert "intruder" in issues[0][1]
