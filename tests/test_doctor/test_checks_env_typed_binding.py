# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""OMN-17554 — the doctor proves a real typed binding, not its own injected set.

Before this suite, ``CheckEnvVars`` read ``os.environ`` for a hardcoded name
list, so ``onex doctor`` reported on ambient process state that no ONEX surface
owns. The regression these tests exist to stop is the *vacuous* one: a doctor
that asserts the health of a set it supplied itself, and reports "healthy" while
the real binding is absent.

Every case here drives the production route — the real ``CheckEnvVars``, the
real ``DoctorRegistry`` factory, and (for the CLI cases) the real Click command,
report renderer and exit code. The only thing redirected is the user's home, so
a test never reads or writes the developer's own ``~/.onex/config.yaml``.
"""

from __future__ import annotations

import json
import traceback
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from omnibase_core.cli.cli_doctor import doctor
from omnibase_core.doctor.checks.check_env_vars import (
    DISPLAY_CONFIG_PATH,
    CheckEnvVars,
)
from omnibase_core.doctor.doctor_registry import DoctorRegistry
from omnibase_core.enums.enum_doctor_category import EnumDoctorCategory
from omnibase_core.enums.enum_health_status_value import EnumHealthStatusValue
from omnibase_core.models.doctor.model_doctor_check_result import ModelDoctorCheckResult

pytestmark = pytest.mark.unit

# A value shaped like a real Linear key so a leak is unambiguous in any channel.
SECRET = "lin_api_omn17554_must_never_be_printed"  # pragma: allowlist secret


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _run(path: Path) -> ModelDoctorCheckResult:
    return CheckEnvVars(path).run()


# ---------------------------------------------------------------------------
# Construction: the check must never fail to construct, whatever the path holds.
# DoctorRegistry.list_all() builds every check before any of them runs, so a
# constructor that touches the filesystem takes the whole report down.
# ---------------------------------------------------------------------------


def test_construction_never_touches_the_filesystem(tmp_path: Path) -> None:
    for candidate in (
        tmp_path / "absent.yaml",
        _write(tmp_path / "broken.yaml", "{{{"),
        tmp_path,  # a directory where a file is expected
    ):
        assert isinstance(CheckEnvVars(candidate), CheckEnvVars)


# ---------------------------------------------------------------------------
# Unhealthy outcomes. Each is a distinct, fixed, secret-safe message and every
# one carries the ENVIRONMENT category.
# ---------------------------------------------------------------------------


def test_absent_config_is_unhealthy(tmp_path: Path) -> None:
    result = _run(tmp_path / "config.yaml")
    assert result.status == EnumHealthStatusValue.UNHEALTHY
    assert result.category == EnumDoctorCategory.ENVIRONMENT
    assert DISPLAY_CONFIG_PATH in result.message


def test_empty_config_is_unhealthy(tmp_path: Path) -> None:
    result = _run(_write(tmp_path / "config.yaml", ""))
    assert result.status == EnumHealthStatusValue.UNHEALTHY
    assert result.category == EnumDoctorCategory.ENVIRONMENT


def test_unreadable_config_is_unhealthy(tmp_path: Path) -> None:
    """A directory where the config should be raises OSError, not a crash."""
    directory = tmp_path / "config.yaml"
    directory.mkdir()
    result = _run(directory)
    assert result.status == EnumHealthStatusValue.UNHEALTHY
    assert result.category == EnumDoctorCategory.ENVIRONMENT


def test_non_utf8_config_is_unhealthy(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    path.write_bytes(b"credentials:\n  LINEAR_API_KEY: \xff\xfe\n")
    result = _run(path)
    assert result.status == EnumHealthStatusValue.UNHEALTHY
    assert result.category == EnumDoctorCategory.ENVIRONMENT


def test_invalid_yaml_is_unhealthy_and_leaks_no_parser_text(tmp_path: Path) -> None:
    path = _write(tmp_path / "config.yaml", f"credentials: [{SECRET}\n")
    result = _run(path)
    assert result.status == EnumHealthStatusValue.UNHEALTHY
    assert SECRET not in result.message
    # A yaml parser error quotes the offending line and its position; neither
    # may reach the operator-facing message.
    assert "line" not in result.message.lower()


def test_non_mapping_document_is_unhealthy(tmp_path: Path) -> None:
    result = _run(_write(tmp_path / "config.yaml", "- just\n- a list\n"))
    assert result.status == EnumHealthStatusValue.UNHEALTHY
    assert result.category == EnumDoctorCategory.ENVIRONMENT


def test_invalid_model_is_unhealthy_and_leaks_no_value(tmp_path: Path) -> None:
    """A managed section whose shape is wrong classifies, it does not escape.

    The prior implementation let the Pydantic ValidationError propagate out of
    the CLI with the raw invalid value in its text.
    """
    path = _write(
        tmp_path / "config.yaml",
        f"version: 1\ncredentials:\n  LINEAR_API_KEY:\n    - {SECRET}\n",
    )
    result = _run(path)
    assert result.status == EnumHealthStatusValue.UNHEALTHY
    assert result.category == EnumDoctorCategory.ENVIRONMENT
    assert SECRET not in result.message


def test_invalid_mode_is_unhealthy(tmp_path: Path) -> None:
    result = _run(
        _write(tmp_path / "config.yaml", "version: 1\nmode: interplanetary\n")
    )
    assert result.status == EnumHealthStatusValue.UNHEALTHY
    assert "interplanetary" not in result.message


def test_blank_binding_is_unhealthy(tmp_path: Path) -> None:
    """The template ships ``LINEAR_API_KEY: ""`` — present but unbound."""
    path = _write(
        tmp_path / "config.yaml",
        'version: 1\nmode: local\ncredentials:\n  LINEAR_API_KEY: ""\n',
    )
    result = _run(path)
    assert result.status == EnumHealthStatusValue.UNHEALTHY
    assert "LINEAR_API_KEY" in result.message


def test_whitespace_only_binding_is_unhealthy(tmp_path: Path) -> None:
    path = _write(
        tmp_path / "config.yaml",
        'version: 1\ncredentials:\n  LINEAR_API_KEY: "   "\n',
    )
    assert _run(path).status == EnumHealthStatusValue.UNHEALTHY


# ---------------------------------------------------------------------------
# The healthy outcome, and the specific vacuity this ticket exists to kill.
# ---------------------------------------------------------------------------


def test_bound_binding_is_healthy_and_never_echoes_the_value(tmp_path: Path) -> None:
    path = _write(
        tmp_path / "config.yaml",
        f"version: 1\nmode: local\ncredentials:\n  LINEAR_API_KEY: {SECRET}\n",
    )
    result = _run(path)
    assert result.status == EnumHealthStatusValue.HEALTHY
    assert result.category == EnumDoctorCategory.ENVIRONMENT
    assert SECRET not in result.message


def test_ambient_environment_alone_is_not_a_binding(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The regression guard: process env is not an authority for this check.

    Exporting ``LINEAR_API_KEY`` in the shell must not make the doctor report
    healthy — the binding lives in the typed user config or it does not exist.
    """
    monkeypatch.setenv("LINEAR_API_KEY", SECRET)
    monkeypatch.setenv("OMNICLAUDE_PROJECT_ROOT", str(tmp_path))
    result = _run(tmp_path / "config.yaml")
    assert result.status == EnumHealthStatusValue.UNHEALTHY


