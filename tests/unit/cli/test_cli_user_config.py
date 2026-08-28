# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Tests for the unified ``~/.onex/config.yaml`` schema (OMN-16037).

Two commands write this file — ``onex config init`` (``cli_config.py``) and
``onex init --user-config`` (``cli_init.py``). Before OMN-16037 they emitted
incompatible shapes. These tests pin the single surviving schema, the
legacy-migration behaviour, and the ``onex health`` registration that the
onboarding flow points users at.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml
from click.testing import CliRunner

from omnibase_core.cli.cli_commands import cli
from omnibase_core.cli.cli_user_config import (
    USER_CONFIG_TEMPLATE,
    default_user_config,
    normalize_user_config,
    user_config_path,
)
from omnibase_core.errors.model_onex_error import ModelOnexError

MANAGED_SECTIONS = ("version", "mode", "credentials", "paths", "kafka", "logging")


def _load(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text())
    assert isinstance(data, dict), f"config did not parse to a mapping: {data!r}"
    return data


def _write_config(onex_home: Path, body: str) -> Path:
    onex_home.mkdir(parents=True, exist_ok=True)
    config_file = onex_home / "config.yaml"
    config_file.write_text(body)
    return config_file


@pytest.mark.unit
class TestUnifiedUserConfigSchema:
    """Both writers must produce one schema."""

    def test_config_init_writes_unified_schema(self, tmp_path: Path) -> None:
        onex_home = tmp_path / ".onex"
        runner = CliRunner()
        result = runner.invoke(cli, ["config", "init", "--onex-home", str(onex_home)])

        assert result.exit_code == 0, result.output
        data = _load(onex_home / "config.yaml")
        assert tuple(data) == MANAGED_SECTIONS
        assert data["version"] == 1
        assert data["mode"] == "local"

    def test_init_user_config_writes_unified_schema(self, tmp_path: Path) -> None:
        onex_home = tmp_path / ".onex"
        runner = CliRunner()
        result = runner.invoke(
            cli, ["init", "--user-config", "--onex-home", str(onex_home)]
        )

        assert result.exit_code == 0, result.output
        data = _load(onex_home / "config.yaml")
        assert tuple(data) == MANAGED_SECTIONS
        assert data["version"] == 1
        assert data["mode"] == "local"

    def test_both_writers_produce_identical_config(self, tmp_path: Path) -> None:
        """The core AC: same file, one shape, byte-for-byte agreement."""
        home_a = tmp_path / "a" / ".onex"
        home_b = tmp_path / "b" / ".onex"
        runner = CliRunner()

        assert (
            runner.invoke(cli, ["config", "init", "--onex-home", str(home_a)]).exit_code
            == 0
        )
        assert (
            runner.invoke(
                cli, ["init", "--user-config", "--onex-home", str(home_b)]
            ).exit_code
            == 0
        )

        assert (home_a / "config.yaml").read_text() == (
            home_b / "config.yaml"
        ).read_text()

    def test_template_matches_model_defaults(self) -> None:
        """Anti-drift ratchet: the commented template IS the model default."""
        assert yaml.safe_load(USER_CONFIG_TEMPLATE) == default_user_config()

    def test_user_config_path_defaults_under_home(self) -> None:
        assert user_config_path() == Path.home() / ".onex" / "config.yaml"


