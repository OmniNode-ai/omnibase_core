# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""OMN-26616 AC1/AC4: the real doctor checks on an empty customer machine.

No check's outcome is replaced. The machine is empty: an empty home directory, no registry, no Kafka, Linear, PostgreSQL or worktree settings and a PATH with no Node.js on it. A developer-only check that is run, counted or named fails the test, and the command must exit 0.
"""

from __future__ import annotations

import json
import re
import stat
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any, NoReturn

import pytest
from click.testing import CliRunner

from omnibase_core.cli import cli_doctor
from omnibase_core.doctor import checks, doctor_registry
from omnibase_core.doctor.doctor_check_base import DoctorCheckBase
from omnibase_core.enums.enum_doctor_category import EnumDoctorCategory
from omnibase_core.enums.enum_health_status_value import EnumHealthStatusValue
from omnibase_core.models.doctor.model_doctor_check_result import ModelDoctorCheckResult

_DEVELOPER_ONLY: tuple[type[DoctorCheckBase], ...] = (
    checks.CheckDocker,
    checks.CheckEnvVars,
    checks.CheckLinear,
    checks.CheckReposSynced,
    checks.CheckStaleWorktrees,
)

_SETTINGS: tuple[str, ...] = (
    "OMNI_HOME",
    "OMNI_WORKTREES",
    "KAFKA_BOOTSTRAP_SERVERS",
    "LINEAR_API_KEY",
    "POSTGRES_HOST",
    "POSTGRES_PORT",
)

_ALL_CAPS_NAME = re.compile(r"\b[A-Z][A-Z0-9]*_[A-Z0-9_]+\b")


@pytest.fixture
def customer_machine(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> list[str]:
    """An empty customer machine; returns the developer-only checks that ran."""
    home = tmp_path / "home"
    home.mkdir()
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()

    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("PATH", str(bin_dir))
    for name in _SETTINGS:
        monkeypatch.delenv(name, raising=False)

    ran: list[str] = []
    for cls in _DEVELOPER_ONLY:
        original_run: Callable[[DoctorCheckBase], ModelDoctorCheckResult] = cls.run

        def wrapper(
            self: DoctorCheckBase,
            _original: Callable[
                [DoctorCheckBase], ModelDoctorCheckResult
            ] = original_run,
        ) -> ModelDoctorCheckResult:
            ran.append(self.__class__.__name__)
            return _original(self)

        monkeypatch.setattr(cls, "run", wrapper)

    return ran


def _doctor_json() -> tuple[int, dict[str, Any]]:
    result = CliRunner().invoke(cli_doctor.doctor, ["--json"])
    return result.exit_code, json.loads(result.output)


def test_no_developer_check_runs_or_is_counted(customer_machine: list[str]) -> None:
    exit_code, body = _doctor_json()
    assert exit_code == 0, f"expected exit 0, got {exit_code}"
    assert customer_machine == [], f"developer-only checks ran: {customer_machine}"
    assert body["total"] == len(body["checks"]), "total does not match number of checks"
    names = {check["name"] for check in body["checks"]}
    dev_names = {cls.check_name for cls in _DEVELOPER_ONLY}
    assert not names & dev_names, (
        f"developer-only check names present: {names & dev_names}"
    )


def test_empty_customer_machine_exits_zero_with_no_failures(
    customer_machine: list[str],
) -> None:
    exit_code, body = _doctor_json()
    assert exit_code == 0, f"expected exit 0, got {exit_code}"
    assert body["failed"] == 0, f"expected 0 failed, got {body['failed']}"


def test_human_output_has_no_repos_heading_and_no_raw_text(
    customer_machine: list[str],
) -> None:
    result = CliRunner().invoke(cli_doctor.doctor, [])
    assert result.exit_code == 0, f"expected exit 0, got {result.exit_code}"
    output = result.output
    assert "Repos" not in output, "output contains 'Repos'"
    assert "[Errno" not in output, "output contains '[Errno'"
    assert "Traceback" not in output, "output contains 'Traceback'"
    assert _ALL_CAPS_NAME.search(output) is None, (
        "output contains ALL_CAPS environment variable names"
    )


def test_missing_nodejs_is_plain_and_does_not_fail_a_customer(
    customer_machine: list[str],
) -> None:
    exit_code, body = _doctor_json()
    assert exit_code == 0, f"expected exit 0, got {exit_code}"
    node_check = next(
        check for check in body["checks"] if check["name"] == "Node.js version"
    )
    message = node_check["message"]
    assert "Errno" not in message, "message contains 'Errno'"
    assert "Node.js is not installed." in message, (
        "message missing 'Node.js is not installed.'"
    )
    assert "Fix:" in message, "message missing 'Fix:'"


def test_nodejs_that_exits_with_an_error_is_plain_and_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    node_script = bin_dir / "node"
    node_script.write_text("#!/bin/sh\necho RAWSECRET >&2\nexit 3\n")
    node_script.chmod(
        stat.S_IXUSR
        | stat.S_IXGRP
        | stat.S_IXOTH
        | stat.S_IRUSR
        | stat.S_IRGRP
        | stat.S_IROTH
    )
    monkeypatch.setenv("PATH", str(bin_dir))

    result = checks.CheckJsRuntime().run()
    assert result.status == EnumHealthStatusValue.UNHEALTHY, (
        f"expected UNHEALTHY, got {result.status}"
    )
    assert "RAWSECRET" not in result.message, "message contains 'RAWSECRET'"
    assert "Fix:" in result.message, "message missing 'Fix:'"


def test_nodejs_that_does_not_answer_is_plain_and_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _raise_timeout(*_args: object, **_kwargs: object) -> NoReturn:
        raise subprocess.TimeoutExpired(cmd="node --version", timeout=5)

    monkeypatch.setattr(subprocess, "run", _raise_timeout)

    result = checks.CheckJsRuntime().run()
    assert result.status == EnumHealthStatusValue.UNHEALTHY, (
        f"expected UNHEALTHY, got {result.status}"
    )
    assert "node --version" in result.message, "message missing 'node --version'"
    assert "timed out" not in result.message, "message contains 'timed out'"
    assert "Fix:" in result.message, "message missing 'Fix:'"


def test_a_crashed_check_is_reported_in_plain_words_not_exception_text() -> None:
    class _Crashing(DoctorCheckBase):
        check_id = "crashing"
        check_name = "Crashing"
        category = EnumDoctorCategory.ENVIRONMENT

        def run(self) -> ModelDoctorCheckResult:
            raise OSError("RAWSECRET /private/path/leak.py")

    registry = doctor_registry.DoctorRegistry()
    registry.register(_Crashing)
    (result,) = registry.run_all()
    assert "RAWSECRET" not in result.message, "message contains 'RAWSECRET'"
    assert "leak.py" not in result.message, "message contains 'leak.py'"
    assert "Fix:" in result.message, "message missing 'Fix:'"
