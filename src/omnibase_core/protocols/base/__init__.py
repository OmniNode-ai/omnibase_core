"""
Core-native base protocols and type aliases.

This module provides common type definitions and base protocols used across
all Core protocol ABCs. It establishes Core-native equivalents for common
SPI types to eliminate external dependencies.

Design Principles:
- Use typing.Protocol with @runtime_checkable for static-only protocols
- Use abc.ABC with @abstractmethod for runtime isinstance checks
- Keep interfaces minimal - only what Core actually needs
- Provide complete type hints for mypy strict mode compliance
"""

from __future__ import annotations

from datetime import datetime
from typing import TypeVar

# =============================================================================
# Type Variables
# =============================================================================

T = TypeVar("T")
T_co = TypeVar("T_co", covariant=True)
TInterface = TypeVar("TInterface")
TImplementation = TypeVar("TImplementation")


# =============================================================================
# DateTime Protocol
# =============================================================================

# Use datetime directly as the protocol type (same as SPI)
ProtocolDateTime = datetime


# =============================================================================
# Protocol Imports
# =============================================================================

from omnibase_core.protocols.base.protocol_context_value import (
    ContextValue,
    ProtocolContextValue,
)
from omnibase_core.protocols.base.protocol_has_model_dump import ProtocolHasModelDump
from omnibase_core.protocols.base.protocol_model_json_serializable import (
    ProtocolModelJsonSerializable,
)
from omnibase_core.protocols.base.protocol_model_validatable import (
    ProtocolModelValidatable,
)
from omnibase_core.protocols.base.protocol_sem_ver import ProtocolSemVer

# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Type Variables
    "T",
    "T_co",
    "TInterface",
    "TImplementation",
    # DateTime
    "ProtocolDateTime",
    # Protocols
    "ProtocolSemVer",
    "ProtocolContextValue",
    "ContextValue",
    "ProtocolHasModelDump",
    "ProtocolModelJsonSerializable",
    "ProtocolModelValidatable",
]
