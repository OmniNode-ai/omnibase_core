"""Dependency injection modes for real vs mock services."""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumDependencyMode(StrValueHelper, str, Enum):
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


__all__ = ["EnumDependencyMode"]
