"""
Protocol for service registration metadata objects.

This module provides the ProtocolServiceRegistrationMetadata protocol which
contains comprehensive metadata about a registered service including
identification, versioning, and configuration.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable
from uuid import UUID

from omnibase_core.protocols.base import ContextValue, ProtocolDateTime, ProtocolSemVer


@runtime_checkable
class ProtocolServiceRegistrationMetadata(Protocol):
    """
    Protocol for service registration metadata objects.

    Contains comprehensive metadata about a registered service including
    identification, versioning, and configuration.
    """

    service_id: UUID
    service_name: str
    service_interface: str
    service_implementation: str
    version: ProtocolSemVer
    description: str | None
    tags: list[str]
    configuration: dict[str, ContextValue]
    created_at: ProtocolDateTime
    last_modified_at: ProtocolDateTime | None


__all__ = ["ProtocolServiceRegistrationMetadata"]
