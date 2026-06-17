# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Interaction model a renderer advertises (OMN-13130).

A renderer declares how a user interacts with it so the capability registry can
route a UI component contract only to renderers whose interaction model can
express it (e.g. a voice renderer cannot express pointer drag).
"""

from enum import StrEnum

__all__ = ["EnumRendererInteractionModel"]


class EnumRendererInteractionModel(StrEnum):
    """How a user interacts with a renderer."""

    POINTER = "pointer"
    """Pointer/mouse-driven (web desktop dashboards)."""

    TOUCH = "touch"
    """Touch-driven (mobile/tablet)."""

    KEYBOARD = "keyboard"
    """Keyboard-driven (CLI / TUI)."""

    VOICE = "voice"
    """Voice-driven (conversational renderers)."""
