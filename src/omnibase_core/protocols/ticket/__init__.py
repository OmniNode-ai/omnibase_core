"""
Protocol definitions for ticket-work automation.

This module provides protocol interfaces for ticket-work automation
dependencies including Linear API client, file system operations,
and notification delivery.
"""

from omnibase_core.protocols.ticket.protocol_ticket_dependencies import (
    ProtocolFileSystem,
    ProtocolLinearClient,
    ProtocolNotification,
)

__all__ = [
    "ProtocolFileSystem",
    "ProtocolLinearClient",
    "ProtocolNotification",
]
