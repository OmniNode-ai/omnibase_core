# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""TypedDict for a single metric entry in MixinMetrics."""

from __future__ import annotations

from typing import NotRequired, TypedDict


class TypedDictMetricEntry(TypedDict):
    """TypedDict for a single metric entry in MixinMetrics."""

    value: float
    tags: NotRequired[dict[str, str]]


__all__ = ["TypedDictMetricEntry"]
