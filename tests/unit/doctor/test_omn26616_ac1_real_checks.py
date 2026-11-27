# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""OMN-26616 AC1/AC4: the real doctor checks on an empty customer machine.

No check's outcome is replaced. The machine is empty: an empty home directory,
no registry, no Kafka, Linear, PostgreSQL or worktree settings and a PATH with
no Node.js on it. A developer-only check that is run, counted or named fails
the test, and the command must exit 0.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

from omnibase_core.cli import cli_doctor
from omnibase_core.doctor.checks import (
    CheckDocker,
    CheckEnvVars,
    CheckLinear,
    CheckReposSynced,
    CheckStaleWorktrees,
)
from omnibase_core.doctor.doctor_check_base import DoctorCheckBase
from omnibase_core.doctor.doctor_registry import DoctorRegistry
from omnibase_core.enums.enum_doctor_category import EnumDoctorCategory
from omnibase_core.models.doctor.model_doctor_check_result import (
    ModelDoctorCheckResult,
)

_DEVELOPER_ONLY: tuple[type[DoctorCheckBase], ...] = (
    CheckDocker,
    CheckEnvVars,
    CheckLinear,
    CheckReposSynced,
    CheckStaleWorktrees,
)
_SETTINGS = (
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
    empty_bin = tmp_path / "bin"
    empty_bin.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("PATH", str(empty_bin))
    for name in _SETTINGS:
        monkeypatch.delenv(name, raising=False)

    ran: list[str] = []

    def tripwire(cls: type[DoctorCheckBase]) -> None:
        # Record the call, then run the real check body unchanged.
        real = cls.run

        def run(self: DoctorCheckBase) -> ModelDoctorCheckResult:
            ran.append(cls.__name__)
            return real(self)

        monkeypatch.setattr(cls, "run", run)

    for cls in _DEVELOPER_ONLY:
        tripwire(cls)
    return ran


def _doctor_json() -> tuple[int, dict[str, Any]]:
    result = CliRunner().invoke(cli_doctor.doctor, ["--json"])
    body: dict[str, Any] = json.loads(result.output)
    return result.exit_code, body


def test_no_developer_check_runs_or_is_counted(customer_machine: list[str]) -> None:
    exit_code, body = _doctor_json()
    names = {check["name"] for check in body["checks"]}
    developer_names = {cls.check_name for cls in _DEVELOPER_ONLY}
    assert customer_machine == []
    assert body["total"] == len(body["checks"])
    assert not names & developer_names
    assert exit_code == 0, body


def test_empty_customer_machine_exits_zero_with_no_failures(
    customer_machine: list[str],
) -> None:
    exit_code, body = _doctor_json()
    assert exit_code == 0, body
    assert body["failed"] == 0, body


def test_human_output_has_no_repos_heading_and_no_raw_text(
    customer_machine: list[str],
) -> None:
    result = CliRunner().invoke(cli_doctor.doctor, [])
    assert result.exit_code == 0, result.output
    assert "Repos" not in result.output
    assert "[Errno" not in result.output
    assert "Traceback" not in result.output
    assert not _ALL_CAPS_NAME.search(result.output), result.output


def test_missing_nodejs_is_plain_and_does_not_fail_a_customer(
    customer_machine: list[str],
) -> None:
    exit_code, body = _doctor_json()
    node = [c for c in body["checks"] if c["name"] == "Node.js version"]
    assert node
    assert "Errno" not in node[0]["message"]
    assert "Node.js is not installed." in node[0]["message"]
    assert "Fix:" in node[0]["message"]
    assert exit_code == 0


def test_a_crashed_check_is_reported_in_plain_words_not_exception_text() -> None:
    class _Crashing(DoctorCheckBase):
        check_id = "crashing"
        check_name = "Crashing"
        category = EnumDoctorCategory.ENVIRONMENT

        def run(self) -> ModelDoctorCheckResult:
            raise OSError("RAWSECRET /private/path/leak.py")

    registry = DoctorRegistry()
    registry.register(_Crashing)

    (result,) = registry.run_all()

    assert "RAWSECRET" not in result.message
    assert "leak.py" not in result.message
    assert "Fix:" in result.message
