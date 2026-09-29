# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Directions for resolved bus topic bindings."""

from enum import Enum


class EnumBusBindingDirection(str, Enum):
    """Whether a principal consumes from or produces to a topic."""

    CONSUME = "consume"
    PRODUCE = "produce"


__all__ = ["EnumBusBindingDirection"]
