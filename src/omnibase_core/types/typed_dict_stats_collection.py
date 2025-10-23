from __future__ import annotations

"""
TypedDict for collections of statistics.
"""

from datetime import datetime
from typing import TypedDict

from .typed_dict_execution_stats import TypedDictExecutionStats
from .typed_dict_health_status import TypedDictHealthStatus
from .typed_dict_resource_usage import TypedDictResourceUsage


class TypedDictStatsCollection(TypedDict):
    """TypedDict for collections of statistics."""

    execution_stats: TypedDictExecutionStats
    health_status: TypedDictHealthStatus
    resource_usage: TypedDictResourceUsage
    last_updated: datetime
