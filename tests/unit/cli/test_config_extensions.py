# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Config extensions must not replace core commands or hide broken plugins.

Failure controls cover a new package's missing command, duplicate metadata,
builtin takeover, import failure, and a non-Click target. Existing config stays
usable without loading an unrelated extension's implementation.
"""

from __future__ import annotations

import importlib
import importlib.metadata
from collections.abc import Iterator
from contextlib import contextmanager
from importlib.metadata import EntryPoint
from types import ModuleType
from unittest.mock import patch

import click
import pytest
from click.testing import CliRunner

from omnibase_core.cli import cli_config
from omnibase_core.errors.model_onex_error import ModelOnexError

pytestmark = pytest.mark.unit


@click.command()
def future_config() -> None:
    """A command supplied by an independently installed capability package."""
    click.echo("external configuration command")


@contextmanager
def _configured(points: list[EntryPoint]) -> Iterator[ModuleType]:
    original = importlib.metadata.entry_points

    def discover(**kwargs: str) -> object:
        if kwargs.get("group") == "onex.config":
            return points
        return original(**kwargs)

    try:
        with patch.object(importlib.metadata, "entry_points", discover):
            yield importlib.reload(cli_config)
    finally:
        importlib.reload(cli_config)


def _point(name: str, target: str = "future_config") -> EntryPoint:
    return EntryPoint(name=name, value=f"{__name__}:{target}", group="onex.config")


def test_unknown_config_command_loads_from_installed_metadata() -> None:
    with _configured([_point("future")]) as module:
        result = CliRunner().invoke(module.config_group, ["future"])
        assert result.exit_code == 0, result.output
        assert result.output == "external configuration command\n"
        assert {"get", "init", "future"} <= set(
            module.config_group.list_commands(click.Context(module.config_group))
        )


@pytest.mark.parametrize("names", [("get",), ("init",), ("future", "future")])
def test_duplicate_config_command_is_refused_before_any_load(
    names: tuple[str, ...],
) -> None:
    with pytest.raises(ModelOnexError, match="collides"):
        with _configured([_point(name, "nonexistent") for name in names]):
            pytest.fail("A colliding config registry was accepted")


@pytest.mark.parametrize("target", ["nonexistent", "pytestmark"])
def test_broken_config_target_fails_only_when_resolved(target: str) -> None:
    with _configured([_point("future", target)]) as module:
        runner = CliRunner()
        assert runner.invoke(module.config_group, ["get", "--help"]).exit_code == 0
        result = runner.invoke(module.config_group, ["future"])
        assert result.exit_code != 0
        assert isinstance(result.exception, ModelOnexError)
        assert "onex.config" in str(result.exception)


def test_no_extensions_preserves_builtin_commands() -> None:
    with _configured([]) as module:
        assert module.config_group.list_commands(
            click.Context(module.config_group)
        ) == ["get", "init"]
