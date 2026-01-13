"""
Architecture enumeration for node metadata.

Defines supported CPU architectures for ONEX nodes.
"""

import enum


@enum.unique
class EnumArchitecture(enum.StrEnum):
    """Supported CPU architectures."""

    AMD64 = "amd64"
    ARM64 = "arm64"
    PPC64LE = "ppc64le"
