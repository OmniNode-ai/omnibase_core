"""
Simplified UUID Service stub for import compatibility.
"""

import uuid


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