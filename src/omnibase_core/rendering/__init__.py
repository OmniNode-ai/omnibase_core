"""
Rendering utilities for ONEX contract and diff visualization.

This module provides formatters and renderers for converting ONEX
data structures into human-readable and machine-readable formats.

Components:
    RendererDiff:
        Static utility class for rendering contract diffs in multiple
        formats (text, JSON, markdown, HTML).

    RendererReportCli:
        Static utility class for rendering evidence reports to CLI format
        with configurable verbosity levels.

    RendererReportHtml:
        Static utility class for rendering evidence summaries to standalone
        HTML with inline CSS for dashboards and web views.

    RendererReportJson:
        Static utility class for rendering evidence summaries to JSON
        format for API responses, storage, or further processing.

    RendererReportMarkdown:
        Static utility class for rendering evidence summaries to
        GitHub-flavored markdown for PRs and documentation.

Example:
    >>> from omnibase_core.rendering import (
    ...     RendererDiff,
    ...     RendererReportCli,
    ...     RendererReportHtml,
    ...     RendererReportJson,
    ...     RendererReportMarkdown,
    ... )
    >>> from omnibase_core.enums import EnumOutputFormat
    >>>
    >>> # Render diff as markdown
    >>> markdown = RendererDiff.render(diff, EnumOutputFormat.MARKDOWN)
    >>>
    >>> # Render with colors for terminal
    >>> text = RendererDiff.render_text(diff, use_colors=True)
    >>>
    >>> # Render as JSON
    >>> json_str = RendererDiff.render_json(diff, indent=2)
    >>>
    >>> # Render evidence report to CLI
    >>> cli_report = RendererReportCli.render(summary, comparisons, recommendation)
    >>>
    >>> # Render evidence summary to JSON
    >>> report = RendererReportJson.render(summary, comparisons, recommendation)
    >>> json_str = RendererReportJson.serialize(report)
    >>>
    >>> # Render evidence summary to markdown
    >>> md_report = RendererReportMarkdown.render(summary, comparisons, recommendation)
    >>>
    >>> # Render evidence summary to HTML
    >>> html_report = RendererReportHtml.render(summary, comparisons, recommendation)

.. versionadded:: 0.6.0
    Added as part of Explainability Output: Diff Rendering (OMN-1149)

.. versionadded:: 0.6.5
    Added RendererReportCli, RendererReportHtml, RendererReportJson,
    and RendererReportMarkdown as part of OMN-1200.
"""

from omnibase_core.rendering.renderer_diff import RendererDiff
from omnibase_core.rendering.renderer_report_cli import (
    COMPARISON_LIMIT_CLI_VERBOSE,
    COST_NA_CLI,
    ELLIPSIS,
    ELLIPSIS_LENGTH,
    PERCENTAGE_MULTIPLIER,
    REPORT_WIDTH,
    SEPARATOR_CHAR,
    SEPARATOR_LINE,
    SUBSECTION_CHAR,
    UUID_DISPLAY_LENGTH,
    RendererReportCli,
)
from omnibase_core.rendering.renderer_report_html import CSS_COLORS, RendererReportHtml
from omnibase_core.rendering.renderer_report_json import (
    JSON_INDENT_SPACES,
    REPORT_VERSION,
    RendererReportJson,
)
from omnibase_core.rendering.renderer_report_markdown import RendererReportMarkdown

__all__ = [
    "COMPARISON_LIMIT_CLI_VERBOSE",
    "COST_NA_CLI",
    "CSS_COLORS",
    "ELLIPSIS",
    "ELLIPSIS_LENGTH",
    "JSON_INDENT_SPACES",
    "PERCENTAGE_MULTIPLIER",
    "REPORT_VERSION",
    "REPORT_WIDTH",
    "RendererDiff",
    "RendererReportCli",
    "RendererReportHtml",
    "RendererReportJson",
    "RendererReportMarkdown",
    "SEPARATOR_CHAR",
    "SEPARATOR_LINE",
    "SUBSECTION_CHAR",
    "UUID_DISPLAY_LENGTH",
]
