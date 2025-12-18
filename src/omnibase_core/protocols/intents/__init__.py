"""
Intent-related protocols for the ONEX framework.

This module provides protocol definitions for intent-related contracts,
including registration records used with PostgreSQL upsert intents.

Protocols:
    ProtocolRegistrationRecord: Contract for registration records that can
        be persisted via ModelPostgresUpsertRegistrationIntent.

Usage:
    >>> from omnibase_core.protocols.intents import ProtocolRegistrationRecord
    >>> from pydantic import BaseModel
    >>>
    >>> class NodeRegistrationRecord(BaseModel):
    ...     '''Custom registration record implementing the protocol.'''
    ...     node_id: str
    ...     node_type: str
    ...     status: str
    ...
    ...     def to_persistence_dict(self) -> dict[str, object]:
    ...         return self.model_dump(mode="json")
    >>>
    >>> # Type checker validates protocol compliance
    >>> record: ProtocolRegistrationRecord = NodeRegistrationRecord(
    ...     node_id="compute-123",
    ...     node_type="compute",
    ...     status="active",
    ... )
"""

from omnibase_core.protocols.intents.protocol_registration_record import (
    ProtocolRegistrationRecord,
)

__all__ = [
    "ProtocolRegistrationRecord",
]
