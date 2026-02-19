# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Enum for mock strategy classifications.

Defines the strategy used for mocking dependencies in test and
stub contexts for ticket-driven workflows [OMN-1968].
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumMockStrategy(StrValueHelper, str, Enum):
    """Strategy for mocking interface dependencies."""

    PROTOCOL_STUB = "protocol_stub"
    FIXTURE_DATA = "fixture_data"
    IN_MEMORY = "in_memory"
    NONE = "none"


# Alias for cleaner imports
MockStrategy = EnumMockStrategy

__all__ = [
    "EnumMockStrategy",
    "MockStrategy",
]
