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
    with (
        patch.dict("os.environ", {"KAFKA_BOOTSTRAP_SERVERS": "testhost:19092"}),
        patch("socket.create_connection", return_value=MagicMock()),
    ):
        result = CheckKafka().run()
    assert result.status == EnumHealthStatusValue.HEALTHY


def test_check_kafka_fail():
    with (
        patch.dict("os.environ", {"KAFKA_BOOTSTRAP_SERVERS": "testhost:19092"}),
        patch("socket.create_connection", side_effect=OSError("Connection refused")),
    ):
        result = CheckKafka().run()
    assert result.status == EnumHealthStatusValue.UNHEALTHY


def test_check_postgres_pass():
    with (
        patch.dict(
            "os.environ", {"POSTGRES_HOST": "testhost", "POSTGRES_PORT": "5432"}
        ),
        patch("socket.create_connection", return_value=MagicMock()),
    ):
        result = CheckPostgres().run()
    assert result.status == EnumHealthStatusValue.HEALTHY


def test_check_postgres_fail():
    with (
        patch.dict(
            "os.environ", {"POSTGRES_HOST": "testhost", "POSTGRES_PORT": "5432"}
        ),
        patch("socket.create_connection", side_effect=OSError("Connection refused")),
    ):
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


def test_no_localhost_fallbacks_in_doctor_checks():
    import re
    from pathlib import Path

    fallback_pattern = re.compile(
        r'os\.environ(?:\.get)?\([^)]*,\s*["\'].*localhost.*["\']'
    )
    checks_dir = (
        Path(__file__).parent.parent.parent
        / "src"
        / "omnibase_core"
        / "doctor"
        / "checks"
    )
    violations = []
    for py_file in sorted(checks_dir.glob("*.py")):
        for lineno, line in enumerate(py_file.read_text().splitlines(), start=1):
            if fallback_pattern.search(line) and not line.strip().startswith("#"):
                violations.append(f"{py_file.name}:{lineno}: {line.strip()}")
    assert violations == [], (
        "localhost fallbacks found in doctor checks:\n" + "\n".join(violations)
    )
