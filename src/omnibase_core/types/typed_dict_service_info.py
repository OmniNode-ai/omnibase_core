from __future__ import annotations

"""
TypedDict for service information.
"""


from typing import NotRequired, TypedDict

from .typed_dict_sem_ver import TypedDictSemVer


class TypedDictServiceInfo(TypedDict):
    """TypedDict for service information."""

    service_name: str
    service_version: TypedDictSemVer
    status: str  # See EnumMcpStatus for related values: RUNNING, ERROR, etc.
    port: NotRequired[int]
    host: NotRequired[str]
    health_check_url: NotRequired[str]


__all__ = ["TypedDictServiceInfo"]
