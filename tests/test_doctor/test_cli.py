# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from unittest.mock import patch

import pytest
from click.testing import CliRunner

from omnibase_core.cli.cli_doctor import doctor

pytestmark = pytest.mark.unit
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


# ---------------------------------------------------------------------------
# Production Click route over the typed configuration binding (OMN-17554)
# ---------------------------------------------------------------------------
#
# These exercise the real `onex doctor` command end to end. The only thing
# substituted is the location of the user config file; the registry, the
# adapter, `run_all()` and both renderers are production code. Discovery is
# disabled and the built-in list is narrowed to the env-binding check so the
# result count is exactly one and every assertion is about this check.

import json
import logging
from pathlib import Path

from omnibase_core.doctor.checks.check_env_vars import CheckEnvVars
from omnibase_core.enums.enum_doctor_config_load_code import EnumDoctorConfigLoadCode

_PATH_SENTINEL = "PATH_SENTINEL_config_dir"
_SECRET_SENTINEL = "SECRET_SENTINEL_lin_do_not_render"  # pragma: allowlist secret
_PARSER_SENTINEL = "PARSER_SENTINEL_unclosed"

_BOUND_CONFIG = """\
version: 1
mode: local
credentials:
  LINEAR_API_KEY: lin_bound_value
"""


def _config_at(tmp_path: Path, text: str, *, raw: bytes | None = None) -> Path:
    directory = tmp_path / _PATH_SENTINEL
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "config.yaml"
    path.write_bytes(text.encode("utf-8") if raw is None else raw)
    return path


def _run_doctor(config_path: Path, args: list[str]):
    runner = CliRunner()
    with (
        patch("omnibase_core.cli.cli_doctor._BUILTIN_CHECKS", [CheckEnvVars]),
        patch(
            "omnibase_core.doctor.doctor_registry.DoctorRegistry.discover",
            lambda self: None,
        ),
        patch(
            "omnibase_core.doctor.checks.check_env_vars.default_user_config_path",
            lambda: config_path,
        ),
    ):
        return runner.invoke(doctor, args)


def _sole_check(result) -> dict[str, object]:
    payload = json.loads(result.output)
    assert payload["total"] == 1, payload
    checks = payload["checks"]
    assert len(checks) == 1, checks
    return dict(checks[0])


def _assert_absent(result, caplog, *sentinels: str) -> None:
    """Every sentinel is absent from every rendering surface."""
    surfaces = {
        "stdout": result.stdout,
        "stderr": result.stderr,
        "exception": "" if result.exception is None else repr(result.exception),
        "logs": caplog.text,
    }
    for name, text in surfaces.items():
        for sentinel in sentinels:
            assert sentinel not in text, f"{sentinel!r} leaked into {name}: {text!r}"


@pytest.mark.parametrize(
    ("body", "raw", "code", "message"),
    [
        (None, None, EnumDoctorConfigLoadCode.MISSING, "Missing: LINEAR_API_KEY"),
        ("\n", None, EnumDoctorConfigLoadCode.EMPTY, "Missing: LINEAR_API_KEY"),
        (
            f"credentials: [{_PARSER_SENTINEL}\n",
            None,
            EnumDoctorConfigLoadCode.INVALID_YAML,
            "User configuration contains invalid YAML.",
        ),
        (
            None,
            b"credentials:\n  LINEAR_API_KEY: \xff\xfe\n",
            EnumDoctorConfigLoadCode.INVALID_ENCODING,
            "User configuration has invalid text encoding.",
        ),
        (
            f"credentials:\n  LINEAR_API_KEY: [{_SECRET_SENTINEL}]\n",
            None,
            EnumDoctorConfigLoadCode.INVALID_MODEL,
            "Managed user configuration is invalid.",
        ),
    ],
)
def test_doctor_unhealthy_binding_rows(tmp_path, caplog, body, raw, code, message):
    if body is None and raw is None:
        config_path = tmp_path / _PATH_SENTINEL / "absent.yaml"
        config_path.parent.mkdir(parents=True, exist_ok=True)
    else:
        config_path = _config_at(tmp_path, body or "", raw=raw)

    assert CheckEnvVars(config_path=config_path).outcome_code is code

    with caplog.at_level(logging.DEBUG):
        human = _run_doctor(config_path, [])
        json_result = _run_doctor(config_path, ["--json"])

    assert human.exit_code == 1
    assert json_result.exit_code == 1
    assert "env_vars" in human.output
    assert message in human.output

    check = _sole_check(json_result)
    assert check["name"] == "env_vars"
    assert check["category"] == "environment"
    assert check["status"] == "unhealthy"
    assert check["message"] == message

    _assert_absent(
        human, caplog, _SECRET_SENTINEL, _PARSER_SENTINEL, _PATH_SENTINEL, "Traceback"
    )
    _assert_absent(
        json_result,
        caplog,
        _SECRET_SENTINEL,
        _PARSER_SENTINEL,
        _PATH_SENTINEL,
        "Traceback",
    )


