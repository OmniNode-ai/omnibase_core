from __future__ import annotations

"""
Mock container implementation for architecture validation.

This is a minimal mock container used by the NodeArchitectureValidator
for testing node functionality without requiring a full container setup.
"""


from typing import Any


class MockContainer:
    """Mock container implementation for testing."""

    def get_service(self, service_name: str) -> None:
        """
        Get a service from the mock container.

        Args:
            service_name: Name of the service to retrieve

        Returns:
            None (mock implementation)
        """
        return None  # Mock implementation


# Export for use
__all__ = [
    "MockContainer",
]
