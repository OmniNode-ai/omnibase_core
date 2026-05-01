# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Unit tests for cli_hooks.py — onex hooks {list,mask,enable,disable}."""

from __future__ import annotations

import os
from pathlib import Path
from unittest import mock

import pytest
from click.testing import CliRunner

from omnibase_core.cli.cli_hooks import hooks_group
from omnibase_core.enums.enum_hook_bit import _DEFAULT_MASK, EnumHookBit

pytestmark = pytest.mark.unit


def _env_file(tmp_path: Path) -> Path:
    return tmp_path / ".env"


def _write_env(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")


def _read_env(path: Path) -> str:
    return path.read_text()


def _mask_from_env(path: Path) -> int | None:
    if not path.exists():
        return None
    for line in path.read_text().splitlines():
        if line.startswith("ONEX_HOOKS_MASK="):
            return int(line.split("=", 1)[1], 0)
    return None


# ---------------------------------------------------------------------------
# list subcommand
# ---------------------------------------------------------------------------


class TestHooksList:
    def test_list_includes_every_member(self, tmp_path: Path) -> None:
        env_path = _env_file(tmp_path)
        runner = CliRunner()
        with mock.patch.dict(
            os.environ, {"OMNIBASE_ENV_FILE": str(env_path)}, clear=False
        ):
            result = runner.invoke(hooks_group, ["list"])
        assert result.exit_code == 0
        for m in EnumHookBit:
            assert m.name in result.output

    def test_list_shows_on_state_by_default(self, tmp_path: Path) -> None:
        env_path = _env_file(tmp_path)
        runner = CliRunner()
        with mock.patch.dict(
            os.environ, {"OMNIBASE_ENV_FILE": str(env_path)}, clear=False
        ):
            result = runner.invoke(hooks_group, ["list"])
        assert result.exit_code == 0
        assert "ON" in result.output

    def test_list_shows_off_for_disabled_bit(self, tmp_path: Path) -> None:
        env_path = _env_file(tmp_path)
        _write_env(env_path, ["ONEX_HOOKS_MASK=0x0"])
        runner = CliRunner()
        with mock.patch.dict(
            os.environ, {"OMNIBASE_ENV_FILE": str(env_path)}, clear=False
        ):
            result = runner.invoke(hooks_group, ["list"])
        assert result.exit_code == 0
        assert "OFF" in result.output


# ---------------------------------------------------------------------------
# mask subcommand
# ---------------------------------------------------------------------------


class TestHooksMask:
    def test_mask_prints_hex_default(self, tmp_path: Path) -> None:
        env_path = _env_file(tmp_path)
        runner = CliRunner()
        with mock.patch.dict(
            os.environ, {"OMNIBASE_ENV_FILE": str(env_path)}, clear=False
        ):
            result = runner.invoke(hooks_group, ["mask"])
        assert result.exit_code == 0
        assert f"0x{_DEFAULT_MASK:x}" in result.output

    def test_mask_prints_stored_hex(self, tmp_path: Path) -> None:
        env_path = _env_file(tmp_path)
        _write_env(env_path, ["ONEX_HOOKS_MASK=0xff"])
        runner = CliRunner()
        with mock.patch.dict(
            os.environ, {"OMNIBASE_ENV_FILE": str(env_path)}, clear=False
        ):
            result = runner.invoke(hooks_group, ["mask"])
        assert result.exit_code == 0
        assert "0xff" in result.output

    def test_mask_dec_format(self, tmp_path: Path) -> None:
        env_path = _env_file(tmp_path)
        runner = CliRunner()
        with mock.patch.dict(
            os.environ, {"OMNIBASE_ENV_FILE": str(env_path)}, clear=False
        ):
            result = runner.invoke(hooks_group, ["mask", "--format", "dec"])
        assert result.exit_code == 0
        assert str(_DEFAULT_MASK) in result.output

    def test_mask_bin_format(self, tmp_path: Path) -> None:
        env_path = _env_file(tmp_path)
        runner = CliRunner()
        with mock.patch.dict(
            os.environ, {"OMNIBASE_ENV_FILE": str(env_path)}, clear=False
        ):
            result = runner.invoke(hooks_group, ["mask", "--format", "bin"])
        assert result.exit_code == 0
        assert "0b" in result.output


# ---------------------------------------------------------------------------
# disable subcommand
# ---------------------------------------------------------------------------


class TestHooksDisable:
    def test_disable_clears_bit(self, tmp_path: Path) -> None:
        env_path = _env_file(tmp_path)
        runner = CliRunner()
        with mock.patch.dict(
            os.environ, {"OMNIBASE_ENV_FILE": str(env_path)}, clear=False
        ):
            result = runner.invoke(hooks_group, ["disable", "CI_REMINDER"])
        assert result.exit_code == 0
        mask = _mask_from_env(env_path)
        assert mask is not None
        assert not (mask & int(EnumHookBit.CI_REMINDER))

    def test_disable_prints_summary(self, tmp_path: Path) -> None:
        env_path = _env_file(tmp_path)
        runner = CliRunner()
        with mock.patch.dict(
            os.environ, {"OMNIBASE_ENV_FILE": str(env_path)}, clear=False
        ):
            result = runner.invoke(hooks_group, ["disable", "CI_REMINDER"])
        assert "CI_REMINDER" in result.output
        assert "disabled" in result.output

    def test_disable_preserves_adjacent_lines(self, tmp_path: Path) -> None:
        env_path = _env_file(tmp_path)
        _write_env(
            env_path,
            [
                "SOME_VAR=hello",
                "ONEX_HOOKS_MASK=0xff",
                "# a comment",
                "OTHER_VAR=world",
            ],
        )
        runner = CliRunner()
        with mock.patch.dict(
            os.environ, {"OMNIBASE_ENV_FILE": str(env_path)}, clear=False
        ):
            result = runner.invoke(hooks_group, ["disable", "CI_REMINDER"])
        assert result.exit_code == 0
        content = _read_env(env_path)
        assert "SOME_VAR=hello" in content
        assert "# a comment" in content
        assert "OTHER_VAR=world" in content

    def test_disable_unknown_name_exits_with_error(self, tmp_path: Path) -> None:
        env_path = _env_file(tmp_path)
        runner = CliRunner()
        with mock.patch.dict(
            os.environ, {"OMNIBASE_ENV_FILE": str(env_path)}, clear=False
        ):
            result = runner.invoke(hooks_group, ["disable", "NONEXISTENT_HOOK"])
        assert result.exit_code == 2
        assert "Unknown hook" in result.output

    def test_disable_case_insensitive(self, tmp_path: Path) -> None:
        env_path = _env_file(tmp_path)
        runner = CliRunner()
        with mock.patch.dict(
            os.environ, {"OMNIBASE_ENV_FILE": str(env_path)}, clear=False
        ):
            result = runner.invoke(hooks_group, ["disable", "ci_reminder"])
        assert result.exit_code == 0
        mask = _mask_from_env(env_path)
        assert mask is not None
        assert not (mask & int(EnumHookBit.CI_REMINDER))


# ---------------------------------------------------------------------------
# enable subcommand
# ---------------------------------------------------------------------------


class TestHooksEnable:
    def test_enable_sets_bit(self, tmp_path: Path) -> None:
        env_path = _env_file(tmp_path)
        runner = CliRunner()
        with mock.patch.dict(
            os.environ, {"OMNIBASE_ENV_FILE": str(env_path)}, clear=False
        ):
            runner.invoke(hooks_group, ["disable", "CI_REMINDER"])
            result = runner.invoke(hooks_group, ["enable", "CI_REMINDER"])
        assert result.exit_code == 0
        mask = _mask_from_env(env_path)
        assert mask is not None
        assert mask & int(EnumHookBit.CI_REMINDER)

    def test_enable_prints_summary(self, tmp_path: Path) -> None:
        env_path = _env_file(tmp_path)
        runner = CliRunner()
        with mock.patch.dict(
            os.environ, {"OMNIBASE_ENV_FILE": str(env_path)}, clear=False
        ):
            runner.invoke(hooks_group, ["disable", "CI_REMINDER"])
            result = runner.invoke(hooks_group, ["enable", "CI_REMINDER"])
        assert "CI_REMINDER" in result.output
        assert "enabled" in result.output

    def test_enable_unknown_name_exits_with_error(self, tmp_path: Path) -> None:
        env_path = _env_file(tmp_path)
        runner = CliRunner()
        with mock.patch.dict(
            os.environ, {"OMNIBASE_ENV_FILE": str(env_path)}, clear=False
        ):
            result = runner.invoke(hooks_group, ["enable", "GARBAGE"])
        assert result.exit_code == 2
        assert "Unknown hook" in result.output

    def test_enable_preserves_adjacent_lines(self, tmp_path: Path) -> None:
        env_path = _env_file(tmp_path)
        _write_env(
            env_path,
            [
                "SOME_VAR=hello",
                "ONEX_HOOKS_MASK=0x0",
                "# a comment",
            ],
        )
        runner = CliRunner()
        with mock.patch.dict(
            os.environ, {"OMNIBASE_ENV_FILE": str(env_path)}, clear=False
        ):
            result = runner.invoke(hooks_group, ["enable", "CI_REMINDER"])
        assert result.exit_code == 0
        content = _read_env(env_path)
        assert "SOME_VAR=hello" in content
        assert "# a comment" in content


# ---------------------------------------------------------------------------
# nearest-match hint
# ---------------------------------------------------------------------------


class TestNearestMatch:
    def test_suggests_similar_name(self, tmp_path: Path) -> None:
        env_path = _env_file(tmp_path)
        runner = CliRunner()
        with mock.patch.dict(
            os.environ, {"OMNIBASE_ENV_FILE": str(env_path)}, clear=False
        ):
            result = runner.invoke(hooks_group, ["disable", "CI_REMINDE"])
        assert result.exit_code == 2
        assert "CI_REMINDER" in result.output

    def test_no_hint_for_completely_wrong_name(self, tmp_path: Path) -> None:
        env_path = _env_file(tmp_path)
        runner = CliRunner()
        with mock.patch.dict(
            os.environ, {"OMNIBASE_ENV_FILE": str(env_path)}, clear=False
        ):
            result = runner.invoke(hooks_group, ["disable", "ZZZZZZZZZ"])
        assert result.exit_code == 2
        assert "Unknown hook" in result.output


# ---------------------------------------------------------------------------
# env file creation
# ---------------------------------------------------------------------------


class TestEnvFileCreation:
    def test_creates_env_if_missing(self, tmp_path: Path) -> None:
        env_path = tmp_path / "subdir" / ".env"
        runner = CliRunner()
        with mock.patch.dict(
            os.environ, {"OMNIBASE_ENV_FILE": str(env_path)}, clear=False
        ):
            result = runner.invoke(hooks_group, ["disable", "CI_REMINDER"])
        assert result.exit_code == 0
        assert env_path.exists()
        mask = _mask_from_env(env_path)
        assert mask is not None
