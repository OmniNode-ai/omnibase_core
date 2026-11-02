# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Closed disposition vocabulary for completed view renders (OMN-21999).

A completed render states whether the app drew the view and whether a typed
empty-state cause accompanies that disposition.
"""

from enum import StrEnum

__all__ = ["EnumViewRenderDisposition"]


class EnumViewRenderDisposition(StrEnum):
    """Disposition of a completed attempt to render a view document."""

    DRAWN = "drawn"
    """The view was drawn without an empty-state cause."""

    DRAWN_WITH_CAUSE = "drawn-with-cause"
    """The view was drawn with a typed empty-state cause."""

    REFUSED = "refused"
    """The app refused to draw the view with a typed cause."""
