# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""`onex` with no arguments opens the terminal UI, but only in a terminal (OMN-23413 AC16).

Failure modes:
  F1. A pipe, CI job or script that runs `onex` alone gets a full-screen app
      instead of the help text it got before.
  F2. In a terminal with a package that registers `tui`, `onex` alone still
      prints help.
  F3. In a terminal with no `tui` registered, `onex` alone errors instead of
      printing help.
"""

from __future__ import annotations

import click
import pytest
from click.testing import CliRunner

from omnibase_core.cli import cli_commands
from omnibase_core.cli.cli_commands import cli

pytestmark = pytest.mark.unit


def test_bare_onex_without_a_terminal_prints_the_same_help() -> None:
    """F1: CliRunner has no terminal, like a pipe or CI."""
    bare = CliRunner().invoke(cli, [])
    helped = CliRunner().invoke(cli, ["--help"])
    assert bare.exit_code == 0
    assert bare.output == helped.output


def test_bare_onex_in_a_terminal_opens_the_registered_tui(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """F2."""
    opened: list[bool] = []

    @click.command("tui")
    def fake_tui() -> None:
        opened.append(True)

    original = cli.get_command
    monkeypatch.setattr(cli_commands, "_interactive_terminal", lambda: True)
    monkeypatch.setattr(
        cli,
        "get_command",
        lambda ctx, name: fake_tui if name == "tui" else original(ctx, name),
    )
    result = CliRunner().invoke(cli, [])
    assert result.exit_code == 0
    assert opened == [True]
    assert "Usage:" not in result.output


def test_bare_onex_in_a_terminal_without_a_tui_prints_help(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """F3."""
    original = cli.get_command
    monkeypatch.setattr(cli_commands, "_interactive_terminal", lambda: True)
    monkeypatch.setattr(
        cli,
        "get_command",
        lambda ctx, name: None if name == "tui" else original(ctx, name),
    )
    result = CliRunner().invoke(cli, [])
    assert result.exit_code == 0
    assert "Usage:" in result.output
