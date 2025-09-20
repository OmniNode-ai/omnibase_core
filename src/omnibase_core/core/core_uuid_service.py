"""
Simplified UUID Service stub for import compatibility.
"""

import uuid
from uuid import UUID


class UUIDService:
    """Simplified UUID service for basic functionality."""

    @staticmethod
    def generate() -> str:
        """Generate a new UUID."""
        return str(uuid.uuid4())

    @staticmethod
    def generate_short() -> str:
        """Generate a short UUID."""
        return str(uuid.uuid4())[:8]

    @staticmethod
    def generate_correlation_id() -> UUID:
        """Generate a correlation ID as UUID."""
        return uuid.uuid4()

    @staticmethod
    def from_string(uuid_str: str) -> UUID:
        """Convert string to UUID, raising ValueError if invalid."""
        return UUID(uuid_str)