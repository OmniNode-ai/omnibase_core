# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Tests for the ``onex validate-shape`` CLI command group.

Tests cover:
- check subcommand: allowed shapes, forbidden shapes, invalid inputs
- list subcommand: displays all canonical shapes
- matrix subcommand: displays compatibility matrix
- Helper resolution functions
"""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from omnibase_core.cli.cli_commands import cli
from omnibase_core.cli.cli_validate_shape import (
    VALID_SOURCES,
    VALID_TARGETS,
    _resolve_source,
    _resolve_target,
)
from omnibase_core.enums.enum_execution_shape import EnumMessageCategory
from omnibase_core.enums.enum_node_kind import EnumNodeKind

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


class TestResolveSource:
    """Tests for _resolve_source helper."""

    def test_resolves_valid_categories(self) -> None:
        assert _resolve_source("event") == EnumMessageCategory.EVENT
        assert _resolve_source("command") == EnumMessageCategory.COMMAND
        assert _resolve_source("intent") == EnumMessageCategory.INTENT

    def test_case_insensitive(self) -> None:
        assert _resolve_source("EVENT") == EnumMessageCategory.EVENT
        assert _resolve_source("Event") == EnumMessageCategory.EVENT

    def test_strips_whitespace(self) -> None:
        assert _resolve_source("  event  ") == EnumMessageCategory.EVENT

    def test_invalid_source_raises(self) -> None:
        import click

        with pytest.raises(click.exceptions.BadParameter, match="Unknown source"):
            _resolve_source("invalid")


class TestResolveTarget:
    """Tests for _resolve_target helper."""

    def test_resolves_valid_targets(self) -> None:
        assert _resolve_target("effect") == EnumNodeKind.EFFECT
        assert _resolve_target("compute") == EnumNodeKind.COMPUTE
        assert _resolve_target("reducer") == EnumNodeKind.REDUCER
        assert _resolve_target("orchestrator") == EnumNodeKind.ORCHESTRATOR

    def test_rejects_runtime_host(self) -> None:
        import click

        with pytest.raises(click.exceptions.BadParameter, match="Unknown target"):
            _resolve_target("runtime_host")

    def test_case_insensitive(self) -> None:
        assert _resolve_target("ORCHESTRATOR") == EnumNodeKind.ORCHESTRATOR

    def test_invalid_target_raises(self) -> None:
        import click

        with pytest.raises(click.exceptions.BadParameter, match="Unknown target"):
            _resolve_target("invalid")


class TestCheckCommand:
    """Tests for ``onex validate-shape check``."""

    def test_allowed_shape_event_to_orchestrator(self) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "validate-shape",
                "check",
                "--source",
                "event",
                "--target",
                "orchestrator",
            ],
        )
        assert "ALLOWED" in result.output
        assert "event_to_orchestrator" in result.output

    def test_allowed_shape_event_to_reducer(self) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["validate-shape", "check", "-s", "event", "-t", "reducer"],
        )
        assert "ALLOWED" in result.output
        assert "event_to_reducer" in result.output

    def test_allowed_shape_intent_to_effect(self) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["validate-shape", "check", "-s", "intent", "-t", "effect"],
        )
        assert "ALLOWED" in result.output

    def test_allowed_shape_command_to_orchestrator(self) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["validate-shape", "check", "-s", "command", "-t", "orchestrator"],
        )
        assert "ALLOWED" in result.output

    def test_allowed_shape_command_to_effect(self) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["validate-shape", "check", "-s", "command", "-t", "effect"],
        )
        assert "ALLOWED" in result.output

    def test_forbidden_shape_command_to_reducer(self) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["validate-shape", "check", "-s", "command", "-t", "reducer"],
        )
        assert result.exit_code != 0
        assert "FORBIDDEN" in result.output
        assert "Valid targets for this source category" in result.output

    def test_forbidden_shape_intent_to_orchestrator(self) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["validate-shape", "check", "-s", "intent", "-t", "orchestrator"],
        )
        assert result.exit_code != 0
        assert "FORBIDDEN" in result.output

    def test_forbidden_shape_event_to_compute(self) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["validate-shape", "check", "-s", "event", "-t", "compute"],
        )
        assert result.exit_code != 0
        assert "FORBIDDEN" in result.output

    def test_invalid_source_shows_error(self) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["validate-shape", "check", "-s", "bogus", "-t", "orchestrator"],
        )
        assert result.exit_code != 0
        assert "Unknown source" in result.output or "Error" in result.output

    def test_invalid_target_shows_error(self) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["validate-shape", "check", "-s", "event", "-t", "bogus"],
        )
        assert result.exit_code != 0
        assert "Unknown target" in result.output or "Error" in result.output

    def test_missing_source_shows_usage(self) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["validate-shape", "check", "--target", "orchestrator"],
        )
        assert result.exit_code != 0

    def test_missing_target_shows_usage(self) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["validate-shape", "check", "--source", "event"],
        )
        assert result.exit_code != 0


class TestListCommand:
    """Tests for ``onex validate-shape list``."""

    def test_lists_all_shapes(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["validate-shape", "list"])
        assert result.exit_code == 0
        assert "Canonical ONEX Execution Shapes" in result.output
        assert "event_to_orchestrator" in result.output
        assert "event_to_reducer" in result.output
        assert "intent_to_effect" in result.output
        assert "command_to_orchestrator" in result.output
        assert "command_to_effect" in result.output
        assert "Total: 5 canonical shapes" in result.output


class TestMatrixCommand:
    """Tests for ``onex validate-shape matrix``."""

    def test_displays_matrix(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["validate-shape", "matrix"])
        assert result.exit_code == 0
        # Should show all source categories as rows
        assert "event" in result.output
        assert "command" in result.output
        assert "intent" in result.output
        # Should show ALLOWED and --- markers
        assert "ALLOWED" in result.output
        assert "---" in result.output
        assert "Legend" in result.output


class TestValidConstants:
    """Tests for module-level constants."""

    def test_valid_sources_matches_enum(self) -> None:
        expected = {c.value for c in EnumMessageCategory}
        assert set(VALID_SOURCES) == expected

    def test_valid_targets_excludes_runtime_host(self) -> None:
        assert "runtime_host" not in VALID_TARGETS
        assert "effect" in VALID_TARGETS
        assert "compute" in VALID_TARGETS
        assert "reducer" in VALID_TARGETS
        assert "orchestrator" in VALID_TARGETS


class TestHelpText:
    """Tests for help text rendering."""

    def test_validate_shape_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["validate-shape", "--help"])
        assert result.exit_code == 0
        assert "execution shapes" in result.output.lower()

    def test_check_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["validate-shape", "check", "--help"])
        assert result.exit_code == 0
        assert "--source" in result.output
        assert "--target" in result.output

    def test_list_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["validate-shape", "list", "--help"])
        assert result.exit_code == 0

    def test_matrix_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["validate-shape", "matrix", "--help"])
        assert result.exit_code == 0