# ---------------------------------------------------------------------------
# Projection: recursive, by declared field *and* alias, absent sections omitted,
# unknown keys dropped at every depth, and the source file never rewritten.
# ---------------------------------------------------------------------------


def test_field_name_and_alias_both_bind(tmp_path: Path) -> None:
    by_alias = _write(
        tmp_path / "alias" / "config.yaml",
        f"credentials:\n  LINEAR_API_KEY: {SECRET}\n",
    )
    by_name = _write(
        tmp_path / "name" / "config.yaml",
        f"credentials:\n  linear_api_key: {SECRET}\n",
    )
    assert _run(by_alias).status == EnumHealthStatusValue.HEALTHY
    assert _run(by_name).status == EnumHealthStatusValue.HEALTHY


def test_unknown_keys_are_dropped_at_every_depth(tmp_path: Path) -> None:
    """The managed models are ``extra="forbid"``.

    A one-layer projection passes a declared section through wholesale, so an
    unknown key *nested inside* ``credentials:`` reaches strict validation and
    fails the whole file. Real user configs carry exactly this: an ``aws:``
    block written by ``onex refresh-credentials`` and hand-added credential
    keys. Neither may make the doctor report the config invalid.
    """
    path = _write(
        tmp_path / "config.yaml",
        "version: 1\n"
        "aws:\n"
        "  region: us-east-1\n"
        "credentials:\n"
        f"  LINEAR_API_KEY: {SECRET}\n"
        "  HAND_ADDED_KEY: whatever\n"
        "paths:\n"
        "  state_dir: ~/.onex/state\n"
        "  hand_added_path: /somewhere\n",
    )
    assert _run(path).status == EnumHealthStatusValue.HEALTHY


def test_absent_sections_are_omitted_not_injected(tmp_path: Path) -> None:
    """Only ``credentials`` is present; every other section takes its default."""
    path = _write(
        tmp_path / "config.yaml", f"credentials:\n  LINEAR_API_KEY: {SECRET}\n"
    )
    assert _run(path).status == EnumHealthStatusValue.HEALTHY


def test_null_section_header_is_tolerated(tmp_path: Path) -> None:
    """``logging:`` with no children parses to ``None`` — it carries no values."""
    path = _write(
        tmp_path / "config.yaml",
        f"credentials:\n  LINEAR_API_KEY: {SECRET}\nlogging:\n",
    )
    assert _run(path).status == EnumHealthStatusValue.HEALTHY


