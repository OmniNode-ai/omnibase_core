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


def _data(baseline: list[dict[str, str]] | None = None) -> dict[str, Any]:
    return {
        "runtime": {"services": ["runtime"], "max_replicas": 1},
        "dependencies": ["postgres"],
        "one_shots": ["migrate"],
        "lanes": {lane: {"compose_files": [_lane_file(lane)]} for lane in LANES},
        "baseline": baseline or [],
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
    for name in (*PLANTED, "onex-runtime", "postgres", "redpanda"):
        assert name not in code
        assert name not in contract


def test_checker_is_pure() -> None:
    source = (VALIDATION / "checker_stack_shape.py").read_text(encoding="utf-8")
    for token in ("subprocess", "open(", "read_text", "os.environ", "os.getenv"):
        assert token not in source


def _contract() -> ModelValidatorSubcontract:
    return ValidatorStackShape(root=ROOT).contract


@pytest.mark.parametrize(
    ("rule_id", "key"),
    [
        (checker.RULE_NOT_ALLOWED, "message"),
        (checker.RULE_REPLICAS, "message"),
        (checker.RULE_BASELINE, "growth_message"),
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
