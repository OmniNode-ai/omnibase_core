# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Accessibility tier a renderer advertises (OMN-13130).

Mirrors WCAG conformance levels. A renderer declares the accessibility tier it
guarantees so a UI component contract requiring a tier is only routed to
renderers that meet or exceed it.
"""

from enum import StrEnum

__all__ = ["EnumAccessibilityTier"]


class EnumAccessibilityTier(StrEnum):
    """WCAG-aligned accessibility conformance tier."""

    A = "a"
    """WCAG level A."""

    AA = "aa"
    """WCAG level AA."""

    AAA = "aaa"
    """WCAG level AAA."""