def test_doctor_healthy_binding_row(tmp_path, caplog):
    config_path = _config_at(tmp_path, _BOUND_CONFIG)
    assert (
        CheckEnvVars(config_path=config_path).outcome_code
        is EnumDoctorConfigLoadCode.VALID
    )

    with caplog.at_level(logging.DEBUG):
        human = _run_doctor(config_path, [])
        json_result = _run_doctor(config_path, ["--json"])

    assert human.exit_code == 0
    assert json_result.exit_code == 0

    check = _sole_check(json_result)
    assert check["name"] == "env_vars"
    assert check["category"] == "environment"
    assert check["status"] == "healthy"
    assert check["message"] == "All required configuration bindings present"

    _assert_absent(human, caplog, "lin_bound_value", _PATH_SENTINEL)
    _assert_absent(json_result, caplog, "lin_bound_value", _PATH_SENTINEL)


def test_doctor_ambient_env_cannot_bind(tmp_path, caplog):
    """An exported LINEAR_API_KEY is not a declared binding and cannot pass."""
    config_path = tmp_path / _PATH_SENTINEL / "absent.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with patch.dict(
        "os.environ",
        {"LINEAR_API_KEY": "lin_ambient_sentinel"},  # pragma: allowlist secret
        clear=False,
    ):
        result = _run_doctor(config_path, ["--json"])
    assert result.exit_code == 1
    assert _sole_check(result)["message"] == "Missing: LINEAR_API_KEY"


def test_doctor_never_calls_a_preprojection_normalizer(tmp_path):
    """The doctor route must not reach `normalize_user_config` or any normalizer."""

    def _forbidden(*args, **kwargs):
        raise AssertionError("normalizer reached from the doctor boundary")

    config_path = _config_at(tmp_path, _BOUND_CONFIG)
    with (
        patch("omnibase_core.cli.cli_user_config.normalize_user_config", _forbidden),
        patch("omnibase_core.cli.cli_user_config.read_user_config", _forbidden),
        patch("omnibase_core.cli.cli_user_config.write_user_config", _forbidden),
        patch("omnibase_core.cli.cli_user_config.migrate_user_config_file", _forbidden),
    ):
        result = _run_doctor(config_path, ["--json"])
    assert result.exit_code == 0
    assert _sole_check(result)["status"] == "healthy"


def test_registry_list_all_returns_an_adapter_for_every_invalid_outcome(tmp_path):
    """`list_all()` yields one adapter without throwing; `run_all()` one result."""
    from omnibase_core.doctor.doctor_registry import DoctorRegistry

    cases = [
        tmp_path / "absent.yaml",
        _config_at(tmp_path, "\n"),
        _config_at(tmp_path, "credentials: [unclosed\n"),
        _config_at(tmp_path, "credentials:\n  LINEAR_API_KEY: [x]\n"),
    ]
    for config_path in cases:
        registry = DoctorRegistry()
        registry.register(CheckEnvVars)
        with patch(
            "omnibase_core.doctor.checks.check_env_vars.default_user_config_path",
            lambda bound=config_path: bound,
        ):
            checks = registry.list_all()
            assert len(checks) == 1
            assert isinstance(checks[0], CheckEnvVars)
            results = registry.run_all()
        assert len(results) == 1
        assert results[0].name == "env_vars"
        assert results[0].status is EnumHealthStatusValue.UNHEALTHY
