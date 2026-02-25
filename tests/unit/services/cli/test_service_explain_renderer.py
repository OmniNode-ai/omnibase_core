#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Unit tests for ServiceExplainRenderer — OMN-2576.

Covers:
    - render(): all required fields present in output
    - render(): works offline (only reads from command_entry param)
    - render(): unknown/not-found command uses render_not_found()
    - render_not_found(): clear error message for unknown command ID
    - render_schema_fields(): object schema formats fields correctly
    - render_schema_fields(): non-object schema shows raw JSON fallback
    - render_schema_fields(): empty properties case
    - hidden/blocked commands: excluded from catalog before render is called
      (catalog responsibility, not renderer's — tested via ServiceCatalogManager)
    - optional metadata: catalog_refresh_ts and cli_version rendered when provided
    - examples: listed when present; fallback message when absent
"""

from __future__ import annotations

import pytest

from omnibase_core.enums.enum_cli_command_risk import EnumCliCommandRisk
from omnibase_core.enums.enum_cli_command_visibility import EnumCliCommandVisibility
from omnibase_core.enums.enum_cli_invocation_type import EnumCliInvocationType
from omnibase_core.models.contracts.model_cli_contribution import (
    ModelCliCommandEntry,
    ModelCliCommandExample,
    ModelCliInvocation,
)
from omnibase_core.services.cli.service_explain_renderer import ServiceExplainRenderer

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _make_command(
    cmd_id: str = "com.omninode.memory.query",
    display_name: str = "Query Memory",
    description: str = "Search the memory store.",
    group: str = "memory",
    permissions: list[str] | None = None,
    risk: EnumCliCommandRisk = EnumCliCommandRisk.LOW,
    requires_hitl: bool = False,
    visibility: EnumCliCommandVisibility = EnumCliCommandVisibility.PUBLIC,
    examples: list[ModelCliCommandExample] | None = None,
) -> ModelCliCommandEntry:
    """Build a minimal valid command entry for testing."""
    return ModelCliCommandEntry(
        id=cmd_id,
        display_name=display_name,
        description=description,
        group=group,
        args_schema_ref=f"{cmd_id}.args.v1",
        output_schema_ref=f"{cmd_id}.output.v1",
        invocation=ModelCliInvocation(
            invocation_type=EnumCliInvocationType.KAFKA_EVENT,
            topic="onex.cmd.memory.query.v1",
        ),
        permissions=permissions or [],
        risk=risk,
        requires_hitl=requires_hitl,
        visibility=visibility,
        examples=examples or [],
    )


@pytest.fixture
def renderer() -> ServiceExplainRenderer:
    """Return a fresh ServiceExplainRenderer."""
    return ServiceExplainRenderer()


@pytest.fixture
def basic_command() -> ModelCliCommandEntry:
    """Return a basic valid command entry."""
    return _make_command()


# ---------------------------------------------------------------------------
# render() — field presence
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestExplainRendererRenderFields:
    """Tests that render() includes all required diagnostic fields."""

    def test_render_contains_contract_id(
        self,
        renderer: ServiceExplainRenderer,
        basic_command: ModelCliCommandEntry,
    ) -> None:
        output = renderer.render(basic_command)
        assert "com.omninode.memory.query" in output

    def test_render_contains_display_name(
        self,
        renderer: ServiceExplainRenderer,
        basic_command: ModelCliCommandEntry,
    ) -> None:
        output = renderer.render(basic_command)
        assert "Query Memory" in output

    def test_render_contains_group(
        self,
        renderer: ServiceExplainRenderer,
        basic_command: ModelCliCommandEntry,
    ) -> None:
        output = renderer.render(basic_command)
        assert "memory" in output

    def test_render_contains_visibility(
        self,
        renderer: ServiceExplainRenderer,
        basic_command: ModelCliCommandEntry,
    ) -> None:
        output = renderer.render(basic_command)
        assert "public" in output

    def test_render_contains_invocation_type(
        self,
        renderer: ServiceExplainRenderer,
        basic_command: ModelCliCommandEntry,
    ) -> None:
        output = renderer.render(basic_command)
        assert "kafka_event" in output.lower()

    def test_render_contains_topic(
        self,
        renderer: ServiceExplainRenderer,
        basic_command: ModelCliCommandEntry,
    ) -> None:
        output = renderer.render(basic_command)
        assert "onex.cmd.memory.query.v1" in output

    def test_render_contains_risk(
        self,
        renderer: ServiceExplainRenderer,
        basic_command: ModelCliCommandEntry,
    ) -> None:
        output = renderer.render(basic_command)
        assert "low" in output

    def test_render_contains_hitl_no(
        self,
        renderer: ServiceExplainRenderer,
        basic_command: ModelCliCommandEntry,
    ) -> None:
        output = renderer.render(basic_command)
        assert "no" in output

    def test_render_contains_hitl_yes_for_critical(
        self, renderer: ServiceExplainRenderer
    ) -> None:
        cmd = _make_command(
            cmd_id="com.omninode.system.nuke",
            risk=EnumCliCommandRisk.CRITICAL,
            requires_hitl=True,
        )
        output = renderer.render(cmd)
        assert "yes" in output
        assert "critical" in output

    def test_render_contains_schema_ref(
        self,
        renderer: ServiceExplainRenderer,
        basic_command: ModelCliCommandEntry,
    ) -> None:
        output = renderer.render(basic_command)
        assert "com.omninode.memory.query.args.v1" in output

    def test_render_contains_output_schema_ref(
        self,
        renderer: ServiceExplainRenderer,
        basic_command: ModelCliCommandEntry,
    ) -> None:
        output = renderer.render(basic_command)
        assert "com.omninode.memory.query.output.v1" in output

    def test_render_contains_description(
        self,
        renderer: ServiceExplainRenderer,
        basic_command: ModelCliCommandEntry,
    ) -> None:
        output = renderer.render(basic_command)
        assert "Search the memory store." in output

    def test_render_permissions_shown_when_present(
        self, renderer: ServiceExplainRenderer
    ) -> None:
        cmd = _make_command(permissions=["memory.read", "catalog.view"])
        output = renderer.render(cmd)
        assert "memory.read" in output
        assert "catalog.view" in output

    def test_render_permissions_none_shown_when_absent(
        self, renderer: ServiceExplainRenderer
    ) -> None:
        cmd = _make_command(permissions=[])
        output = renderer.render(cmd)
        assert "(none)" in output


# ---------------------------------------------------------------------------
# render() — optional catalog metadata
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestExplainRendererMetadata:
    """Tests for optional catalog metadata rendering."""

    def test_render_with_refresh_ts(
        self, renderer: ServiceExplainRenderer, basic_command: ModelCliCommandEntry
    ) -> None:
        output = renderer.render(
            basic_command,
            catalog_refresh_ts="2026-02-25T01:00:00Z",
        )
        assert "2026-02-25T01:00:00Z" in output

    def test_render_without_refresh_ts_shows_not_available(
        self, renderer: ServiceExplainRenderer, basic_command: ModelCliCommandEntry
    ) -> None:
        output = renderer.render(basic_command, catalog_refresh_ts=None)
        assert "(not available)" in output

    def test_render_with_cli_version(
        self, renderer: ServiceExplainRenderer, basic_command: ModelCliCommandEntry
    ) -> None:
        output = renderer.render(basic_command, cli_version="0.19.0")
        assert "0.19.0" in output

    def test_render_without_cli_version_shows_not_configured(
        self, renderer: ServiceExplainRenderer, basic_command: ModelCliCommandEntry
    ) -> None:
        output = renderer.render(basic_command)
        assert "(not configured)" in output


# ---------------------------------------------------------------------------
# render() — examples
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestExplainRendererExamples:
    """Tests for example rendering in render()."""

    def test_render_with_examples(self, renderer: ServiceExplainRenderer) -> None:
        examples = [
            ModelCliCommandExample(
                description="Query last 10 records",
                invocation="omn com.omninode.memory.query --limit 10",
                expected_output="10 records returned",
            )
        ]
        cmd = _make_command(examples=examples)
        output = renderer.render(cmd)
        assert "Query last 10 records" in output
        assert "omn com.omninode.memory.query --limit 10" in output
        assert "10 records returned" in output

    def test_render_without_examples_shows_fallback(
        self, renderer: ServiceExplainRenderer
    ) -> None:
        cmd = _make_command(examples=[])
        output = renderer.render(cmd)
        assert "(no examples provided)" in output

    def test_render_example_without_expected_output(
        self, renderer: ServiceExplainRenderer
    ) -> None:
        examples = [
            ModelCliCommandExample(
                description="Basic query",
                invocation="omn com.omninode.memory.query",
                expected_output=None,
            )
        ]
        cmd = _make_command(examples=examples)
        output = renderer.render(cmd)
        assert "Basic query" in output
        assert "omn com.omninode.memory.query" in output


# ---------------------------------------------------------------------------
# render_not_found()
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestExplainRendererNotFound:
    """Tests for render_not_found()."""

    def test_not_found_contains_command_id(
        self, renderer: ServiceExplainRenderer
    ) -> None:
        output = renderer.render_not_found("com.omninode.does.not.exist")
        assert "com.omninode.does.not.exist" in output

    def test_not_found_contains_helpful_hint(
        self, renderer: ServiceExplainRenderer
    ) -> None:
        output = renderer.render_not_found("com.omninode.does.not.exist")
        assert "omn refresh" in output

    def test_not_found_contains_help_hint(
        self, renderer: ServiceExplainRenderer
    ) -> None:
        output = renderer.render_not_found("com.omninode.does.not.exist")
        assert "omn --help" in output

    def test_not_found_is_non_empty(self, renderer: ServiceExplainRenderer) -> None:
        output = renderer.render_not_found("x.y")
        assert len(output) > 50


# ---------------------------------------------------------------------------
# render_schema_fields()
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestExplainRendererSchemaFields:
    """Tests for render_schema_fields()."""

    def test_schema_fields_basic_properties(
        self, renderer: ServiceExplainRenderer
    ) -> None:
        schema: dict[str, object] = {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Max results.",
                    "default": 10,
                },
                "query": {
                    "type": "string",
                    "description": "Search query.",
                },
            },
            "required": ["query"],
        }
        output = renderer.render_schema_fields(schema, "com.omninode.test.run")
        assert "--limit" in output
        assert "--query" in output
        assert "integer" in output
        assert "string" in output
        assert "[required]" in output
        assert "Max results." in output
        assert "Search query." in output

    def test_schema_fields_default_shown(
        self, renderer: ServiceExplainRenderer
    ) -> None:
        schema: dict[str, object] = {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "default": 10},
            },
        }
        output = renderer.render_schema_fields(schema, "com.omninode.test.run")
        assert "10" in output

    def test_schema_fields_enum_type(self, renderer: ServiceExplainRenderer) -> None:
        schema: dict[str, object] = {
            "type": "object",
            "properties": {
                "mode": {
                    "type": "string",
                    "enum": ["fast", "slow"],
                    "description": "Execution mode.",
                },
            },
        }
        output = renderer.render_schema_fields(schema, "com.omninode.test.run")
        assert "fast" in output
        assert "slow" in output
        assert "enum" in output

    def test_schema_fields_non_object_fallback(
        self, renderer: ServiceExplainRenderer
    ) -> None:
        schema: dict[str, object] = {"type": "string"}
        output = renderer.render_schema_fields(schema, "com.omninode.test.run")
        assert "string" in output

    def test_schema_fields_empty_properties(
        self, renderer: ServiceExplainRenderer
    ) -> None:
        schema: dict[str, object] = {"type": "object", "properties": {}}
        output = renderer.render_schema_fields(schema, "com.omninode.test.run")
        assert "no properties" in output

    def test_schema_fields_required_marker_absent_when_not_required(
        self, renderer: ServiceExplainRenderer
    ) -> None:
        schema: dict[str, object] = {
            "type": "object",
            "properties": {
                "optional_field": {"type": "string", "description": "Optional."},
            },
        }
        output = renderer.render_schema_fields(schema, "com.omninode.test.run")
        assert "[required]" not in output

    def test_schema_fields_command_id_in_header(
        self, renderer: ServiceExplainRenderer
    ) -> None:
        schema: dict[str, object] = {"type": "object", "properties": {}}
        output = renderer.render_schema_fields(schema, "com.omninode.test.run")
        assert "com.omninode.test.run" in output


# ---------------------------------------------------------------------------
# Offline safety — no network calls during render
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestExplainRendererOffline:
    """Tests confirming render() makes no network calls."""

    def test_render_does_not_import_network_modules(
        self, renderer: ServiceExplainRenderer, basic_command: ModelCliCommandEntry
    ) -> None:
        """render() should not import kafka, httpx, or requests."""
        import sys

        # Gather initial modules
        before = set(sys.modules.keys())

        # Execute render
        _ = renderer.render(basic_command)

        after = set(sys.modules.keys())
        new_imports = after - before

        network_patterns = {"kafka", "httpx", "requests", "aiohttp", "urllib3"}
        for pattern in network_patterns:
            for module_name in new_imports:
                assert pattern not in module_name, (
                    f"render() imported network module '{module_name}'"
                )
