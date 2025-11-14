"""
UUID Service - Centralized UUID generation and validation.

Provides consistent UUID generation across the ONEX system.
"""

from uuid import UUID, uuid4


class UtilUUID:
    """Centralized UUID generation and validation utility."""

    @staticmethod
    def generate() -> UUID:
        """Generate a new UUID4."""
        return uuid4()

    @staticmethod
    def generate_str() -> str:
        """Generate a new UUID4 as string."""
        return str(uuid4())

    @staticmethod
    def is_valid(uuid_string: str) -> bool:
        """Check if a string is a valid UUID."""
        try:
            UUID(uuid_string)
            return True
        except (ValueError, TypeError):
            return False

    @staticmethod
    def parse(uuid_string: str) -> UUID | None:
        """Parse a UUID string, return None if invalid."""
        try:
            return UUID(uuid_string)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def generate_correlation_id() -> UUID:
        """Generate a correlation ID (UUID4)."""
        return uuid4()

    @staticmethod
    def ensure_uuid(value: UUID | str | None) -> UUID:
        """Ensure value is a UUID, generate if None or invalid."""
        if value is None:
            return uuid4()
        if isinstance(value, UUID):
            return value
        if isinstance(value, str):
            try:
                return UUID(value)
            except (ValueError, TypeError):
                return uuid4()
        return uuid4()  # type: ignore[unreachable]  # Defensive fallback

    @staticmethod
    def from_string(uuid_string: str) -> UUID:
        """Parse UUID from string, raise exception if invalid."""
        return UUID(uuid_string)

    @staticmethod
    def generate_event_id() -> UUID:
        """Generate an event ID (UUID4)."""
        return uuid4()

    @staticmethod
    def generate_session_id() -> UUID:
        """Generate a session ID (UUID4)."""
        return uuid4()
