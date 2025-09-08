"""
UUID Service Protocol.

Protocol definition for UUID generation and validation services.
"""

from typing import Any, Optional, Protocol
from uuid import UUID


class ProtocolUUIDService(Protocol):
    """Protocol for UUID generation and validation services."""

    @staticmethod
    def generate() -> UUID:
        """Generate a new UUID4."""
        ...

    @staticmethod
    def generate_str() -> str:
        """Generate a new UUID4 as string."""
        ...

    @staticmethod
    def is_valid(uuid_string: str) -> bool:
        """Check if a string is a valid UUID."""
        ...

    @staticmethod
    def parse(uuid_string: str) -> Optional[UUID]:
        """Parse a UUID string, return None if invalid."""
        ...

    @staticmethod
    def generate_correlation_id() -> UUID:
        """Generate a correlation ID (UUID4)."""
        ...

    @staticmethod
    def ensure_uuid(value: Any) -> UUID:
        """Ensure value is a UUID, generate if None or invalid."""
        ...

    @staticmethod
    def from_string(uuid_string: str) -> UUID:
        """Parse UUID from string, raise exception if invalid."""
        ...

    @staticmethod
    def generate_event_id() -> UUID:
        """Generate an event ID (UUID4)."""
        ...

    @staticmethod
    def generate_session_id() -> UUID:
        """Generate a session ID (UUID4)."""
        ...