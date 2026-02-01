"""
TypedDict for service information.
"""

from __future__ import annotations

from typing import NotRequired, TypedDict

from .typed_dict_sem_ver import TypedDictSemVer


class TypedDictServiceInfo(TypedDict):
    service_name: str
    service_version: TypedDictSemVer
    status: str  # See EnumMCPStatus for related values: RUNNING, ERROR, etc.
    port: NotRequired[int]
    host: NotRequired[str]
    health_check_url: NotRequired[str]


__all__ = ["TypedDictServiceInfo"]