@pytest.mark.unit
class TestLegacyConfigMigration:
    """Legacy files in either shape must migrate, never corrupt."""

    LEGACY_STANDALONE = (
        "mode: standalone\n"
        "kafka:\n"
        "  bootstrap_servers: broker.internal:9092\n"
        "logging:\n"
        "  level: DEBUG\n"
    )
    LEGACY_USER = (
        "version: 1\n"
        "mode: local\n"
        "credentials:\n"
        '  LINEAR_API_KEY: "lin_api_secret"\n'  # pragma: allowlist secret
        '  INFISICAL_TOKEN: ""\n'
        "paths:\n"
        "  state_dir: ~/.onex/state\n"
        "  log_dir: ~/.onex/logs\n"
        "  worktrees_root: ~/omni_worktrees\n"
    )

    def test_legacy_standalone_mode_migrates_to_local(self) -> None:
        normalized, migrated = normalize_user_config(
            yaml.safe_load(self.LEGACY_STANDALONE)
        )
        assert migrated is True
        assert normalized["version"] == 1
        assert normalized["mode"] == "local"

    def test_legacy_standalone_preserves_operational_values(self) -> None:
        normalized, _ = normalize_user_config(yaml.safe_load(self.LEGACY_STANDALONE))
        assert normalized["kafka"]["bootstrap_servers"] == "broker.internal:9092"
        assert normalized["logging"]["level"] == "DEBUG"

    def test_legacy_standalone_gains_missing_sections(self) -> None:
        normalized, _ = normalize_user_config(yaml.safe_load(self.LEGACY_STANDALONE))
        assert normalized["credentials"]["LINEAR_API_KEY"] == ""
        assert normalized["paths"]["worktrees_root"] == "~/omni_worktrees"

    def test_legacy_user_shape_gains_missing_sections(self) -> None:
        normalized, migrated = normalize_user_config(yaml.safe_load(self.LEGACY_USER))
        assert migrated is True
        assert normalized["kafka"]["bootstrap_servers"] == "localhost:19092"
        assert normalized["logging"]["level"] == "INFO"

    def test_legacy_user_shape_preserves_credentials(self) -> None:
        normalized, _ = normalize_user_config(yaml.safe_load(self.LEGACY_USER))
        linear_key = "LINEAR" + "_API_KEY"
        assert (
            normalized["credentials"][linear_key] == "lin_api_secret"
        )  # pragma: allowlist secret

    def test_unknown_sections_are_preserved(self) -> None:
        """``aws:`` is written by ``onex refresh-credentials`` — must survive."""
        raw = yaml.safe_load(
            self.LEGACY_STANDALONE
            + "aws:\n  profile_name: local-profile\n  region: us-west-2\n"
        )
        normalized, _ = normalize_user_config(raw)
        assert normalized["aws"] == {
            "profile_name": "local-profile",
            "region": "us-west-2",
        }

    def test_unknown_keys_inside_managed_sections_are_preserved(self) -> None:
        raw = yaml.safe_load(self.LEGACY_USER)
        raw["credentials"]["GITHUB_TOKEN"] = "gh_tok"  # pragma: allowlist secret
        normalized, _ = normalize_user_config(raw)
        github_key = "GITHUB" + "_TOKEN"
        assert (
            normalized["credentials"][github_key] == "gh_tok"
        )  # pragma: allowlist secret

    def test_already_normalized_config_is_not_flagged_as_migrated(self) -> None:
        normalized, migrated = normalize_user_config(default_user_config())
        assert migrated is False
        assert normalized == default_user_config()

    def test_empty_config_normalizes_to_defaults(self) -> None:
        normalized, migrated = normalize_user_config(None)
        assert normalized == default_user_config()
        assert migrated is True

    def test_non_mapping_section_is_rejected_with_a_clear_message(self) -> None:
        with pytest.raises(ModelOnexError, match="kafka"):
            normalize_user_config({"version": 1, "mode": "local", "kafka": "nope"})

    def test_empty_section_header_fills_that_sections_defaults(self) -> None:
        """``logging:`` with no children parses to None — fill defaults, never refuse.

        A user who comments out every key under a section leaves a bare header.
        That is a valid file carrying no values, so it must migrate like any
        other legacy shape instead of aborting ``config init --force``,
        ``refresh-credentials`` and ``bootstrap apply``.
        """
        normalized, migrated = normalize_user_config(
            yaml.safe_load("version: 1\nmode: local\nlogging:\n")
        )
        assert normalized["logging"] == default_user_config()["logging"]
        assert migrated is True

    def test_unknown_mode_is_rejected(self) -> None:
        with pytest.raises(ModelOnexError, match="mode"):
            normalize_user_config({"version": 1, "mode": "interstellar"})


