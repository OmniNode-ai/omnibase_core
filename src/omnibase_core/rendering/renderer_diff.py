"""
Contract Diff Renderer for Multi-Format Output.

Provides the RendererDiff class which renders contract diffs in various
formats including text, JSON, markdown, and HTML.

.. versionadded:: 0.6.0
    Added as part of Explainability Output: Diff Rendering (OMN-1149)
"""

import html as html_module
import json

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


class RendererDiff:
    """
    Static utility class for rendering contract diffs in multiple formats.

    This class provides methods to convert ModelContractDiff instances into
    various output formats for display, documentation, or programmatic use.

    Supported formats:
        - TEXT: Terminal-friendly output with optional ANSI colors
        - JSON: Machine-readable JSON for API responses
        - MARKDOWN: Rich formatting for documentation and PRs
        - HTML: Web-ready output for reports and dashboards

    All methods are static and stateless, making RendererDiff thread-safe
    for concurrent use from multiple threads.

    Example:
        >>> from omnibase_core.rendering import RendererDiff
        >>> from omnibase_core.enums import EnumOutputFormat
        >>>
        >>> # Using the main entry point
        >>> output = RendererDiff.render(diff, EnumOutputFormat.MARKDOWN)
        >>>
        >>> # Using format-specific methods
        >>> text_output = RendererDiff.render_text(diff, use_colors=True)
        >>> json_output = RendererDiff.render_json(diff, indent=4)

    Thread Safety:
        All methods are static and stateless. RendererDiff can be safely
        used from multiple threads concurrently.

    .. versionadded:: 0.6.0
        Added as part of Explainability Output: Diff Rendering (OMN-1149)
    """

    # ANSI color codes for terminal output
    _COLORS = {
        "reset": "\033[0m",
        "bold": "\033[1m",
        "red": "\033[91m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "cyan": "\033[96m",
        "gray": "\033[90m",
    }

    # Change type to color mapping
    _CHANGE_COLORS = {
        EnumContractDiffChangeType.ADDED: "green",
        EnumContractDiffChangeType.REMOVED: "red",
        EnumContractDiffChangeType.MODIFIED: "yellow",
        EnumContractDiffChangeType.MOVED: "cyan",
        EnumContractDiffChangeType.UNCHANGED: "gray",
    }

    # Change type symbols
    _CHANGE_SYMBOLS = {
        EnumContractDiffChangeType.ADDED: "+",
        EnumContractDiffChangeType.REMOVED: "-",
        EnumContractDiffChangeType.MODIFIED: "~",
        EnumContractDiffChangeType.MOVED: "\u2194",  # Unicode arrow
        EnumContractDiffChangeType.UNCHANGED: " ",
    }

    @staticmethod
    def render(
        diff: ModelContractDiff,
        output_format: EnumOutputFormat,
        options: ModelOutputFormatOptions | None = None,
    ) -> str:
        """
        Main entry point for rendering contract diffs.

        Routes to the appropriate format-specific method based on the
        requested output format.

        Args:
            diff: The contract diff to render.
            output_format: The output format to use.
            options: Optional formatting configuration.

        Returns:
            The rendered diff as a string in the specified format.

        Raises:
            ValueError: If the format is not supported.

        Example:
            >>> output = RendererDiff.render(diff, EnumOutputFormat.MARKDOWN)
        """
        format_handlers = {
            EnumOutputFormat.TEXT: lambda: RendererDiff.render_text(diff, options),
            EnumOutputFormat.JSON: lambda: RendererDiff.render_json(diff, options),
            EnumOutputFormat.MARKDOWN: lambda: RendererDiff.render_markdown(
                diff, options
            ),
            EnumOutputFormat.DETAILED: lambda: RendererDiff.render_text(
                diff, options, use_colors=False
            ),
            EnumOutputFormat.COMPACT: lambda: RendererDiff._render_compact(
                diff, options
            ),
        }

        handler = format_handlers.get(output_format)
        if handler is None:
            supported = ", ".join(f.value for f in format_handlers)
            msg = f"Unsupported output format: {output_format.value}. Supported: {supported}"
            # error-ok: standard ValueError for invalid enum input (cannot use OnexError in static utility)
            raise ValueError(msg)

        return handler()

    @staticmethod
    def render_text(
        diff: ModelContractDiff,
        options: ModelOutputFormatOptions | None = None,
        use_colors: bool = True,
    ) -> str:
        """
        Render diff as terminal-friendly text output.

        Produces human-readable output with optional ANSI color codes
        for terminal display. Uses symbols (+, -, ~) to indicate change types.

        Args:
            diff: The contract diff to render.
            options: Optional formatting configuration.
            use_colors: If True, include ANSI color codes for terminal display.
                       Defaults to True.

        Returns:
            Terminal-friendly text representation of the diff.

        Example:
            >>> print(RendererDiff.render_text(diff, use_colors=True))
            Contract Diff: MyContract v1.0.0 -> v2.0.0
            =============================================
            Summary: 5 changes (2 added, 1 removed, 2 modified)
            ...
        """
        lines: list[str] = []

        # Check color settings from options
        color_enabled = use_colors
        if options is not None and not options.color_enabled:
            color_enabled = False

        def colorize(text: str, color: str) -> str:
            if not color_enabled:
                return text
            return f"{RendererDiff._COLORS.get(color, '')}{text}{RendererDiff._COLORS['reset']}"

        # Header
        header = (
            f"Contract Diff: {diff.before_contract_name} -> {diff.after_contract_name}"
        )
        lines.append(colorize(header, "bold"))
        lines.append("=" * len(header))
        lines.append("")

        # Fingerprints (if available)
        if diff.before_fingerprint or diff.after_fingerprint:
            if diff.before_fingerprint:
                lines.append(f"Before Fingerprint: {diff.before_fingerprint}")
            if diff.after_fingerprint:
                lines.append(f"After Fingerprint:  {diff.after_fingerprint}")
            lines.append("")

        # Summary
        summary = diff.change_summary
        summary_parts = []
        if summary["added"] > 0:
            summary_parts.append(colorize(f"{summary['added']} added", "green"))
        if summary["removed"] > 0:
            summary_parts.append(colorize(f"{summary['removed']} removed", "red"))
        if summary["modified"] > 0:
            summary_parts.append(colorize(f"{summary['modified']} modified", "yellow"))
        if summary["moved"] > 0:
            summary_parts.append(colorize(f"{summary['moved']} moved", "cyan"))

        if summary_parts:
            lines.append(
                f"Summary: {diff.total_changes} changes ({', '.join(summary_parts)})"
            )
        else:
            lines.append(colorize("No changes detected.", "gray"))
        lines.append("")

        if not diff.has_changes:
            return "\n".join(lines)

        # Field Changes
        if diff.field_diffs:
            active_field_diffs = [
                fd
                for fd in diff.field_diffs
                if fd.change_type != EnumContractDiffChangeType.UNCHANGED
            ]
            if active_field_diffs:
                lines.append(colorize("Field Changes:", "bold"))
                for fd in active_field_diffs:
                    lines.append(
                        "  "
                        + RendererDiff._render_field_diff_text_line(fd, color_enabled)
                    )
                lines.append("")

        # List Changes
        for ld in diff.list_diffs:
            if ld.has_changes:
                lines.append(
                    colorize(
                        f"List Changes [{ld.field_path}] (identity: {ld.identity_key}):",
                        "bold",
                    )
                )
                for item in ld.get_all_field_diffs():
                    lines.append(
                        "  "
                        + RendererDiff._render_field_diff_text_line(item, color_enabled)
                    )
                lines.append("")

        return "\n".join(lines)

    @staticmethod
    def render_json(
        diff: ModelContractDiff,
        options: ModelOutputFormatOptions | None = None,
        indent: int = 2,
    ) -> str:
        """
        Render diff as machine-readable JSON.

        Uses Pydantic's model_dump for full fidelity serialization.
        Suitable for API responses and programmatic consumption.

        Args:
            diff: The contract diff to render.
            options: Optional formatting configuration. If provided,
                options.pretty_print controls whether indentation is applied.
            indent: JSON indentation level when pretty printing is enabled.
                Ignored when options.pretty_print is False. Defaults to 2.

        Returns:
            JSON string representation of the diff.

        Note:
            The indent parameter only applies when pretty printing is enabled
            (options.pretty_print=True or when options is None, which defaults
            to pretty=True). When options.pretty_print=False, compact JSON
            is returned regardless of the indent value.

        Example:
            >>> json_str = RendererDiff.render_json(diff, indent=4)
        """
        # Check options for pretty print settings
        pretty = True
        sort_keys = False
        if options is not None:
            pretty = options.pretty_print
            sort_keys = options.sort_keys

        data = diff.model_dump(mode="json")

        if pretty:
            # indent parameter only used when pretty printing
            return json.dumps(
                data, indent=indent, sort_keys=sort_keys, ensure_ascii=False
            )
        # Compact output ignores indent parameter
        return json.dumps(data, sort_keys=sort_keys, ensure_ascii=False)

    @staticmethod
    def render_markdown(
        diff: ModelContractDiff,
        options: ModelOutputFormatOptions | None = None,  # noqa: ARG004
    ) -> str:
        """
        Render diff as rich markdown format.

        Produces markdown suitable for documentation, pull requests,
        and other documentation systems. Includes:
        - Section headers
        - Summary statistics
        - Tables for field and list changes
        - Code block formatting for values
        - Collapsible sections for large diffs

        Args:
            diff: The contract diff to render.
            options: Optional formatting configuration (reserved for future use).

        Returns:
            Markdown formatted representation of the diff.

        Example:
            >>> md = RendererDiff.render_markdown(diff)
            >>> print(md)
            # Contract Diff: MyContract -> MyContract
            ...
        """
        lines: list[str] = []

        # Title
        lines.append(
            f"# Contract Diff: {diff.before_contract_name} -> {diff.after_contract_name}"
        )
        lines.append("")

        # Metadata section
        lines.append(f"**Computed At**: {diff.computed_at.isoformat()}")
        lines.append(f"**Diff ID**: `{diff.diff_id}`")
        lines.append("")

        # Fingerprints
        if diff.before_fingerprint or diff.after_fingerprint:
            lines.append("## Fingerprints")
            lines.append("")
            if diff.before_fingerprint:
                lines.append(f"- **Before**: `{diff.before_fingerprint}`")
            if diff.after_fingerprint:
                lines.append(f"- **After**: `{diff.after_fingerprint}`")
            lines.append("")

        # Summary
        summary = diff.change_summary
        lines.append("## Summary")
        lines.append("")
        lines.append(f"- **Total Changes**: {diff.total_changes}")
        lines.append(f"- **Added**: {summary['added']}")
        lines.append(f"- **Removed**: {summary['removed']}")
        lines.append(f"- **Modified**: {summary['modified']}")
        lines.append(f"- **Moved**: {summary['moved']}")
        lines.append("")

        if not diff.has_changes:
            lines.append("*No changes detected.*")
            return "\n".join(lines)

        # Field Changes
        active_field_diffs = [
            fd
            for fd in diff.field_diffs
            if fd.change_type != EnumContractDiffChangeType.UNCHANGED
        ]
        if active_field_diffs:
            lines.append("## Field Changes")
            lines.append("")

            # Use collapsible section for many changes
            use_collapsible = len(active_field_diffs) > 10

            if use_collapsible:
                lines.append(
                    f"<details><summary>Show {len(active_field_diffs)} field changes</summary>"
                )
                lines.append("")

            lines.append("| Change | Field Path | Old Value | New Value |")
            lines.append("|:------:|------------|-----------|-----------|")

            for fd in active_field_diffs:
                lines.append(RendererDiff._render_field_diff_markdown_row(fd))

            if use_collapsible:
                lines.append("")
                lines.append("</details>")

            lines.append("")

        # List Changes
        for ld in diff.list_diffs:
            if ld.has_changes:
                lines.append(f"## List Changes: `{ld.field_path}`")
                lines.append("")
                lines.append(f"*Identity Key*: `{ld.identity_key}`")
                lines.append("")

                all_items = ld.get_all_field_diffs()
                use_collapsible = len(all_items) > 10

                if use_collapsible:
                    lines.append(
                        f"<details><summary>Show {len(all_items)} element changes</summary>"
                    )
                    lines.append("")

                lines.append("| Change | Element | Old Value | New Value |")
                lines.append("|:------:|---------|-----------|-----------|")

                for item in all_items:
                    lines.append(RendererDiff._render_field_diff_markdown_row(item))

                if use_collapsible:
                    lines.append("")
                    lines.append("</details>")

                lines.append("")

        return "\n".join(lines)

    @staticmethod
    def render_html(
        diff: ModelContractDiff,
        options: ModelOutputFormatOptions | None = None,  # noqa: ARG004
        standalone: bool = False,
    ) -> str:
        """
        Render diff as HTML format.

        Produces HTML suitable for web reports and dashboards.
        Uses CSS classes for styling (diff-added, diff-removed, etc.)

        Args:
            diff: The contract diff to render.
            options: Optional formatting configuration (reserved for future use).
            standalone: If True, include inline CSS for self-contained output.
                       Defaults to False.

        Returns:
            HTML representation of the diff.

        Example:
            >>> html_output = RendererDiff.render_html(diff, standalone=True)
            >>> with open("diff.html", "w") as f:
            ...     f.write(html_output)
        """
        lines: list[str] = []

        # Inline CSS for standalone mode
        css = """
<style>
.diff-container { font-family: system-ui, -apple-system, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; }
.diff-header { border-bottom: 2px solid #333; padding-bottom: 10px; margin-bottom: 20px; }
.diff-header h1 { margin: 0; color: #333; }
.diff-meta { color: #666; font-size: 0.9em; }
.diff-summary { background: #f5f5f5; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
.diff-summary ul { margin: 0; padding-left: 20px; }
.diff-section { margin-bottom: 30px; }
.diff-section h2 { color: #444; border-bottom: 1px solid #ddd; padding-bottom: 5px; }
.diff-table { width: 100%; border-collapse: collapse; font-size: 0.9em; }
.diff-table th { background: #f0f0f0; text-align: left; padding: 10px; border: 1px solid #ddd; }
.diff-table td { padding: 10px; border: 1px solid #ddd; vertical-align: top; }
.diff-table tr:hover { background: #fafafa; }
.diff-added { color: #22863a; }
.diff-added td:first-child { border-left: 3px solid #22863a; }
.diff-removed { color: #cb2431; }
.diff-removed td:first-child { border-left: 3px solid #cb2431; }
.diff-modified { color: #b08800; }
.diff-modified td:first-child { border-left: 3px solid #b08800; }
.diff-moved { color: #0366d6; }
.diff-moved td:first-child { border-left: 3px solid #0366d6; }
.diff-symbol { font-weight: bold; font-size: 1.2em; width: 30px; text-align: center; }
.diff-value { font-family: 'SFMono-Regular', Consolas, monospace; background: #f6f8fa; padding: 2px 5px; border-radius: 3px; }
.diff-empty { color: #999; font-style: italic; }
.diff-fingerprint { font-family: monospace; font-size: 0.85em; }
</style>
"""

        if standalone:
            lines.append("<!DOCTYPE html>")
            lines.append('<html lang="en">')
            lines.append("<head>")
            lines.append('<meta charset="UTF-8">')
            before_name = html_module.escape(diff.before_contract_name)
            after_name = html_module.escape(diff.after_contract_name)
            lines.append(f"<title>Contract Diff: {before_name} -> {after_name}</title>")
            lines.append(css)
            lines.append("</head>")
            lines.append("<body>")

        lines.append('<div class="diff-container">')

        # Header
        lines.append('<div class="diff-header">')
        before_name = html_module.escape(diff.before_contract_name)
        after_name = html_module.escape(diff.after_contract_name)
        lines.append(f"<h1>Contract Diff: {before_name} -> {after_name}</h1>")
        lines.append(
            f'<p class="diff-meta">Computed: {diff.computed_at.isoformat()} | '
            f"ID: <code>{diff.diff_id}</code></p>"
        )
        lines.append("</div>")

        # Fingerprints
        if diff.before_fingerprint or diff.after_fingerprint:
            lines.append('<div class="diff-section">')
            lines.append("<h2>Fingerprints</h2>")
            lines.append("<ul>")
            if diff.before_fingerprint:
                fp_escaped = html_module.escape(str(diff.before_fingerprint))
                lines.append(
                    f'<li><strong>Before:</strong> <code class="diff-fingerprint">'
                    f"{fp_escaped}</code></li>"
                )
            if diff.after_fingerprint:
                fp_escaped = html_module.escape(str(diff.after_fingerprint))
                lines.append(
                    f'<li><strong>After:</strong> <code class="diff-fingerprint">'
                    f"{fp_escaped}</code></li>"
                )
            lines.append("</ul>")
            lines.append("</div>")

        # Summary
        summary = diff.change_summary
        lines.append('<div class="diff-summary">')
        lines.append("<h2>Summary</h2>")
        lines.append("<ul>")
        lines.append(f"<li><strong>Total Changes:</strong> {diff.total_changes}</li>")
        lines.append(
            f'<li><span class="diff-added">Added:</span> {summary["added"]}</li>'
        )
        lines.append(
            f'<li><span class="diff-removed">Removed:</span> {summary["removed"]}</li>'
        )
        lines.append(
            f'<li><span class="diff-modified">Modified:</span> {summary["modified"]}</li>'
        )
        lines.append(
            f'<li><span class="diff-moved">Moved:</span> {summary["moved"]}</li>'
        )
        lines.append("</ul>")
        lines.append("</div>")

        if not diff.has_changes:
            lines.append('<p class="diff-empty">No changes detected.</p>')
        else:
            # Field Changes
            active_field_diffs = [
                fd
                for fd in diff.field_diffs
                if fd.change_type != EnumContractDiffChangeType.UNCHANGED
            ]
            if active_field_diffs:
                lines.append('<div class="diff-section">')
                lines.append("<h2>Field Changes</h2>")
                lines.append(RendererDiff._render_html_table(active_field_diffs))
                lines.append("</div>")

            # List Changes
            for ld in diff.list_diffs:
                if ld.has_changes:
                    lines.append('<div class="diff-section">')
                    field_path_escaped = html_module.escape(ld.field_path)
                    lines.append(
                        f"<h2>List Changes: <code>{field_path_escaped}</code></h2>"
                    )
                    identity_key_escaped = html_module.escape(ld.identity_key)
                    lines.append(
                        f"<p><em>Identity Key:</em> <code>{identity_key_escaped}</code></p>"
                    )
                    lines.append(
                        RendererDiff._render_html_table(ld.get_all_field_diffs())
                    )
                    lines.append("</div>")

        lines.append("</div>")  # diff-container

        if standalone:
            lines.append("</body>")
            lines.append("</html>")

        return "\n".join(lines)

    @staticmethod
    def render_field_diff_text(field_diff: ModelContractFieldDiff) -> str:
        """
        Render a single field diff as text.

        Low-level helper for rendering individual field diffs without colors.

        Args:
            field_diff: The field diff to render.

        Returns:
            Single-line text representation of the field diff.

        Example:
            >>> line = RendererDiff.render_field_diff_text(field_diff)
            >>> print(line)
            ~ meta.name: "OldName" -> "NewName"
        """
        return RendererDiff._render_field_diff_text_line(field_diff, use_colors=False)

    @staticmethod
    def render_change_symbol(change_type: EnumContractDiffChangeType) -> str:
        """
        Get the symbol for a change type.

        Returns the standard symbol used to represent each change type:
        - '+' for ADDED
        - '-' for REMOVED
        - '~' for MODIFIED
        - (unicode arrow) for MOVED
        - ' ' for UNCHANGED

        Args:
            change_type: The change type to get the symbol for.

        Returns:
            Single character symbol for the change type.

        Example:
            >>> RendererDiff.render_change_symbol(EnumContractDiffChangeType.ADDED)
            '+'
        """
        return RendererDiff._CHANGE_SYMBOLS.get(change_type, "?")

    # =========================================================================
    # Private helper methods
    # =========================================================================

    @staticmethod
    def _render_compact(
        diff: ModelContractDiff,
        options: ModelOutputFormatOptions | None = None,  # noqa: ARG004
    ) -> str:
        """Render a compact summary of the diff."""
        if not diff.has_changes:
            return f"{diff.before_contract_name}: No changes"

        summary = diff.change_summary
        parts = []
        if summary["added"] > 0:
            parts.append(f"+{summary['added']}")
        if summary["removed"] > 0:
            parts.append(f"-{summary['removed']}")
        if summary["modified"] > 0:
            parts.append(f"~{summary['modified']}")
        if summary["moved"] > 0:
            parts.append(f">{summary['moved']}")

        return f"{diff.before_contract_name}: {' '.join(parts)}"

    @staticmethod
    def _render_field_diff_text_line(
        field_diff: ModelContractFieldDiff,
        use_colors: bool = False,
    ) -> str:
        """Render a single field diff as a text line with optional colors."""
        symbol = RendererDiff._CHANGE_SYMBOLS.get(field_diff.change_type, "?")

        # Format values
        old_val = RendererDiff._format_value_for_text(field_diff.old_value)
        new_val = RendererDiff._format_value_for_text(field_diff.new_value)

        # Build the line
        if field_diff.change_type == EnumContractDiffChangeType.ADDED:
            line = f"{symbol} {field_diff.field_path}: {new_val}"
        elif field_diff.change_type == EnumContractDiffChangeType.REMOVED:
            line = f"{symbol} {field_diff.field_path}: {old_val}"
        elif field_diff.change_type == EnumContractDiffChangeType.MOVED:
            line = f"{symbol} {field_diff.field_path}: [{field_diff.old_index} -> {field_diff.new_index}]"
        else:
            line = f"{symbol} {field_diff.field_path}: {old_val} -> {new_val}"

        # Apply color if enabled
        if use_colors:
            color = RendererDiff._CHANGE_COLORS.get(field_diff.change_type, "reset")
            color_code = RendererDiff._COLORS.get(color, "")
            reset = RendererDiff._COLORS["reset"]
            return f"{color_code}{line}{reset}"

        return line

    @staticmethod
    def _render_field_diff_markdown_row(field_diff: ModelContractFieldDiff) -> str:
        """Render a single field diff as a markdown table row."""
        symbol = RendererDiff._CHANGE_SYMBOLS.get(field_diff.change_type, "?")

        # Format values with code blocks
        old_val = RendererDiff._format_value_for_markdown(field_diff.old_value)
        new_val = RendererDiff._format_value_for_markdown(field_diff.new_value)

        # Add move info if applicable
        field_path = field_diff.field_path
        if field_diff.change_type == EnumContractDiffChangeType.MOVED:
            field_path = (
                f"{field_path} ({field_diff.old_index}->{field_diff.new_index})"
            )

        return f"| {symbol} | `{field_path}` | {old_val} | {new_val} |"

    @staticmethod
    def _render_html_table(field_diffs: list[ModelContractFieldDiff]) -> str:
        """Render a list of field diffs as an HTML table."""
        lines: list[str] = []
        lines.append('<table class="diff-table">')
        lines.append("<thead><tr>")
        lines.append('<th class="diff-symbol">Change</th>')
        lines.append("<th>Field Path</th>")
        lines.append("<th>Old Value</th>")
        lines.append("<th>New Value</th>")
        lines.append("</tr></thead>")
        lines.append("<tbody>")

        for fd in field_diffs:
            css_class = RendererDiff._get_html_class(fd.change_type)
            symbol = html_module.escape(
                RendererDiff._CHANGE_SYMBOLS.get(fd.change_type, "?")
            )
            field_path = html_module.escape(fd.field_path)

            # Add move info
            if fd.change_type == EnumContractDiffChangeType.MOVED:
                field_path = f"{field_path} <em>({fd.old_index} -> {fd.new_index})</em>"

            old_val = RendererDiff._format_value_for_html(fd.old_value)
            new_val = RendererDiff._format_value_for_html(fd.new_value)

            lines.append(f'<tr class="{css_class}">')
            lines.append(f'<td class="diff-symbol">{symbol}</td>')
            lines.append(f"<td><code>{field_path}</code></td>")
            lines.append(f"<td>{old_val}</td>")
            lines.append(f"<td>{new_val}</td>")
            lines.append("</tr>")

        lines.append("</tbody>")
        lines.append("</table>")

        return "\n".join(lines)

    @staticmethod
    def _get_html_class(change_type: EnumContractDiffChangeType) -> str:
        """Get the CSS class for a change type."""
        class_map = {
            EnumContractDiffChangeType.ADDED: "diff-added",
            EnumContractDiffChangeType.REMOVED: "diff-removed",
            EnumContractDiffChangeType.MODIFIED: "diff-modified",
            EnumContractDiffChangeType.MOVED: "diff-moved",
            EnumContractDiffChangeType.UNCHANGED: "",
        }
        return class_map.get(change_type, "")

    @staticmethod
    def _format_value_for_text(value: ModelSchemaValue | None) -> str:
        """Format a ModelSchemaValue for text display."""
        if value is None:
            return "-"
        # ModelSchemaValue has a to_value() method
        python_value = value.to_value()

        if python_value is None:
            return "null"
        if isinstance(python_value, str):
            return f'"{python_value}"'
        if isinstance(python_value, bool):
            return "true" if python_value else "false"
        return str(python_value)

    @staticmethod
    def _format_value_for_markdown(value: ModelSchemaValue | None) -> str:
        """Format a ModelSchemaValue for markdown display.

        Note:
            Values are HTML-escaped as defense-in-depth against markdown
            processors that don't properly handle code spans.
        """
        if value is None:
            return "-"
        python_value = value.to_value()

        if python_value is None:
            return "`null`"
        if isinstance(python_value, str):
            # Escape HTML chars first (defense-in-depth), then markdown pipe
            escaped = html_module.escape(python_value).replace("|", "\\|")
            return f'`"{escaped}"`'
        if isinstance(python_value, bool):
            return "`true`" if python_value else "`false`"
        if isinstance(python_value, (dict, list)):
            # For complex values, show truncated JSON
            json_str = json.dumps(python_value)
            if len(json_str) > 50:
                json_str = json_str[:47] + "..."
            # HTML escape JSON content
            return f"`{html_module.escape(json_str)}`"
        return f"`{html_module.escape(str(python_value))}`"

    @staticmethod
    def _format_value_for_html(value: ModelSchemaValue | None) -> str:
        """Format a ModelSchemaValue for HTML display."""
        if value is None:
            return '<span class="diff-empty">-</span>'
        python_value = value.to_value()

        if python_value is None:
            return '<code class="diff-value">null</code>'
        if isinstance(python_value, str):
            escaped = html_module.escape(python_value)
            return f'<code class="diff-value">"{escaped}"</code>'
        if isinstance(python_value, bool):
            val_str = "true" if python_value else "false"
            return f'<code class="diff-value">{val_str}</code>'
        if isinstance(python_value, (dict, list)):
            json_str = json.dumps(python_value)
            if len(json_str) > 50:
                json_str = json_str[:47] + "..."
            return f'<code class="diff-value">{html_module.escape(json_str)}</code>'
        return (
            f'<code class="diff-value">{html_module.escape(str(python_value))}</code>'
        )


__all__ = ["RendererDiff"]
