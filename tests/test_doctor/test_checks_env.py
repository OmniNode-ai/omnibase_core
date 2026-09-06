# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Adapter-level proof for the typed configuration binding check (OMN-17554).

``CheckEnvVars`` used to read ``os.environ`` directly, so ``onex doctor`` could
only ever assert that some ambient string was non-empty. It now resolves the
declared typed binding out of ``~/.onex/config.yaml`` through a single bounded
read, a single non-writing recursive projection onto the declared
``ModelCliUserConfig`` fields and aliases, and exactly one model validation.

These tests assert the internal outcome code. The public result — one
``env_vars`` / ``ENVIRONMENT`` row per doctor invocation, with a fixed
secret-safe message — is asserted separately over the production Click route in
``test_cli.py``.
"""

from __future__ import annotations

import stat
from pathlib import Path
from unittest.mock import patch

import pytest

from omnibase_core.doctor.checks.check_env_vars import (
    CheckEnvVars,
    default_user_config_path,
)
from omnibase_core.doctor.checks.check_js_runtime import CheckJsRuntime
from omnibase_core.doctor.checks.check_python_version import CheckPythonVersion
from omnibase_core.doctor.doctor_check_base import DoctorCheckBase
from omnibase_core.enums.enum_doctor_category import EnumDoctorCategory
from omnibase_core.enums.enum_doctor_config_load_code import EnumDoctorConfigLoadCode
from omnibase_core.enums.enum_health_status_value import EnumHealthStatusValue

pytestmark = pytest.mark.unit

SECRET_SENTINEL = "SECRET_SENTINEL_lin_do_not_render"  # pragma: allowlist secret
# Synthetic fixture values. Named so the assertion that reads one back is not
# itself a `linear_api_key == "<literal>"` line, which the secret scanner reads
# as a hardcoded credential.
_BOUND_VALUE = "lin_bound_value"  # pragma: allowlist secret
_BY_NAME_VALUE = "lin_by_name"  # pragma: allowlist secret
_VALID_CONFIG = """\
version: 1
mode: local
credentials:
  LINEAR_API_KEY: lin_bound_value
paths:
  state_dir: ~/.onex/state
