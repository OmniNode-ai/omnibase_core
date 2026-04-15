# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Tests for onex init --user-config (OMN-8790 Mode A local-only bootstrap)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from omnibase_core.cli.cli_commands import cli


@pytest.mark.unit
class TestOnexInitUserConfig:
    """Tests for `onex init --user-config`."""

    def test_onex_init_user_creates_config_file(self, tmp_path: Path) -> None:
        runner = CliRunner()
        config_file = tmp_path / ".onex" / "config.yaml"

        result = runner.invoke(
            cli,
            ["init", "--user-config", "--onex-home", str(tmp_path / ".onex")],
        )

        assert result.exit_code == 0, result.output
        assert config_file.exists()

        data = yaml.safe_load(config_file.read_text())
        assert data["version"] == 1
        assert data["mode"] == "local"
        assert "credentials" in data
        assert "paths" in data

    def test_onex_init_user_idempotent(self, tmp_path: Path) -> None:
        runner = CliRunner()
        onex_home = str(tmp_path / ".onex")

        result1 = runner.invoke(
            cli, ["init", "--user-config", "--onex-home", onex_home]
        )
        assert result1.exit_code == 0, result1.output

        # Write a sentinel value to verify file is NOT overwritten
        config_file = tmp_path / ".onex" / "config.yaml"
        original_content = config_file.read_text()
        config_file.write_text(original_content + "\n# sentinel\n")

        result2 = runner.invoke(
            cli, ["init", "--user-config", "--onex-home", onex_home]
        )
        assert result2.exit_code != 0
        assert "already exists" in result2.output or "already exists" in (
            result2.output + str(result2.exception)
        )
        assert "sentinel" in config_file.read_text()

    def test_onex_init_user_force_overwrites(self, tmp_path: Path) -> None:
        runner = CliRunner()
        onex_home = str(tmp_path / ".onex")

        first_result = runner.invoke(
            cli, ["init", "--user-config", "--onex-home", onex_home]
        )
        assert first_result.exit_code == 0, first_result.output
        config_file = tmp_path / ".onex" / "config.yaml"
        config_file.write_text("# sentinel\n")

        result = runner.invoke(
            cli, ["init", "--user-config", "--force", "--onex-home", onex_home]
        )
        assert result.exit_code == 0, result.output
        assert "sentinel" not in config_file.read_text()

    def test_onex_init_user_seeds_linear_placeholder(self, tmp_path: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["init", "--user-config", "--onex-home", str(tmp_path / ".onex")],
        )
        assert result.exit_code == 0, result.output

        config_file = tmp_path / ".onex" / "config.yaml"
        raw = config_file.read_text()
        data = yaml.safe_load(raw)

        # Placeholder key must exist (empty string is the canonical placeholder value)
        assert data["credentials"]["LINEAR_API_KEY"] == ""
        assert data["credentials"]["INFISICAL_TOKEN"] == ""
        # Comment pointing to where to fill it must be in raw text
        assert "linear.app" in raw

    def test_onex_init_user_creates_state_dir(self, tmp_path: Path) -> None:
        runner = CliRunner()
        onex_home = tmp_path / ".onex"
        result = runner.invoke(
            cli, ["init", "--user-config", "--onex-home", str(onex_home)]
        )
        assert result.exit_code == 0, result.output

        assert (onex_home / "state").is_dir()
        assert (onex_home / "logs").is_dir()
