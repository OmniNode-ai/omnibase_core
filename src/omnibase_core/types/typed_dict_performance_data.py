# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Typed structure for performance data updates.
"""

from __future__ import annotations

from typing import TypedDict


class TypedDictPerformanceData(TypedDict, total=False):
    average_execution_time_ms: float
    peak_memory_usage_mb: float
    total_invocations: int


__all__ = ["TypedDictPerformanceData"]