def test_run_never_writes_the_config_file(tmp_path: Path) -> None:
    """The doctor diagnoses. It must not migrate, normalize or rewrite."""
    text = "version: 1\naws:\n  region: us-east-1\ncredentials: {}\n"
    path = _write(tmp_path / "config.yaml", text)
    before_bytes = path.read_bytes()
    before_mtime = path.stat().st_mtime_ns

    _run(path)

    assert path.read_bytes() == before_bytes
    assert path.stat().st_mtime_ns == before_mtime
    assert sorted(p.name for p in tmp_path.iterdir()) == ["config.yaml"]


# ---------------------------------------------------------------------------
# Registry: the check is constructed through a declared factory, and a crashing
# check is reported without echoing its exception text.
# ---------------------------------------------------------------------------


def test_registry_builds_the_check_through_its_declared_factory(
    tmp_path: Path,
) -> None:
    registry = DoctorRegistry()
    registry.register(CheckEnvVars, factory=lambda: CheckEnvVars(tmp_path / "c.yaml"))
    checks = registry.list_all()
    assert len(checks) == 1
    assert isinstance(checks[0], CheckEnvVars)
    assert registry.run_all()[0].status == EnumHealthStatusValue.UNHEALTHY


def test_registry_crash_message_omits_exception_text() -> None:
    from omnibase_core.doctor.doctor_check_base import DoctorCheckBase

    class Exploding(DoctorCheckBase):
        check_id = "exploding"
        check_name = "Exploding"
        category = EnumDoctorCategory.ENVIRONMENT

        def run(self) -> ModelDoctorCheckResult:
            raise ValueError(SECRET)  # error-ok: deliberate crash fixture

    registry = DoctorRegistry()
    registry.register(Exploding)
    result = registry.run_all()[0]
    assert result.status == EnumHealthStatusValue.UNHEALTHY
    assert SECRET not in result.message


# ---------------------------------------------------------------------------
# Production CLI route: real command, real registry, real renderer, real exit
# code — human and JSON, with redaction asserted on every output channel.
# ---------------------------------------------------------------------------


def _invoke_doctor(config_path: Path, args: list[str]) -> object:
    runner = CliRunner()
    with (
        patch("omnibase_core.cli.cli_doctor._BUILTIN_CHECKS", []),
        patch(
            "omnibase_core.cli.cli_doctor.user_config_path", return_value=config_path
        ),
        patch.object(DoctorRegistry, "discover", lambda self: None),
    ):
        return runner.invoke(doctor, args, catch_exceptions=True)


@pytest.mark.parametrize("args", [[], ["--json"]])
def test_cli_reports_missing_binding_as_a_failure(
    tmp_path: Path, args: list[str]
) -> None:
    result = _invoke_doctor(tmp_path / "config.yaml", args)
    assert result.exception is None or isinstance(result.exception, SystemExit)
    assert result.exit_code == 1
    if args:
        payload = json.loads(result.output)
        assert payload["failed"] == 1
        assert payload["checks"][0]["category"] == "environment"


def test_cli_reports_a_real_binding_as_healthy(tmp_path: Path) -> None:
    path = _write(
        tmp_path / "config.yaml",
        f"version: 1\nmode: local\ncredentials:\n  LINEAR_API_KEY: {SECRET}\n",
    )
    result = _invoke_doctor(path, ["--json"])
    payload = json.loads(result.output)
    assert result.exit_code == 0
    assert payload["passed"] == 1
    assert payload["failed"] == 0


@pytest.mark.parametrize("args", [[], ["--json"]])
def test_cli_never_leaks_the_secret_on_any_channel(
    tmp_path: Path, args: list[str]
) -> None:
    """stdout, stderr, the raised exception and its traceback are all checked.

    The second rejected attempt exited 1 with the raw invalid credential inside
    the Click exception text; asserting only on stdout would have passed it.
    """
    path = _write(
        tmp_path / "config.yaml",
        f"version: 1\ncredentials:\n  LINEAR_API_KEY:\n    - {SECRET}\n",
    )
    result = _invoke_doctor(path, args)

    assert SECRET not in result.output
    assert SECRET not in repr(result.exception)
    if result.exc_info is not None:
        assert SECRET not in "".join(
            traceback.format_exception(*result.exc_info)  # type: ignore[arg-type]
        )
    assert result.exit_code == 1


def test_cli_classifies_rather_than_crashing_on_a_malformed_file(
    tmp_path: Path,
) -> None:
    """Exit 1 from a *classified* unhealthy result, never from an uncaught error."""
    path = _write(tmp_path / "config.yaml", "credentials: [unclosed\n")
    result = _invoke_doctor(path, ["--json"])
    payload = json.loads(result.output)
    assert result.exit_code == 1
    assert payload["total"] == 1
    assert payload["checks"][0]["status"] == "unhealthy"
