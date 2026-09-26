# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""``onex auth`` command surface, including the fail-closed path (OMN-15922).

The fail-closed tests assert a NON-ZERO EXIT plus a named remediation, not
merely that a warning was printed. A command that warns on stderr and exits 0
is indistinguishable, to every caller and every CI script, from a command that
succeeded -- which is the shape of the failure this whole slice exists to
prevent: a delegation that ran locally while the operator believed it reached
the cloud.
"""

from __future__ import annotations

import json
import stat
from pathlib import Path

import pytest
from click.testing import CliRunner

from omnibase_core.cli.cli_auth import auth_group

pytestmark = pytest.mark.unit

_SECRET = "s3cr3t-not-a-real-value"  # pragma: allowlist secret
_TOKEN_ENDPOINT = "https://keycloak.invalid/realms/acme/protocol/openid-connect/token"


@pytest.fixture
def onex_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point ``Path.home()`` at a scratch directory for the whole command."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    return home / ".onex"


def _login(runner: CliRunner) -> object:
    return runner.invoke(
        auth_group,
        [
            "login",
            "--tenant-slug",
            "acme",
            "--client-id",
            "ga-acme",
            "--token-endpoint",
            _TOKEN_ENDPOINT,
            "--base-url",
            "https://api.invalid",
            "--client-secret-stdin",
            "--edge-instance-id",
            "test-edge",
        ],
        input=f"{_SECRET}\n",
    )


def test_login_stores_by_reference_and_never_echoes_the_secret(onex_home: Path) -> None:
    runner = CliRunner()

    result = _login(runner)

    assert result.exit_code == 0
    assert _SECRET not in result.output
    assert _SECRET not in (onex_home / "config.yaml").read_text()
    credentials = onex_home / "credentials.json"
    assert json.loads(credentials.read_text())["acme-gateway"] == _SECRET
    assert stat.S_IMODE(credentials.stat().st_mode) == 0o600


def test_status_prints_identity_without_any_secret_material(onex_home: Path) -> None:
    runner = CliRunner()
    _login(runner)

    result = runner.invoke(auth_group, ["status"])

    assert result.exit_code == 0
    assert "acme" in result.output
    assert "ga-acme" in result.output
    assert _SECRET not in result.output


def test_status_without_a_credential_exits_non_zero_and_names_the_remediation(
    onex_home: Path,
) -> None:
    result = CliRunner().invoke(auth_group, ["status"])

    assert result.exit_code != 0
    assert "onex auth login" in result.output


def test_token_without_a_credential_fails_closed_before_touching_a_transport(
    onex_home: Path,
) -> None:
    """No credential is a hard stop -- there is no anonymous token to emit."""
    result = CliRunner().invoke(auth_group, ["token"])

    assert result.exit_code != 0
    assert "onex auth login" in result.output


def test_token_without_a_registered_transport_refuses_rather_than_degrading(
    onex_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """ADR-005: core ships no HTTP adapter, so absence must be loud.

    Asserting on the exit code AND on the refusal naming the entry-point group
    is what separates "fails closed" from "prints something and carries on".
    """
    runner = CliRunner()
    _login(runner)
    monkeypatch.setattr(
        "omnibase_core.cli.cli_auth.entry_points",
        lambda group: [],
    )

    result = runner.invoke(auth_group, ["token"])

    assert result.exit_code != 0
    assert "onex.gateway_transport" in result.output
    assert "unauthenticated" in result.output


def test_login_refuses_an_empty_secret_on_stdin(onex_home: Path) -> None:
    result = CliRunner().invoke(
        auth_group,
        [
            "login",
            "--tenant-slug",
            "acme",
            "--client-id",
            "ga-acme",
            "--token-endpoint",
            _TOKEN_ENDPOINT,
            "--base-url",
            "https://api.invalid",
            "--client-secret-stdin",
        ],
        input="\n",
    )

    assert result.exit_code != 0
    assert not (onex_home / "credentials.json").exists()


def test_the_secret_is_never_accepted_as_a_command_line_value(onex_home: Path) -> None:
    """A --client-secret <value> option must not exist at all.

    Its absence is the mechanism; a documented convention that operators should
    prefer stdin is not one. argv reaches the process table, the shell history
    file, and any exec audit log.
    """
    result = CliRunner().invoke(auth_group, ["login", "--help"])

    assert "--client-secret-stdin" in result.output
    assert "--client-secret " not in result.output


def test_logout_removes_the_credential_and_status_then_fails_closed(
    onex_home: Path,
) -> None:
    runner = CliRunner()
    _login(runner)

    logout = runner.invoke(auth_group, ["logout"])
    assert logout.exit_code == 0

    after = runner.invoke(auth_group, ["status"])
    assert after.exit_code != 0
