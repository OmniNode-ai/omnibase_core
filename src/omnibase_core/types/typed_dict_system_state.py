"""
TypedDict for overall system state.
"""

from __future__ import annotations

from typing import TypedDict
from uuid import UUID

from .typed_dict_dependency_info import TypedDictDependencyInfo
from .typed_dict_sem_ver import TypedDictSemVer
from .typed_dict_service_info import TypedDictServiceInfo
from .typed_dict_stats_collection import TypedDictStatsCollection


class TypedDictSystemState(TypedDict):
    system_id: UUID
    system_name: str
    version: TypedDictSemVer
    environment: str
    status: str
    stats: TypedDictStatsCollection
    services: list[TypedDictServiceInfo]
    dependencies: list[TypedDictDependencyInfo]


__all__ = ["TypedDictSystemState"]
