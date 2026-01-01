# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
TypedDict for provider attribute values used in capability resolution.

This type represents the merged attributes and features from a provider
that are used for constraint checking and scoring during resolution.

.. versionadded:: 0.4.0
"""

from __future__ import annotations

__all__ = ["TypedDictProviderAttributeValue"]

# Provider attribute values can be strings, booleans, ints, floats, or None
# This is the union of all valid attribute value types
TypedDictProviderAttributeValue = str | bool | int | float | None