@pytest.mark.unit
class TestConfigInitForceMigrates:
    """``--force`` rewrites onto the current schema without destroying values."""

    def test_force_migrates_legacy_file_in_place(self, tmp_path: Path) -> None:
        onex_home = tmp_path / ".onex"
        _write_config(onex_home, TestLegacyConfigMigration.LEGACY_STANDALONE)

        runner = CliRunner()
        result = runner.invoke(
            cli, ["config", "init", "--force", "--onex-home", str(onex_home)]
        )

        assert result.exit_code == 0, result.output
        data = _load(onex_home / "config.yaml")
        assert data["version"] == 1
        assert data["mode"] == "local"
        assert data["kafka"]["bootstrap_servers"] == "broker.internal:9092"

    def test_force_preserves_user_credentials(self, tmp_path: Path) -> None:
        onex_home = tmp_path / ".onex"
        _write_config(onex_home, TestLegacyConfigMigration.LEGACY_USER)

        runner = CliRunner()
        result = runner.invoke(
            cli, ["config", "init", "--force", "--onex-home", str(onex_home)]
        )

        assert result.exit_code == 0, result.output
        data = _load(onex_home / "config.yaml")
        linear_key = "LINEAR" + "_API_KEY"
        assert (
            data["credentials"][linear_key] == "lin_api_secret"
        )  # pragma: allowlist secret

    def test_init_user_config_force_preserves_user_credentials(
        self, tmp_path: Path
    ) -> None:
        onex_home = tmp_path / ".onex"
        _write_config(onex_home, TestLegacyConfigMigration.LEGACY_USER)

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["init", "--user-config", "--force", "--onex-home", str(onex_home)],
        )

        assert result.exit_code == 0, result.output
        data = _load(onex_home / "config.yaml")
        linear_key = "LINEAR" + "_API_KEY"
        assert (
            data["credentials"][linear_key] == "lin_api_secret"
        )  # pragma: allowlist secret
        assert data["kafka"]["bootstrap_servers"] == "localhost:19092"

    def test_without_force_existing_file_is_untouched(self, tmp_path: Path) -> None:
        onex_home = tmp_path / ".onex"
        config_file = _write_config(
            onex_home, TestLegacyConfigMigration.LEGACY_STANDALONE
        )

        runner = CliRunner()
        result = runner.invoke(cli, ["config", "init", "--onex-home", str(onex_home)])

        assert result.exit_code != 0
        assert "already exists" in result.output
        assert config_file.read_text() == TestLegacyConfigMigration.LEGACY_STANDALONE


@pytest.mark.unit
class TestConfigGetAgainstUnifiedSchema:
    """``onex config get`` must read every managed section of the new shape."""

    @pytest.mark.parametrize(
        ("key", "expected"),
        [
            ("version", "1"),
            ("mode", "local"),
            ("kafka.bootstrap_servers", "localhost:19092"),
            ("paths.worktrees_root", "~/omni_worktrees"),
        ],
    )
    def test_get_reads_managed_keys(
        self, tmp_path: Path, key: str, expected: str
    ) -> None:
        onex_home = tmp_path / ".onex"
        runner = CliRunner()
        assert (
            runner.invoke(
                cli, ["config", "init", "--onex-home", str(onex_home)]
            ).exit_code
            == 0
        )

        result = runner.invoke(
            cli, ["config", "get", key, "--onex-home", str(onex_home)]
        )
        assert result.exit_code == 0, result.output
        assert result.output.strip() == expected


@pytest.mark.unit
class TestOnexHealthRegistration:
    """OMN-8796's DoD cites ``onex health``; it must actually resolve."""

    def test_health_command_is_registered(self) -> None:
        assert "health" in cli.commands

    def test_health_help_exits_clean(self) -> None:
        result = CliRunner().invoke(cli, ["health", "--help"])
        assert result.exit_code == 0, result.output

    def test_bootstrap_next_step_hint_is_an_invocable_command(
        self, tmp_path: Path
    ) -> None:
        """The onboarding hint printed by ``onex init --user-config`` must run.

        Regression: the hint used to read ``onex health --mode local``, but
        ``health`` has no ``--mode`` option, so the first command a new user was
        told to type failed with ``No such option: --mode``.
        """
        onex_home = tmp_path / ".onex"
        runner = CliRunner()
        result = runner.invoke(
            cli, ["init", "--user-config", "--onex-home", str(onex_home)]
        )
        assert result.exit_code == 0, result.output

        hints = [
            line.strip().removeprefix("Run:").strip()
            for line in result.output.splitlines()
            if line.strip().startswith("Run: onex ")
        ]
        assert hints, f"no 'Run: onex ...' hint printed:\n{result.output}"

        for hint in hints:
            args = hint.split()[1:]  # drop the leading "onex"
            probe = runner.invoke(cli, [*args, "--help"])
            assert probe.exit_code == 0, (
                f"hint {hint!r} is not invocable: {probe.output}"
            )
