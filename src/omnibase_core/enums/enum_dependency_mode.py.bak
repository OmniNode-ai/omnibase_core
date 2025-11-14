from enum import Enum


class EnumDependencyMode(str, Enum):
    """
    Canonical enum for scenario dependency injection modes.
    Controls whether scenarios use real external services or mocked test doubles.
    """

    REAL = "real"
    MOCK = "mock"

    def is_real(self) -> bool:
        """Return True if this mode uses real external services."""
        return self == self.REAL

    def is_mock(self) -> bool:
        """Return True if this mode uses mocked dependencies."""
        return self == self.MOCK
