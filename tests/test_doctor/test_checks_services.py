# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from unittest.mock import MagicMock, patch

import pytest

from omnibase_core.doctor.checks.check_docker import CheckDocker

pytestmark = pytest.mark.unit
from omnibase_core.doctor.checks.check_kafka import CheckKafka
from omnibase_core.doctor.checks.check_linear import CheckLinear
from omnibase_core.doctor.checks.check_postgres import CheckPostgres
from omnibase_core.enums.enum_doctor_category import EnumDoctorCategory
from omnibase_core.enums.enum_health_status_value import EnumHealthStatusValue


def test_check_docker_pass():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        result = CheckDocker().run()
    assert result.status == EnumHealthStatusValue.HEALTHY
    assert result.category == EnumDoctorCategory.SERVICES


def test_check_docker_fail():
    with patch("subprocess.run", side_effect=FileNotFoundError):
        result = CheckDocker().run()
    assert result.status == EnumHealthStatusValue.UNHEALTHY


def test_check_kafka_pass():
    with patch("socket.create_connection", return_value=MagicMock()):
        result = CheckKafka().run()
    assert result.status == EnumHealthStatusValue.HEALTHY


def test_check_kafka_fail():
    with patch("socket.create_connection", side_effect=OSError("Connection refused")):
        result = CheckKafka().run()
    assert result.status == EnumHealthStatusValue.UNHEALTHY


def test_check_postgres_pass():
    with patch("socket.create_connection", return_value=MagicMock()):
        result = CheckPostgres().run()
    assert result.status == EnumHealthStatusValue.HEALTHY


def test_check_postgres_fail():
    with patch("socket.create_connection", side_effect=OSError("Connection refused")):
        result = CheckPostgres().run()
    assert result.status == EnumHealthStatusValue.UNHEALTHY


def test_check_linear_pass():
    with (
        patch.dict(
            "os.environ",
            {"LINEAR_API_KEY": "test-token"},  # pragma: allowlist secret
        ),
        patch("subprocess.run") as mock_run,
    ):
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = '{"data":{}}'
        result = CheckLinear().run()
    assert result.status == EnumHealthStatusValue.HEALTHY
