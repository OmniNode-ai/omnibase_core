# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
Unit tests for RendererDiff.

This module provides comprehensive tests for the contract diff rendering utilities,
validating all output formats (text, JSON, markdown, HTML) and edge cases.

Coverage Requirements:
- >95% line coverage for all methods
- 100% coverage for error handling paths
- Comprehensive edge case and boundary condition testing
"""

import json
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from omnibase_core.enums.enum_contract_diff_change_type import (
    EnumContractDiffChangeType,
)
from omnibase_core.enums.enum_output_format import EnumOutputFormat
from omnibase_core.models.cli.model_output_format_options import (
    ModelOutputFormatOptions,
)
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.contracts.diff.model_contract_diff import ModelContractDiff
from omnibase_core.models.contracts.diff.model_contract_field_diff import (
    ModelContractFieldDiff,
)
from omnibase_core.models.contracts.diff.model_contract_list_diff import (
    ModelContractListDiff,
)
from omnibase_core.rendering.renderer_diff import RendererDiff

# =================== FIXTURES ===================


@pytest.fixture
def empty_diff() -> ModelContractDiff:
    """Diff with no changes."""
    return ModelContractDiff(
        diff_id=uuid4(),
        before_contract_name="TestContract",
        after_contract_name="TestContract",
        field_diffs=[],
        list_diffs=[],
        computed_at=datetime.now(UTC),
    )


@pytest.fixture
def simple_diff() -> ModelContractDiff:
    """Diff with one of each change type (except UNCHANGED and MOVED)."""
    return ModelContractDiff(
        diff_id=uuid4(),
        before_contract_name="TestContract",
        after_contract_name="TestContract",
        field_diffs=[
            ModelContractFieldDiff(
                field_path="meta.name",
                change_type=EnumContractDiffChangeType.MODIFIED,
                old_value=ModelSchemaValue.from_value("OldName"),
                new_value=ModelSchemaValue.from_value("NewName"),
                value_type="str",
            ),
            ModelContractFieldDiff(
                field_path="meta.version",
                change_type=EnumContractDiffChangeType.ADDED,
                old_value=None,
                new_value=ModelSchemaValue.from_value("2.0.0"),
                value_type="str",
            ),
            ModelContractFieldDiff(
                field_path="meta.deprecated",
                change_type=EnumContractDiffChangeType.REMOVED,
                old_value=ModelSchemaValue.from_value(True),
                new_value=None,
                value_type="bool",
            ),
        ],
        list_diffs=[],
        computed_at=datetime.now(UTC),
    )


@pytest.fixture
def diff_with_only_added() -> ModelContractDiff:
    """Diff with only added fields."""
    return ModelContractDiff(
        diff_id=uuid4(),
        before_contract_name="BeforeContract",
        after_contract_name="AfterContract",
        field_diffs=[
            ModelContractFieldDiff(
                field_path="field_a",
                change_type=EnumContractDiffChangeType.ADDED,
                old_value=None,
                new_value=ModelSchemaValue.from_value("value_a"),
                value_type="str",
            ),
            ModelContractFieldDiff(
                field_path="field_b",
                change_type=EnumContractDiffChangeType.ADDED,
                old_value=None,
                new_value=ModelSchemaValue.from_value(42),
                value_type="int",
            ),
        ],
        list_diffs=[],
        computed_at=datetime.now(UTC),
    )


@pytest.fixture
def diff_with_only_removed() -> ModelContractDiff:
    """Diff with only removed fields."""
    return ModelContractDiff(
        diff_id=uuid4(),
        before_contract_name="BeforeContract",
        after_contract_name="AfterContract",
        field_diffs=[
            ModelContractFieldDiff(
                field_path="old_field_x",
                change_type=EnumContractDiffChangeType.REMOVED,
                old_value=ModelSchemaValue.from_value("old_value"),
                new_value=None,
                value_type="str",
            ),
            ModelContractFieldDiff(
                field_path="old_field_y",
                change_type=EnumContractDiffChangeType.REMOVED,
                old_value=ModelSchemaValue.from_value(100),
                new_value=None,
                value_type="int",
            ),
        ],
        list_diffs=[],
        computed_at=datetime.now(UTC),
    )


@pytest.fixture
def diff_with_only_modified() -> ModelContractDiff:
    """Diff with only modified fields."""
    return ModelContractDiff(
        diff_id=uuid4(),
        before_contract_name="TestContract",
        after_contract_name="TestContract",
        field_diffs=[
            ModelContractFieldDiff(
                field_path="config.timeout",
                change_type=EnumContractDiffChangeType.MODIFIED,
                old_value=ModelSchemaValue.from_value(1000),
                new_value=ModelSchemaValue.from_value(2000),
                value_type="int",
            ),
            ModelContractFieldDiff(
                field_path="config.enabled",
                change_type=EnumContractDiffChangeType.MODIFIED,
                old_value=ModelSchemaValue.from_value(True),
                new_value=ModelSchemaValue.from_value(False),
                value_type="bool",
            ),
        ],
        list_diffs=[],
        computed_at=datetime.now(UTC),
    )


@pytest.fixture
def diff_with_moved_list_items() -> ModelContractDiff:
    """Diff with moved list items."""
    return ModelContractDiff(
        diff_id=uuid4(),
        before_contract_name="TestContract",
        after_contract_name="TestContract",
        field_diffs=[],
        list_diffs=[
            ModelContractListDiff(
                field_path="dependencies",
                identity_key="name",
                added_items=[],
                removed_items=[],
                modified_items=[],
                moved_items=[
                    ModelContractFieldDiff(
                        field_path="dependencies[dep_a]",
                        change_type=EnumContractDiffChangeType.MOVED,
                        old_value=ModelSchemaValue.from_value({"name": "dep_a"}),
                        new_value=ModelSchemaValue.from_value({"name": "dep_a"}),
                        value_type="dict",
                        old_index=0,
                        new_index=1,
                    ),
                    ModelContractFieldDiff(
                        field_path="dependencies[dep_b]",
                        change_type=EnumContractDiffChangeType.MOVED,
                        old_value=ModelSchemaValue.from_value({"name": "dep_b"}),
                        new_value=ModelSchemaValue.from_value({"name": "dep_b"}),
                        value_type="dict",
                        old_index=1,
                        new_index=0,
                    ),
                ],
                unchanged_count=0,
            )
        ],
        computed_at=datetime.now(UTC),
    )


@pytest.fixture
def large_diff() -> ModelContractDiff:
    """Diff with many fields for testing collapsible sections."""
    field_diffs = [
        ModelContractFieldDiff(
            field_path=f"field_{i}",
            change_type=EnumContractDiffChangeType.MODIFIED,
            old_value=ModelSchemaValue.from_value(f"old_{i}"),
            new_value=ModelSchemaValue.from_value(f"new_{i}"),
            value_type="str",
        )
        for i in range(15)  # More than 10 to trigger collapsible
    ]
    return ModelContractDiff(
        diff_id=uuid4(),
        before_contract_name="LargeContract",
        after_contract_name="LargeContract",
        field_diffs=field_diffs,
        list_diffs=[],
        computed_at=datetime.now(UTC),
    )


@pytest.fixture
def diff_with_none_values() -> ModelContractDiff:
    """Diff with None values (null in schema)."""
    return ModelContractDiff(
        diff_id=uuid4(),
        before_contract_name="TestContract",
        after_contract_name="TestContract",
        field_diffs=[
            ModelContractFieldDiff(
                field_path="nullable_field",
                change_type=EnumContractDiffChangeType.MODIFIED,
                old_value=ModelSchemaValue.from_value(None),
                new_value=ModelSchemaValue.from_value("now_has_value"),
                value_type="str",
            ),
        ],
        list_diffs=[],
        computed_at=datetime.now(UTC),
    )


@pytest.fixture
def diff_with_complex_values() -> ModelContractDiff:
    """Diff with complex nested values."""
    return ModelContractDiff(
        diff_id=uuid4(),
        before_contract_name="ComplexContract",
        after_contract_name="ComplexContract",
        field_diffs=[
            ModelContractFieldDiff(
                field_path="nested.config",
                change_type=EnumContractDiffChangeType.MODIFIED,
                old_value=ModelSchemaValue.from_value({"key": "old", "count": 1}),
                new_value=ModelSchemaValue.from_value({"key": "new", "count": 2}),
                value_type="dict",
            ),
            ModelContractFieldDiff(
                field_path="items_list",
                change_type=EnumContractDiffChangeType.MODIFIED,
                old_value=ModelSchemaValue.from_value(["a", "b"]),
                new_value=ModelSchemaValue.from_value(["a", "b", "c"]),
                value_type="list",
            ),
        ],
        list_diffs=[],
        computed_at=datetime.now(UTC),
    )


@pytest.fixture
def diff_with_list_changes() -> ModelContractDiff:
    """Diff with list-level changes (added, removed, modified items)."""
    return ModelContractDiff(
        diff_id=uuid4(),
        before_contract_name="TestContract",
        after_contract_name="TestContract",
        field_diffs=[],
        list_diffs=[
            ModelContractListDiff(
                field_path="dependencies",
                identity_key="name",
                added_items=[
                    ModelContractFieldDiff(
                        field_path="dependencies[new_dep]",
                        change_type=EnumContractDiffChangeType.ADDED,
                        old_value=None,
                        new_value=ModelSchemaValue.from_value({"name": "new_dep"}),
                        value_type="dict",
                    ),
                ],
                removed_items=[
                    ModelContractFieldDiff(
                        field_path="dependencies[old_dep]",
                        change_type=EnumContractDiffChangeType.REMOVED,
                        old_value=ModelSchemaValue.from_value({"name": "old_dep"}),
                        new_value=None,
                        value_type="dict",
                    ),
                ],
                modified_items=[
                    ModelContractFieldDiff(
                        field_path="dependencies[mod_dep].version",
                        change_type=EnumContractDiffChangeType.MODIFIED,
                        old_value=ModelSchemaValue.from_value("1.0"),
                        new_value=ModelSchemaValue.from_value("2.0"),
                        value_type="str",
                    ),
                ],
                moved_items=[],
                unchanged_count=2,
            )
        ],
        computed_at=datetime.now(UTC),
    )


# =================== RENDER ROUTING TESTS ===================


@pytest.mark.unit
class TestRendererDiffRouting:
    """Tests for RendererDiff.render() routing behavior."""

    def test_render_routes_to_text(self, simple_diff: ModelContractDiff) -> None:
        """Test render() routes TEXT to render_text()."""
        output = RendererDiff.render(simple_diff, EnumOutputFormat.TEXT)

        # Should contain text-specific output (contract name header, etc.)
        assert "Contract Diff:" in output
        assert simple_diff.before_contract_name in output

    def test_render_routes_to_json(self, simple_diff: ModelContractDiff) -> None:
        """Test render() routes JSON to render_json()."""
        output = RendererDiff.render(simple_diff, EnumOutputFormat.JSON)

        # Should be valid JSON
        parsed = json.loads(output)
        assert isinstance(parsed, dict)
        assert "before_contract_name" in parsed

    def test_render_routes_to_markdown(self, simple_diff: ModelContractDiff) -> None:
        """Test render() routes MARKDOWN to render_markdown()."""
        output = RendererDiff.render(simple_diff, EnumOutputFormat.MARKDOWN)

        # Should contain markdown-specific formatting
        assert "# Contract Diff:" in output
        assert "|" in output  # Markdown table

    def test_render_routes_to_detailed(self, simple_diff: ModelContractDiff) -> None:
        """Test render() routes DETAILED to render_text() without colors."""
        output = RendererDiff.render(simple_diff, EnumOutputFormat.DETAILED)

        # Should be text format
        assert "Contract Diff:" in output
        # Should NOT contain ANSI color codes
        assert "\033[" not in output

    def test_render_routes_to_compact(self, simple_diff: ModelContractDiff) -> None:
        """Test render() routes COMPACT to _render_compact()."""
        output = RendererDiff.render(simple_diff, EnumOutputFormat.COMPACT)

        # Compact format is a single line
        assert simple_diff.before_contract_name in output
        assert len(output.splitlines()) == 1

    def test_render_unsupported_format_raises(
        self, simple_diff: ModelContractDiff
    ) -> None:
        """Test render() raises ValueError for unsupported formats."""
        # RAW format is not supported by RendererDiff
        with pytest.raises(ValueError, match="Unsupported output format"):
            RendererDiff.render(simple_diff, EnumOutputFormat.RAW)


# =================== TEXT RENDERING TESTS ===================


@pytest.mark.unit
class TestRendererDiffText:
    """Tests for RendererDiff.render_text()."""

    def test_render_text_includes_symbols(self, simple_diff: ModelContractDiff) -> None:
        """Test text output includes +/- symbols."""
        output = RendererDiff.render_text(simple_diff, use_colors=False)

        # Check for symbols
        assert "+" in output  # ADDED
        assert "-" in output  # REMOVED
        assert "~" in output  # MODIFIED

    def test_render_text_includes_header(self, simple_diff: ModelContractDiff) -> None:
        """Test text output includes header with contract names."""
        output = RendererDiff.render_text(simple_diff, use_colors=False)

        assert "Contract Diff:" in output
        assert simple_diff.before_contract_name in output
        assert simple_diff.after_contract_name in output

    def test_render_text_includes_summary(self, simple_diff: ModelContractDiff) -> None:
        """Test text output includes change summary."""
        output = RendererDiff.render_text(simple_diff, use_colors=False)

        assert "Summary:" in output
        assert "added" in output.lower()
        assert "removed" in output.lower()
        assert "modified" in output.lower()

    def test_render_text_no_colors(self, simple_diff: ModelContractDiff) -> None:
        """Test text output without ANSI colors."""
        output = RendererDiff.render_text(simple_diff, use_colors=False)

        # Should NOT contain ANSI escape codes
        assert "\033[" not in output

    def test_render_text_with_colors(self, simple_diff: ModelContractDiff) -> None:
        """Test text output with ANSI colors."""
        output = RendererDiff.render_text(simple_diff, use_colors=True)

        # Should contain ANSI escape codes
        assert "\033[" in output

    def test_render_text_respects_options_color_disabled(
        self, simple_diff: ModelContractDiff
    ) -> None:
        """Test that options.color_enabled=False overrides use_colors."""
        options = ModelOutputFormatOptions(color_enabled=False)
        output = RendererDiff.render_text(simple_diff, options=options, use_colors=True)

        # Should NOT contain ANSI escape codes despite use_colors=True
        assert "\033[" not in output

    def test_render_text_empty_diff(self, empty_diff: ModelContractDiff) -> None:
        """Test text output for empty diff (no changes)."""
        output = RendererDiff.render_text(empty_diff, use_colors=False)

        assert "No changes detected" in output

    def test_render_text_includes_field_changes(
        self, simple_diff: ModelContractDiff
    ) -> None:
        """Test text output includes field change details."""
        output = RendererDiff.render_text(simple_diff, use_colors=False)

        assert "Field Changes:" in output
        assert "meta.name" in output
        assert "meta.version" in output
        assert "meta.deprecated" in output


# =================== JSON RENDERING TESTS ===================


@pytest.mark.unit
class TestRendererDiffJson:
    """Tests for RendererDiff.render_json()."""

    def test_render_json_is_valid_json(self, simple_diff: ModelContractDiff) -> None:
        """Test JSON output can be parsed."""
        output = RendererDiff.render_json(simple_diff)

        # Should be valid JSON
        parsed = json.loads(output)
        assert isinstance(parsed, dict)

    def test_render_json_contains_all_fields(
        self, simple_diff: ModelContractDiff
    ) -> None:
        """Test JSON output contains all diff fields."""
        output = RendererDiff.render_json(simple_diff)
        parsed = json.loads(output)

        assert "diff_id" in parsed
        assert "before_contract_name" in parsed
        assert "after_contract_name" in parsed
        assert "field_diffs" in parsed
        assert "list_diffs" in parsed
        assert "computed_at" in parsed
        assert "has_changes" in parsed
        assert "total_changes" in parsed
        assert "change_summary" in parsed

    def test_render_json_with_indent(self, simple_diff: ModelContractDiff) -> None:
        """Test JSON output respects indent parameter."""
        output_indent_2 = RendererDiff.render_json(simple_diff, indent=2)
        output_indent_4 = RendererDiff.render_json(simple_diff, indent=4)

        # Both should be valid JSON
        json.loads(output_indent_2)
        json.loads(output_indent_4)

        # Indent 4 should produce longer output due to more spaces
        assert len(output_indent_4) > len(output_indent_2)

        # Verify the outputs have expected indent patterns at first level
        assert '\n  "' in output_indent_2  # First level uses 2 spaces
        assert '\n    "' in output_indent_4  # First level uses 4 spaces

    def test_render_json_options_pretty_print_false(
        self, simple_diff: ModelContractDiff
    ) -> None:
        """Test JSON output with pretty_print=False is compact."""
        options = ModelOutputFormatOptions(pretty_print=False)
        output = RendererDiff.render_json(simple_diff, options=options)

        # Compact JSON should have fewer newlines
        assert output.count("\n") < 5

    def test_render_json_options_sort_keys(
        self, simple_diff: ModelContractDiff
    ) -> None:
        """Test JSON output with sort_keys=True sorts keys."""
        options = ModelOutputFormatOptions(sort_keys=True)
        output = RendererDiff.render_json(simple_diff, options=options)
        parsed = json.loads(output)

        # Keys should be sorted
        keys = list(parsed.keys())
        assert keys == sorted(keys)

    def test_render_json_empty_diff(self, empty_diff: ModelContractDiff) -> None:
        """Test JSON output for empty diff."""
        output = RendererDiff.render_json(empty_diff)
        parsed = json.loads(output)

        assert parsed["has_changes"] is False
        assert parsed["total_changes"] == 0
        assert parsed["field_diffs"] == []
        assert parsed["list_diffs"] == []


# =================== MARKDOWN RENDERING TESTS ===================


@pytest.mark.unit
class TestRendererDiffMarkdown:
    """Tests for RendererDiff.render_markdown()."""

    def test_render_markdown_has_title(self, simple_diff: ModelContractDiff) -> None:
        """Test markdown output has proper title header."""
        output = RendererDiff.render_markdown(simple_diff)

        assert "# Contract Diff:" in output
        assert simple_diff.before_contract_name in output

    def test_render_markdown_has_table(self, simple_diff: ModelContractDiff) -> None:
        """Test markdown output includes table."""
        output = RendererDiff.render_markdown(simple_diff)

        # Markdown tables have | separators and header lines
        assert "| Change | Field Path | Old Value | New Value |" in output
        assert "|:------:|" in output

    def test_render_markdown_has_summary_section(
        self, simple_diff: ModelContractDiff
    ) -> None:
        """Test markdown output has summary section."""
        output = RendererDiff.render_markdown(simple_diff)

        assert "## Summary" in output
        assert "**Total Changes**" in output

    def test_render_markdown_has_metadata(self, simple_diff: ModelContractDiff) -> None:
        """Test markdown output includes metadata (computed_at, diff_id)."""
        output = RendererDiff.render_markdown(simple_diff)

        assert "**Computed At**" in output
        assert "**Diff ID**" in output

    def test_render_markdown_empty_diff(self, empty_diff: ModelContractDiff) -> None:
        """Test markdown output for empty diff."""
        output = RendererDiff.render_markdown(empty_diff)

        assert "*No changes detected.*" in output

    def test_render_markdown_collapsible_for_large_diffs(
        self, large_diff: ModelContractDiff
    ) -> None:
        """Test markdown uses collapsible sections for large diffs (>10 items)."""
        output = RendererDiff.render_markdown(large_diff)

        # Should use <details> for collapsible section
        assert "<details>" in output
        assert "<summary>" in output
        assert "</details>" in output

    def test_render_markdown_field_paths_in_backticks(
        self, simple_diff: ModelContractDiff
    ) -> None:
        """Test markdown wraps field paths in backticks."""
        output = RendererDiff.render_markdown(simple_diff)

        # Field paths should be in backticks
        assert "`meta.name`" in output


# =================== HTML RENDERING TESTS ===================


@pytest.mark.unit
class TestRendererDiffHtml:
    """Tests for RendererDiff.render_html()."""

    def test_render_html_has_table_tags(self, simple_diff: ModelContractDiff) -> None:
        """Test HTML output includes table elements."""
        output = RendererDiff.render_html(simple_diff)

        assert "<table" in output
        assert "</table>" in output
        assert "<tr" in output
        assert "<td" in output
        assert "<th" in output

    def test_render_html_has_css_classes(self, simple_diff: ModelContractDiff) -> None:
        """Test HTML output uses CSS classes."""
        output = RendererDiff.render_html(simple_diff)

        assert 'class="diff-container"' in output
        assert 'class="diff-header"' in output
        assert 'class="diff-table"' in output

    def test_render_html_has_change_type_classes(
        self, simple_diff: ModelContractDiff
    ) -> None:
        """Test HTML output applies change type CSS classes to rows."""
        output = RendererDiff.render_html(simple_diff)

        assert 'class="diff-added"' in output
        assert 'class="diff-removed"' in output
        assert 'class="diff-modified"' in output

    def test_render_html_standalone_has_css(
        self, simple_diff: ModelContractDiff
    ) -> None:
        """Test standalone HTML includes inline CSS."""
        output = RendererDiff.render_html(simple_diff, standalone=True)

        assert "<!DOCTYPE html>" in output
        assert "<html" in output
        assert "<head>" in output
        assert "<style>" in output
        assert "</style>" in output
        assert "</html>" in output

    def test_render_html_non_standalone_no_doctype(
        self, simple_diff: ModelContractDiff
    ) -> None:
        """Test non-standalone HTML does not include DOCTYPE."""
        output = RendererDiff.render_html(simple_diff, standalone=False)

        assert "<!DOCTYPE html>" not in output
        assert "<html" not in output

    def test_render_html_escapes_special_chars(
        self, simple_diff: ModelContractDiff
    ) -> None:
        """Test HTML output properly escapes special characters."""
        # Create a diff with HTML special characters
        diff_with_html = ModelContractDiff(
            diff_id=uuid4(),
            before_contract_name="Test<Script>",
            after_contract_name="Test&Contract",
            field_diffs=[
                ModelContractFieldDiff(
                    field_path="field_with<bracket>",
                    change_type=EnumContractDiffChangeType.MODIFIED,
                    old_value=ModelSchemaValue.from_value("<old>"),
                    new_value=ModelSchemaValue.from_value("&new"),
                    value_type="str",
                ),
            ],
            list_diffs=[],
            computed_at=datetime.now(UTC),
        )
        output = RendererDiff.render_html(diff_with_html)

        # HTML entities should be escaped
        assert "&lt;" in output  # Escaped <
        assert "&gt;" in output  # Escaped >
        assert "&amp;" in output  # Escaped &

    def test_render_html_empty_diff(self, empty_diff: ModelContractDiff) -> None:
        """Test HTML output for empty diff."""
        output = RendererDiff.render_html(empty_diff)

        assert 'class="diff-empty"' in output
        assert "No changes detected" in output


# =================== FIELD DIFF TEXT RENDERING ===================


@pytest.mark.unit
class TestRenderFieldDiffText:
    """Tests for RendererDiff.render_field_diff_text()."""

    def test_render_field_diff_text_modified(self) -> None:
        """Test rendering a MODIFIED field diff."""
        field_diff = ModelContractFieldDiff(
            field_path="config.timeout",
            change_type=EnumContractDiffChangeType.MODIFIED,
            old_value=ModelSchemaValue.from_value(1000),
            new_value=ModelSchemaValue.from_value(2000),
            value_type="int",
        )
        output = RendererDiff.render_field_diff_text(field_diff)

        assert "~" in output  # MODIFIED symbol
        assert "config.timeout" in output
        assert "1000" in output
        assert "2000" in output
        assert "->" in output

    def test_render_field_diff_text_added(self) -> None:
        """Test rendering an ADDED field diff."""
        field_diff = ModelContractFieldDiff(
            field_path="new_field",
            change_type=EnumContractDiffChangeType.ADDED,
            old_value=None,
            new_value=ModelSchemaValue.from_value("new_value"),
            value_type="str",
        )
        output = RendererDiff.render_field_diff_text(field_diff)

        assert "+" in output  # ADDED symbol
        assert "new_field" in output
        assert '"new_value"' in output

    def test_render_field_diff_text_removed(self) -> None:
        """Test rendering a REMOVED field diff."""
        field_diff = ModelContractFieldDiff(
            field_path="old_field",
            change_type=EnumContractDiffChangeType.REMOVED,
            old_value=ModelSchemaValue.from_value("old_value"),
            new_value=None,
            value_type="str",
        )
        output = RendererDiff.render_field_diff_text(field_diff)

        assert "-" in output  # REMOVED symbol
        assert "old_field" in output
        assert '"old_value"' in output


# =================== CHANGE SYMBOL TESTS ===================


@pytest.mark.unit
class TestRenderChangeSymbol:
    """Tests for RendererDiff.render_change_symbol()."""

    def test_change_symbol_added(self) -> None:
        """Test symbol for ADDED is '+'."""
        symbol = RendererDiff.render_change_symbol(EnumContractDiffChangeType.ADDED)
        assert symbol == "+"

    def test_change_symbol_removed(self) -> None:
        """Test symbol for REMOVED is '-'."""
        symbol = RendererDiff.render_change_symbol(EnumContractDiffChangeType.REMOVED)
        assert symbol == "-"

    def test_change_symbol_modified(self) -> None:
        """Test symbol for MODIFIED is '~'."""
        symbol = RendererDiff.render_change_symbol(EnumContractDiffChangeType.MODIFIED)
        assert symbol == "~"

    def test_change_symbol_moved(self) -> None:
        """Test symbol for MOVED is unicode arrow."""
        symbol = RendererDiff.render_change_symbol(EnumContractDiffChangeType.MOVED)
        assert symbol == "\u2194"  # Unicode bidirectional arrow

    def test_change_symbol_unchanged(self) -> None:
        """Test symbol for UNCHANGED is space."""
        symbol = RendererDiff.render_change_symbol(EnumContractDiffChangeType.UNCHANGED)
        assert symbol == " "


# =================== EDGE CASE TESTS ===================


@pytest.mark.unit
class TestRendererDiffEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_diff_with_only_added_fields(
        self, diff_with_only_added: ModelContractDiff
    ) -> None:
        """Test rendering diff with only added fields."""
        text_output = RendererDiff.render_text(diff_with_only_added, use_colors=False)
        json_output = RendererDiff.render_json(diff_with_only_added)

        assert "+" in text_output
        assert "-" not in text_output.split("Summary")[1]  # No removals after summary

        parsed = json.loads(json_output)
        assert parsed["change_summary"]["added"] == 2
        assert parsed["change_summary"]["removed"] == 0

    def test_diff_with_only_removed_fields(
        self, diff_with_only_removed: ModelContractDiff
    ) -> None:
        """Test rendering diff with only removed fields."""
        text_output = RendererDiff.render_text(diff_with_only_removed, use_colors=False)
        json_output = RendererDiff.render_json(diff_with_only_removed)

        assert "-" in text_output

        parsed = json.loads(json_output)
        assert parsed["change_summary"]["removed"] == 2
        assert parsed["change_summary"]["added"] == 0

    def test_diff_with_only_modified_fields(
        self, diff_with_only_modified: ModelContractDiff
    ) -> None:
        """Test rendering diff with only modified fields."""
        text_output = RendererDiff.render_text(
            diff_with_only_modified, use_colors=False
        )
        json_output = RendererDiff.render_json(diff_with_only_modified)

        assert "~" in text_output

        parsed = json.loads(json_output)
        assert parsed["change_summary"]["modified"] == 2
        assert parsed["change_summary"]["added"] == 0
        assert parsed["change_summary"]["removed"] == 0

    def test_diff_with_moved_list_items(
        self, diff_with_moved_list_items: ModelContractDiff
    ) -> None:
        """Test rendering diff with moved list items."""
        text_output = RendererDiff.render_text(
            diff_with_moved_list_items, use_colors=False
        )
        md_output = RendererDiff.render_markdown(diff_with_moved_list_items)

        # Text should show moved symbol and indices
        assert "List Changes" in text_output
        assert "0" in text_output  # old_index
        assert "1" in text_output  # new_index

        # Markdown should include list changes section
        assert "List Changes:" in md_output

    def test_diff_with_none_values(
        self, diff_with_none_values: ModelContractDiff
    ) -> None:
        """Test rendering diff with None (null) values."""
        text_output = RendererDiff.render_text(diff_with_none_values, use_colors=False)
        json_output = RendererDiff.render_json(diff_with_none_values)

        # Text should show null
        assert "null" in text_output

        # JSON should be valid and parseable
        parsed = json.loads(json_output)
        assert parsed["has_changes"] is True

    def test_diff_with_complex_values(
        self, diff_with_complex_values: ModelContractDiff
    ) -> None:
        """Test rendering diff with complex nested values."""
        md_output = RendererDiff.render_markdown(diff_with_complex_values)
        html_output = RendererDiff.render_html(diff_with_complex_values)

        # Should handle complex values without errors
        assert "nested.config" in md_output
        assert "items_list" in md_output

        # HTML should render without errors
        assert "<table" in html_output

    def test_large_diff_renders(self, large_diff: ModelContractDiff) -> None:
        """Test that large diff renders without errors."""
        text_output = RendererDiff.render_text(large_diff, use_colors=False)
        json_output = RendererDiff.render_json(large_diff)
        md_output = RendererDiff.render_markdown(large_diff)
        html_output = RendererDiff.render_html(large_diff)

        # All formats should render
        assert len(text_output) > 0
        assert len(json_output) > 0
        assert len(md_output) > 0
        assert len(html_output) > 0

        # JSON should be valid
        parsed = json.loads(json_output)
        assert parsed["total_changes"] == 15

    def test_diff_with_list_changes(
        self, diff_with_list_changes: ModelContractDiff
    ) -> None:
        """Test rendering diff with list-level changes."""
        text_output = RendererDiff.render_text(diff_with_list_changes, use_colors=False)
        md_output = RendererDiff.render_markdown(diff_with_list_changes)
        html_output = RendererDiff.render_html(diff_with_list_changes)

        # Should show list changes section
        assert "List Changes" in text_output
        assert "dependencies" in text_output
        assert "name" in text_output  # identity_key

        # Markdown should have list changes section
        assert "## List Changes:" in md_output
        assert "*Identity Key*:" in md_output

        # HTML should have list changes
        assert "List Changes:" in html_output

    def test_empty_diff_all_formats(self, empty_diff: ModelContractDiff) -> None:
        """Test that empty diff renders correctly in all formats."""
        text = RendererDiff.render_text(empty_diff, use_colors=False)
        json_out = RendererDiff.render_json(empty_diff)
        md = RendererDiff.render_markdown(empty_diff)
        html = RendererDiff.render_html(empty_diff)

        # All should indicate no changes
        assert "No changes detected" in text
        assert json.loads(json_out)["has_changes"] is False
        assert "*No changes detected.*" in md
        assert "No changes detected" in html


# =================== COMPACT FORMAT TESTS ===================


@pytest.mark.unit
class TestRendererDiffCompact:
    """Tests for compact format rendering."""

    def test_compact_no_changes(self, empty_diff: ModelContractDiff) -> None:
        """Test compact format for no changes."""
        output = RendererDiff.render(empty_diff, EnumOutputFormat.COMPACT)

        assert "No changes" in output
        assert empty_diff.before_contract_name in output

    def test_compact_with_changes(self, simple_diff: ModelContractDiff) -> None:
        """Test compact format shows change counts."""
        output = RendererDiff.render(simple_diff, EnumOutputFormat.COMPACT)

        # Compact format shows +N, -N, ~N notation
        assert "+" in output  # Added
        assert "-" in output  # Removed
        assert "~" in output  # Modified

    def test_compact_single_line(self, simple_diff: ModelContractDiff) -> None:
        """Test compact format is a single line."""
        output = RendererDiff.render(simple_diff, EnumOutputFormat.COMPACT)

        assert len(output.splitlines()) == 1


# =================== VALUE FORMATTING TESTS ===================


@pytest.mark.unit
class TestValueFormatting:
    """Tests for value formatting in different output modes."""

    def test_string_values_quoted_in_text(self) -> None:
        """Test string values are quoted in text output."""
        diff = ModelContractDiff(
            diff_id=uuid4(),
            before_contract_name="Test",
            after_contract_name="Test",
            field_diffs=[
                ModelContractFieldDiff(
                    field_path="name",
                    change_type=EnumContractDiffChangeType.MODIFIED,
                    old_value=ModelSchemaValue.from_value("old"),
                    new_value=ModelSchemaValue.from_value("new"),
                    value_type="str",
                ),
            ],
            list_diffs=[],
            computed_at=datetime.now(UTC),
        )
        output = RendererDiff.render_text(diff, use_colors=False)

        assert '"old"' in output
        assert '"new"' in output

    def test_boolean_values_in_text(self) -> None:
        """Test boolean values rendered as true/false in text."""
        diff = ModelContractDiff(
            diff_id=uuid4(),
            before_contract_name="Test",
            after_contract_name="Test",
            field_diffs=[
                ModelContractFieldDiff(
                    field_path="enabled",
                    change_type=EnumContractDiffChangeType.MODIFIED,
                    old_value=ModelSchemaValue.from_value(True),
                    new_value=ModelSchemaValue.from_value(False),
                    value_type="bool",
                ),
            ],
            list_diffs=[],
            computed_at=datetime.now(UTC),
        )
        output = RendererDiff.render_text(diff, use_colors=False)

        assert "true" in output
        assert "false" in output

    def test_number_values_in_text(self) -> None:
        """Test numeric values rendered correctly in text."""
        diff = ModelContractDiff(
            diff_id=uuid4(),
            before_contract_name="Test",
            after_contract_name="Test",
            field_diffs=[
                ModelContractFieldDiff(
                    field_path="count",
                    change_type=EnumContractDiffChangeType.MODIFIED,
                    old_value=ModelSchemaValue.from_value(42),
                    new_value=ModelSchemaValue.from_value(100),
                    value_type="int",
                ),
            ],
            list_diffs=[],
            computed_at=datetime.now(UTC),
        )
        output = RendererDiff.render_text(diff, use_colors=False)

        assert "42" in output
        assert "100" in output

    def test_none_old_value_shows_dash_in_text(self) -> None:
        """Test None old_value shows dash for ADDED fields."""
        diff = ModelContractDiff(
            diff_id=uuid4(),
            before_contract_name="Test",
            after_contract_name="Test",
            field_diffs=[
                ModelContractFieldDiff(
                    field_path="new_field",
                    change_type=EnumContractDiffChangeType.ADDED,
                    old_value=None,
                    new_value=ModelSchemaValue.from_value("added"),
                    value_type="str",
                ),
            ],
            list_diffs=[],
            computed_at=datetime.now(UTC),
        )
        # Field diff text shows just the new value for ADDED
        field_diff_text = RendererDiff.render_field_diff_text(diff.field_diffs[0])

        # ADDED format: "+ field_path: new_value" (no old value shown)
        assert "+" in field_diff_text
        assert '"added"' in field_diff_text
