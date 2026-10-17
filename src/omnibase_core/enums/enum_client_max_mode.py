# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""A host's client-section maximum mode (OMN-18531; relocated from omnimarket by OMN-21093)."""

from enum import StrEnum


class EnumClientMaxMode(StrEnum):
    """The most the server may do for a host: observe, run selectively, or require delegation."""

    OBSERVE = "observe"
    SELECTIVE = "selective"
    REQUIRED = "required"
