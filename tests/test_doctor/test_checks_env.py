# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from unittest.mock import patch

import pytest

from omnibase_core.doctor.checks.check_env_vars import CheckEnvVars

pytestmark = pytest.mark.unit
from omnibase_core.doctor.checks.check_node_version import CheckNodeVersion
from omnibase_core.doctor.checks.check_python_version import CheckPythonVersion
from omnibase_core.enums.enum_doctor_category import EnumDoctorCategory
from omnibase_core.enums.enum_health_status_value import EnumHealthStatusValue


def test_env_vars_all_set():
    env = {
        "LINEAR_API_KEY": "lin_abc",  # pragma: allowlist secret
        "OMNICLAUDE_PROJECT_ROOT": "/some/path",
    }
    with patch.dict("os.environ", env, clear=False):
        result = CheckEnvVars().run()
    assert result.category == EnumDoctorCategory.ENVIRONMENT


def test_env_vars_missing():
    with patch.dict("os.environ", {}, clear=True):
        result = CheckEnvVars().run()
    assert result.status in (
        EnumHealthStatusValue.DEGRADED,
        EnumHealthStatusValue.UNHEALTHY,
    )


def test_python_version():
    result = CheckPythonVersion().run()
    assert result.category == EnumDoctorCategory.ENVIRONMENT
    # We're running on 3.12+, so this should pass
    assert result.status == EnumHealthStatusValue.HEALTHY


def test_node_version_present():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "v20.11.0\n"
        result = CheckNodeVersion().run()
    assert result.status == EnumHealthStatusValue.HEALTHY
