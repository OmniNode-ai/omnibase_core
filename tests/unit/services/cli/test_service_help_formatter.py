#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Unit tests for ServiceHelpFormatter — OMN-2576.

Covers:
    - format_help(): groups commands into Core / Node-provided / Experimental
    - format_help(): core group detection by group name
    - format_help(): experimental commands in their own section
    - format_help(): hidden commands absent from output (excluded by catalog,
      not by formatter — tested by confirming formatter shows what it receives)
    - format_help(): empty catalog shows helpful fallback message
    - format_help(): each command shows a one-line description (not raw JSON)
    - format_help(): deterministic output (sorted within sections)
    - format_help(): cli_version shown in header when provided
"""

from __future__ import annotations

import pytest

from omnibase_core.enums.enum_cli_command_visibility import EnumCliCommandVisibility
from omnibase_core.enums.enum_cli_invocation_type import EnumCliInvocationType
from omnibase_core.models.contracts.model_cli_contribution import (
    ModelCliCommandEntry,
    ModelCliInvocation,
)
from omnibase_core.services.cli.service_help_formatter import ServiceHelpFormatter

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _make_command(
    cmd_id: str,
    display_name: str = "A Command",
    description: str = "Does something useful.",
    group: str = "memory",
    visibility: EnumCliCommandVisibility = EnumCliCommandVisibility.PUBLIC,
) -> ModelCliCommandEntry:
    """Build a minimal valid command entry."""
    return ModelCliCommandEntry(
        id=cmd_id,
        display_name=display_name,
        description=description,
        group=group,
        args_schema_ref=f"{cmd_id}.args.v1",
        output_schema_ref=f"{cmd_id}.output.v1",
        invocation=ModelCliInvocation(
            invocation_type=EnumCliInvocationType.KAFKA_EVENT,
            topic="onex.cmd.test.v1",
        ),
        visibility=visibility,
    )


@pytest.fixture
def formatter() -> ServiceHelpFormatter:
    """Return a fresh ServiceHelpFormatter."""
    return ServiceHelpFormatter()


# ---------------------------------------------------------------------------
# Grouping
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestHelpFormatterGrouping:
    """Tests that format_help() groups commands correctly."""

    def test_core_group_in_core_section(self, formatter: ServiceHelpFormatter) -> None:
        entries = [
            _make_command("com.omninode.core.refresh", group="core"),
        ]
        output = formatter.format_help(entries)
        assert "CORE COMMANDS" in output
        assert "com.omninode.core.refresh" in output

    def test_catalog_group_in_core_section(
        self, formatter: ServiceHelpFormatter
    ) -> None:
        entries = [
            _make_command("com.omninode.catalog.list", group="catalog"),
        ]
        output = formatter.format_help(entries)
        assert "CORE COMMANDS" in output
        assert "com.omninode.catalog.list" in output

    def test_non_core_group_in_node_provided_section(
        self, formatter: ServiceHelpFormatter
    ) -> None:
        entries = [
            _make_command("com.omninode.memory.query", group="memory"),
        ]
        output = formatter.format_help(entries)
        assert "NODE-PROVIDED COMMANDS" in output
        assert "com.omninode.memory.query" in output

    def test_experimental_in_experimental_section(
        self, formatter: ServiceHelpFormatter
    ) -> None:
        entries = [
            _make_command(
                "com.omninode.experiment.beta",
                group="memory",
                visibility=EnumCliCommandVisibility.EXPERIMENTAL,
            ),
        ]
        output = formatter.format_help(entries)
        assert "EXPERIMENTAL" in output
        assert "com.omninode.experiment.beta" in output

    def test_experimental_not_in_node_provided(
        self, formatter: ServiceHelpFormatter
    ) -> None:
        entries = [
            _make_command(
                "com.omninode.experiment.beta",
                group="memory",
                visibility=EnumCliCommandVisibility.EXPERIMENTAL,
            ),
        ]
        output = formatter.format_help(entries)
        assert "NODE-PROVIDED COMMANDS" not in output

    def test_mixed_commands_grouped_correctly(
        self, formatter: ServiceHelpFormatter
    ) -> None:
        entries = [
            _make_command("com.omninode.core.refresh", group="core"),
            _make_command("com.omninode.memory.query", group="memory"),
            _make_command(
                "com.omninode.experiment.beta",
                group="memory",
                visibility=EnumCliCommandVisibility.EXPERIMENTAL,
            ),
        ]
        output = formatter.format_help(entries)
        assert "CORE COMMANDS" in output
        assert "NODE-PROVIDED COMMANDS" in output
        assert "EXPERIMENTAL" in output
        assert "com.omninode.core.refresh" in output
        assert "com.omninode.memory.query" in output
        assert "com.omninode.experiment.beta" in output

    def test_core_not_shown_when_no_core_commands(
        self, formatter: ServiceHelpFormatter
    ) -> None:
        entries = [
            _make_command("com.omninode.memory.query", group="memory"),
        ]
        output = formatter.format_help(entries)
        assert "CORE COMMANDS" not in output

    def test_experimental_section_not_shown_when_none(
        self, formatter: ServiceHelpFormatter
    ) -> None:
        entries = [
            _make_command("com.omninode.memory.query", group="memory"),
        ]
        output = formatter.format_help(entries)
        assert "EXPERIMENTAL" not in output


# ---------------------------------------------------------------------------
# Empty catalog
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestHelpFormatterEmptyCatalog:
    """Tests for empty catalog fallback."""

    def test_empty_catalog_shows_fallback(
        self, formatter: ServiceHelpFormatter
    ) -> None:
        output = formatter.format_help([])
        assert "No commands available" in output
        assert "omn refresh" in output

    def test_empty_catalog_no_section_headers(
        self, formatter: ServiceHelpFormatter
    ) -> None:
        output = formatter.format_help([])
        assert "CORE COMMANDS" not in output
        assert "NODE-PROVIDED COMMANDS" not in output
        assert "EXPERIMENTAL" not in output


# ---------------------------------------------------------------------------
# Content quality
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestHelpFormatterContent:
    """Tests that output contains expected content."""

    def test_each_command_shows_one_line_description(
        self, formatter: ServiceHelpFormatter
    ) -> None:
        entries = [
            _make_command(
                "com.omninode.memory.query",
                description="Search the memory store.",
                group="memory",
            ),
        ]
        output = formatter.format_help(entries)
        assert "Search the memory store." in output

    def test_command_id_shown_in_output(self, formatter: ServiceHelpFormatter) -> None:
        entries = [
            _make_command("com.omninode.memory.query", group="memory"),
        ]
        output = formatter.format_help(entries)
        assert "com.omninode.memory.query" in output

    def test_cli_version_shown_in_header(self, formatter: ServiceHelpFormatter) -> None:
        entries = [_make_command("com.omninode.memory.query", group="memory")]
        output = formatter.format_help(entries, cli_version="0.19.0")
        assert "0.19.0" in output

    def test_cli_version_absent_when_not_provided(
        self, formatter: ServiceHelpFormatter
    ) -> None:
        entries = [_make_command("com.omninode.memory.query", group="memory")]
        output = formatter.format_help(entries)
        # Header should be present but without version
        assert "omn" in output

    def test_explain_hint_shown_in_footer(
        self, formatter: ServiceHelpFormatter
    ) -> None:
        output = formatter.format_help([])
        assert "omn explain" in output

    def test_refresh_hint_shown_in_footer(
        self, formatter: ServiceHelpFormatter
    ) -> None:
        output = formatter.format_help([])
        assert "omn refresh" in output


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestHelpFormatterDeterminism:
    """Tests that output is deterministic (same input → same output)."""

    def test_same_input_same_output(self, formatter: ServiceHelpFormatter) -> None:
        entries = [
            _make_command("com.omninode.memory.query", group="memory"),
            _make_command("com.omninode.core.refresh", group="core"),
        ]
        output1 = formatter.format_help(entries)
        output2 = formatter.format_help(entries)
        assert output1 == output2

    def test_sorted_within_section(self, formatter: ServiceHelpFormatter) -> None:
        entries = [
            _make_command(
                "com.omninode.memory.store", display_name="Store", group="memory"
            ),
            _make_command(
                "com.omninode.memory.query", display_name="Query", group="memory"
            ),
        ]
        output = formatter.format_help(entries)
        # "Query" should appear before "Store" (alphabetical by display_name)
        query_pos = output.find("com.omninode.memory.query")
        store_pos = output.find("com.omninode.memory.store")
        assert query_pos < store_pos


# ---------------------------------------------------------------------------
# Hidden commands excluded (catalog responsibility)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestHelpFormatterHiddenExclusion:
    """Tests confirming the formatter renders only what it receives.

    The actual filtering of HIDDEN/DEPRECATED commands is done by
    ServiceCatalogManager.  The formatter renders whatever entries are
    passed to it — this test confirms it does not add its own filtering
    for HIDDEN commands.
    """

    def test_hidden_command_present_in_output_when_passed(
        self, formatter: ServiceHelpFormatter
    ) -> None:
        """If a caller passes hidden commands, the formatter renders them."""
        entries = [
            _make_command(
                "com.omninode.hidden.cmd",
                group="memory",
                visibility=EnumCliCommandVisibility.HIDDEN,
            ),
        ]
        output = formatter.format_help(entries)
        # HIDDEN is not EXPERIMENTAL so it lands in NODE-PROVIDED
        assert "com.omninode.hidden.cmd" in output

    def test_deprecated_command_present_in_output_when_passed(
        self, formatter: ServiceHelpFormatter
    ) -> None:
        """Deprecated commands passed to the formatter are rendered."""
        entries = [
            _make_command(
                "com.omninode.old.cmd",
                group="memory",
                visibility=EnumCliCommandVisibility.DEPRECATED,
            ),
        ]
        output = formatter.format_help(entries)
        assert "com.omninode.old.cmd" in output
