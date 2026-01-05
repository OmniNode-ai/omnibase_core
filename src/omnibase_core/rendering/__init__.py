# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
Rendering utilities for ONEX contract and diff visualization.

This module provides formatters and renderers for converting ONEX
data structures into human-readable and machine-readable formats.

Components:
    RendererDiff:
        Static utility class for rendering contract diffs in multiple
        formats (text, JSON, markdown, HTML).

Example:
    >>> from omnibase_core.rendering import RendererDiff
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

.. versionadded:: 0.6.0
    Added as part of Explainability Output: Diff Rendering (OMN-1149)
"""

from omnibase_core.rendering.renderer_diff import RendererDiff

__all__ = [
    "RendererDiff",
]
