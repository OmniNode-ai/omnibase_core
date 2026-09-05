# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

import inspect
import typing
from pathlib import Path
from unittest.mock import patch

import pytest

from omnibase_core.doctor.checks.check_env_vars import CheckEnvVars

pytestmark = pytest.mark.unit
from omnibase_core.doctor.checks.check_js_runtime import CheckJsRuntime
from omnibase_core.doctor.checks.check_python_version import CheckPythonVersion
from omnibase_core.enums.enum_doctor_category import EnumDoctorCategory
from omnibase_core.enums.enum_health_status_value import EnumHealthStatusValue


def test_env_vars_requires_an_explicit_config_authority():
    """OMN-17554: the check cannot be built without being told what to read.

    A zero-argument constructor is what let this check fall back to ambient
    ``os.environ``. Removing that constructor is the structural half of the fix;
    the behavioural half is covered in ``test_checks_env_typed_binding.py``.
    """
    with pytest.raises(TypeError):
        CheckEnvVars()  # type: ignore[call-arg]

    signature = inspect.signature(CheckEnvVars.__init__)
    assert list(signature.parameters) == ["self", "config_path"]
    assert typing.get_type_hints(CheckEnvVars.__init__)["config_path"] is Path


def test_env_vars_reports_environment_category(tmp_path: Path):
    result = CheckEnvVars(tmp_path / "config.yaml").run()
    assert result.category == EnumDoctorCategory.ENVIRONMENT
    assert result.status == EnumHealthStatusValue.UNHEALTHY


def test_python_version():
    result = CheckPythonVersion().run()
    assert result.category == EnumDoctorCategory.ENVIRONMENT
    # We're running on 3.12+, so this should pass
    assert result.status == EnumHealthStatusValue.HEALTHY


def test_node_version_present():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "v20.11.0\n"
        result = CheckJsRuntime().run()
    assert result.status == EnumHealthStatusValue.HEALTHY
