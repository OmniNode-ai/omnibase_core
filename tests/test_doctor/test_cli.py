# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from click.testing import CliRunner
from unittest.mock import patch
from omnibase_core.cli.cli_doctor import doctor
from omnibase_core.enums.enum_doctor_category import EnumDoctorCategory
from omnibase_core.enums.enum_health_status_value import EnumHealthStatusValue
from omnibase_core.models.doctor.model_doctor_check_result import ModelDoctorCheckResult


def _mock_results():
    return [
        ModelDoctorCheckResult(
            name="Docker",
            category=EnumDoctorCategory.SERVICES,
            status=EnumHealthStatusValue.HEALTHY,
            message="running",
            duration_ms=100,
        ),
    ]


def test_doctor_human_output():
    runner = CliRunner()
    with patch("omnibase_core.cli.cli_doctor.DoctorRegistry") as MockReg:
        instance = MockReg.return_value
        instance.run_all.return_value = _mock_results()
        result = runner.invoke(doctor, [])
    assert result.exit_code == 0
    assert "Docker" in result.output


def test_doctor_json_output():
    runner = CliRunner()
    with patch("omnibase_core.cli.cli_doctor.DoctorRegistry") as MockReg:
        instance = MockReg.return_value
        instance.run_all.return_value = _mock_results()
        result = runner.invoke(doctor, ["--json"])
    assert result.exit_code == 0
    assert '"total"' in result.output


def test_doctor_exits_nonzero_on_failure():
    runner = CliRunner()
    with patch("omnibase_core.cli.cli_doctor.DoctorRegistry") as MockReg:
        instance = MockReg.return_value
        instance.run_all.return_value = [
            ModelDoctorCheckResult(
                name="Broken",
                category=EnumDoctorCategory.SERVICES,
                status=EnumHealthStatusValue.UNHEALTHY,
                message="down",
            ),
        ]
        result = runner.invoke(doctor, [])
    assert result.exit_code == 1
