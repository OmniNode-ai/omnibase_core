"""
UUID Service - Centralized UUID generation and validation.

Provides consistent UUID generation across the ONEX system.
"""

from typing import Optional
from uuid import UUID, uuid4


class UUIDService:
    """Centralized UUID generation and validation service."""

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
    def parse(uuid_string: str) -> Optional[UUID]:
        """Parse a UUID string, return None if invalid."""
        try:
            return UUID(uuid_string)
        except (ValueError, TypeError):
            return None
