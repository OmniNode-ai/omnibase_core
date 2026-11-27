# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""OMN-26616 AC1: a customer install does not run developer-only doctor checks."""

from pathlib import Path

import pytest
from click.testing import CliRunner

from omnibase_core.cli import cli_doctor
from omnibase_core.doctor.checks import CheckDocker, CheckLinear, CheckReposSynced
from omnibase_core.doctor.doctor_check_base import DoctorCheckBase
from omnibase_core.enums.enum_health_status_value import EnumHealthStatusValue
from omnibase_core.models.doctor.model_doctor_check_result import (
    ModelDoctorCheckResult,
)

DEVELOPER_ONLY = (CheckDocker, CheckLinear, CheckReposSynced)


@pytest.fixture
def ran(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Replace every check's run() with a recorder so nothing touches the host."""
    calls: list[str] = []

    def make(cls: type[DoctorCheckBase]) -> None:
        def run(self: DoctorCheckBase) -> ModelDoctorCheckResult:
            calls.append(cls.__name__)
            return ModelDoctorCheckResult(
                name=self.check_name,
                category=self.category,
                status=EnumHealthStatusValue.HEALTHY,
                message="ok",
            )

        monkeypatch.setattr(cls, "run", run)

    for cls in cli_doctor._BUILTIN_CHECKS:
        make(cls)
    return calls


def test_customer_install_skips_developer_only_checks(
    ran: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("OMNI_HOME", raising=False)
    result = CliRunner().invoke(cli_doctor.doctor, ["--json"])
    assert result.exit_code == 0, result.output
    for cls in DEVELOPER_ONLY:
        assert cls.__name__ not in ran
        assert cls.__name__ not in result.output
    assert "CheckPythonVersion" in ran


def test_missing_omni_home_directory_is_still_a_customer_install(
    ran: list[str], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("OMNI_HOME", str(tmp_path / "does-not-exist"))
    CliRunner().invoke(cli_doctor.doctor, ["--json"])
    assert not set(ran) & {cls.__name__ for cls in DEVELOPER_ONLY}


def test_developer_install_still_runs_developer_only_checks(
    ran: list[str], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("OMNI_HOME", str(tmp_path))
    CliRunner().invoke(cli_doctor.doctor, ["--json"])
    assert {cls.__name__ for cls in DEVELOPER_ONLY} <= set(ran)
