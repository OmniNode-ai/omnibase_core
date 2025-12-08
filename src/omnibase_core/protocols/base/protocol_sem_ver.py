"""
Semantic Version Protocol.

Provides a structured approach to versioning with major, minor, and patch
components. Used throughout Core for protocol versioning, dependency
management, and compatibility checking.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ProtocolSemVer(Protocol):
    """
    Protocol for semantic version objects following SemVer specification.

    Provides a structured approach to versioning with major, minor, and patch
    components. Used throughout Core for protocol versioning, dependency
    management, and compatibility checking.
    """

    major: int
    minor: int
    patch: int

    def __str__(self) -> str:
        """Return version string in 'major.minor.patch' format."""
        ...


__all__ = ["ProtocolSemVer"]
