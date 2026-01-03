"""
Infrastructure protocols for database and service discovery.

This module provides protocols for infrastructure-level concerns:
- Database connections with async lifecycle and transaction support
- Service discovery for distributed deployments

Design Principles:
- Use typing.Protocol with @runtime_checkable for duck typing support
- Keep interfaces minimal - only define what ONEX Core actually needs
- Provide complete type hints for mypy strict mode compliance
- Support async operations for production deployments

Usage:
    from omnibase_core.protocols.infrastructure import (
        ProtocolDatabaseConnection,
        ProtocolServiceDiscovery,
    )
"""

from omnibase_core.protocols.infrastructure.protocol_database_connection import (
    ProtocolDatabaseConnection,
)
from omnibase_core.protocols.infrastructure.protocol_service_discovery import (
    ProtocolServiceDiscovery,
)

__all__ = [
    "ProtocolDatabaseConnection",
    "ProtocolServiceDiscovery",
]