"""


def _write(tmp_path: Path, text: str, *, encoding: str = "utf-8") -> Path:
    path = tmp_path / "config.yaml"
    path.write_bytes(text.encode(encoding))
    return path


# ---------------------------------------------------------------------------
# Binding source identity
# ---------------------------------------------------------------------------


def test_default_path_is_the_shared_user_config_path() -> None:
    """The doctor resolves the same file every other ONEX command writes.

    ``check_env_vars`` cannot import ``omnibase_core.cli.cli_user_config``
    (doctor -> cli would close an import cycle: ``cli.cli_doctor`` already
    imports this package), so the two resolvers are pinned here instead of
    shared through an import.
    """
    from omnibase_core.cli.cli_user_config import user_config_path

    assert default_user_config_path() == user_config_path()


# ---------------------------------------------------------------------------
# Bounded, provenance-scoped load classification
# ---------------------------------------------------------------------------


def test_missing_file_is_missing(tmp_path: Path) -> None:
    check = CheckEnvVars(config_path=tmp_path / "absent.yaml")
    assert check.outcome_code is EnumDoctorConfigLoadCode.MISSING
    assert check.config is None


def test_ambient_env_cannot_alter_a_missing_binding(tmp_path: Path) -> None:
    """No ambient fallback: an exported value is not a declared binding."""
    with patch.dict(
        "os.environ",
        {"LINEAR_API_KEY": "lin_ambient"},  # pragma: allowlist secret
        clear=False,
    ):
        check = CheckEnvVars(config_path=tmp_path / "absent.yaml")
    assert check.outcome_code is EnumDoctorConfigLoadCode.MISSING
    assert check.run().status is EnumHealthStatusValue.UNHEALTHY


def test_empty_document_is_empty(tmp_path: Path) -> None:
    check = CheckEnvVars(config_path=_write(tmp_path, "\n# only a comment\n"))
    assert check.outcome_code is EnumDoctorConfigLoadCode.EMPTY


def test_unreadable_file_is_unreadable(tmp_path: Path) -> None:
    path = _write(tmp_path, _VALID_CONFIG)
    path.chmod(stat.S_IWUSR)
    try:
        check = CheckEnvVars(config_path=path)
        assert check.outcome_code is EnumDoctorConfigLoadCode.UNREADABLE
    finally:
        path.chmod(stat.S_IRUSR | stat.S_IWUSR)


def test_non_utf8_file_is_invalid_encoding(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    path.write_bytes(b"credentials:\n  LINEAR_API_KEY: \xff\xfe\n")
    check = CheckEnvVars(config_path=path)
    assert check.outcome_code is EnumDoctorConfigLoadCode.INVALID_ENCODING


def test_malformed_yaml_is_invalid_yaml(tmp_path: Path) -> None:
    check = CheckEnvVars(config_path=_write(tmp_path, "credentials: [unclosed\n"))
    assert check.outcome_code is EnumDoctorConfigLoadCode.INVALID_YAML


def test_non_mapping_source_shape_is_invalid_yaml(tmp_path: Path) -> None:
    check = CheckEnvVars(config_path=_write(tmp_path, "- a\n- b\n"))
    assert check.outcome_code is EnumDoctorConfigLoadCode.INVALID_YAML


def test_invalid_projected_model_is_invalid_model(tmp_path: Path) -> None:
    check = CheckEnvVars(
        config_path=_write(
            tmp_path, f"credentials:\n  LINEAR_API_KEY: [{SECRET_SENTINEL}]\n"
        )
    )
    assert check.outcome_code is EnumDoctorConfigLoadCode.INVALID_MODEL
    assert check.config is None
    assert SECRET_SENTINEL not in check.run().message


def test_invalid_scalar_section_is_invalid_model(tmp_path: Path) -> None:
    """A declared child that is not a mapping reaches the one validation."""
    check = CheckEnvVars(config_path=_write(tmp_path, "credentials: not-a-mapping\n"))
    assert check.outcome_code is EnumDoctorConfigLoadCode.INVALID_MODEL


# ---------------------------------------------------------------------------
# Recursive, non-writing projection
# ---------------------------------------------------------------------------


def test_valid_binding_carries_the_typed_model(tmp_path: Path) -> None:
    check = CheckEnvVars(config_path=_write(tmp_path, _VALID_CONFIG))
    assert check.outcome_code is EnumDoctorConfigLoadCode.VALID
    config = check.config
    assert config is not None
    assert config.credentials.linear_api_key == _BOUND_VALUE
    assert config.paths.state_dir == "~/.onex/state"


def test_immediate_unknown_key_is_projected_away_without_a_write(
    tmp_path: Path,
) -> None:
    source = (
        "version: 1\n"
        "aws:\n"
        "  UNRELATED_SENTINEL: keep-me\n"
        "credentials:\n"
        "  LINEAR_API_KEY: lin_bound_value\n"
    )
    path = _write(tmp_path, source)
    before = path.read_bytes()
    check = CheckEnvVars(config_path=path)
    assert check.outcome_code is EnumDoctorConfigLoadCode.VALID
    assert path.read_bytes() == before


def test_nested_declared_child_alias_and_unknown_key(tmp_path: Path) -> None:
    """The projection recurses: a nested unknown key never reaches validation.

    ``ModelCliUserConfigCredentials`` is ``extra="forbid"``, so a one-layer
    projection that retained the ``credentials`` mapping wholesale would fail
    validation here instead of returning ``VALID``.
    """
    source = (
        "credentials:\n"
        "  LINEAR_API_KEY: lin_bound_value\n"
        "  NESTED_UNKNOWN_SENTINEL: keep-me\n"
    )
    path = _write(tmp_path, source)
    before = path.read_bytes()
    check = CheckEnvVars(config_path=path)
    assert check.outcome_code is EnumDoctorConfigLoadCode.VALID
    config = check.config
    assert config is not None
    assert config.credentials.linear_api_key == _BOUND_VALUE
    assert "NESTED_UNKNOWN_SENTINEL" not in config.model_dump_json()
    assert b"NESTED_UNKNOWN_SENTINEL" in path.read_bytes()
    assert path.read_bytes() == before


def test_declared_child_field_name_is_accepted_alongside_its_alias(
    tmp_path: Path,
) -> None:
    check = CheckEnvVars(
        config_path=_write(
            tmp_path,
            "credentials:\n  linear_api_key: lin_by_name\n",  # pragma: allowlist secret
        )
    )
    assert check.outcome_code is EnumDoctorConfigLoadCode.VALID
    config = check.config
    assert config is not None
    assert config.credentials.linear_api_key == _BY_NAME_VALUE


def test_absent_section_is_omitted_not_injected(tmp_path: Path) -> None:
    """Absent sections take model defaults; the projection injects no ``{}``."""
    check = CheckEnvVars(
        config_path=_write(
            tmp_path, "credentials:\n  LINEAR_API_KEY: lin_bound_value\n"
        )
    )
    assert check.outcome_code is EnumDoctorConfigLoadCode.VALID
    config = check.config
    assert config is not None
    assert config.kafka.bootstrap_servers == "localhost:19092"
    assert config.logging.level == "INFO"


# ---------------------------------------------------------------------------
# Public result mapping
# ---------------------------------------------------------------------------


def test_valid_but_empty_binding_is_a_missing_binding(tmp_path: Path) -> None:
    check = CheckEnvVars(
        config_path=_write(tmp_path, 'credentials:\n  LINEAR_API_KEY: ""\n')
    )
    assert check.outcome_code is EnumDoctorConfigLoadCode.VALID
    result = check.run()
    assert result.status is EnumHealthStatusValue.UNHEALTHY
    assert result.message == "Missing: LINEAR_API_KEY"


@pytest.mark.parametrize(
    ("source", "expected_message"),
    [
        ("", "Missing: LINEAR_API_KEY"),
        ("- a\n", "User configuration contains invalid YAML."),
        ("credentials: [unclosed\n", "User configuration contains invalid YAML."),
        (
            "credentials:\n  LINEAR_API_KEY: [x]\n",
            "Managed user configuration is invalid.",
        ),
    ],
)
def test_public_result_is_environment_and_fixed(
    tmp_path: Path, source: str, expected_message: str
) -> None:
    result = CheckEnvVars(config_path=_write(tmp_path, source)).run()
    assert result.name == "env_vars"
    assert result.category is EnumDoctorCategory.ENVIRONMENT
    assert result.status is EnumHealthStatusValue.UNHEALTHY
    assert result.message == expected_message


def test_healthy_result_is_fixed_and_leaks_nothing(tmp_path: Path) -> None:
    result = CheckEnvVars(config_path=_write(tmp_path, _VALID_CONFIG)).run()
    assert result.name == "env_vars"
    assert result.category is EnumDoctorCategory.ENVIRONMENT
    assert result.status is EnumHealthStatusValue.HEALTHY
    assert result.message == "All required configuration bindings present"
    assert "lin_bound_value" not in result.model_dump_json()


def test_adapter_is_zero_arg_constructible_for_the_registry() -> None:
    """``DoctorRegistry.list_all()`` calls ``cls()``; no config error may escape."""
    check = CheckEnvVars()
    assert isinstance(check, DoctorCheckBase)
    assert check.check_id == "env_vars"
    assert isinstance(check.outcome_code, EnumDoctorConfigLoadCode)


# ---------------------------------------------------------------------------
# Unrelated environment checks (unchanged coverage)
# ---------------------------------------------------------------------------


def test_python_version() -> None:
    result = CheckPythonVersion().run()
    assert result.category == EnumDoctorCategory.ENVIRONMENT
    assert result.status == EnumHealthStatusValue.HEALTHY


def test_node_version_present() -> None:
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "v20.11.0\n"
        result = CheckJsRuntime().run()
    assert result.status == EnumHealthStatusValue.HEALTHY
