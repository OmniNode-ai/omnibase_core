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
from typing import TYPE_CHECKING, Literal, Protocol, TypeVar, runtime_checkable

if TYPE_CHECKING:
    pass

# =============================================================================
# Type Variables
# =============================================================================

T = TypeVar("T")
T_co = TypeVar("T_co", covariant=True)
TInterface = TypeVar("TInterface")
TImplementation = TypeVar("TImplementation")


# =============================================================================
# Core Literal Type Aliases (Core-native equivalents of SPI types)
# =============================================================================

# Logging levels
LiteralLogLevel = Literal[
    "TRACE", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL", "FATAL"
]

# Node types in ONEX 4-node architecture
LiteralNodeType = Literal["COMPUTE", "EFFECT", "REDUCER", "ORCHESTRATOR"]

# Health status indicators
LiteralHealthStatus = Literal[
    "healthy",
    "degraded",
    "unhealthy",
    "critical",
    "unknown",
    "warning",
    "unreachable",
    "available",
    "unavailable",
    "initializing",
    "disposing",
    "error",
]

# Operation status
LiteralOperationStatus = Literal[
    "success", "failed", "in_progress", "cancelled", "pending"
]

# Service lifecycle patterns
LiteralServiceLifecycle = Literal[
    "singleton", "transient", "scoped", "pooled", "lazy", "eager"
]

# Injection scope patterns
LiteralInjectionScope = Literal[
    "request", "session", "thread", "process", "global", "custom"
]

# Service resolution status
LiteralServiceResolutionStatus = Literal[
    "resolved", "failed", "circular_dependency", "missing_dependency", "type_mismatch"
]

# Validation levels
LiteralValidationLevel = Literal["BASIC", "STANDARD", "COMPREHENSIVE", "PARANOID"]

# Validation modes
LiteralValidationMode = Literal[
    "strict", "lenient", "smoke", "regression", "integration"
]

# Validation severity
LiteralValidationSeverity = Literal["error", "warning", "info"]

# Event priority
LiteralEventPriority = Literal["low", "normal", "high", "critical"]


# =============================================================================
# DateTime Protocol
# =============================================================================

# Use datetime directly as the protocol type (same as SPI)
ProtocolDateTime = datetime


# =============================================================================
# Semantic Version Protocol
# =============================================================================


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


# =============================================================================
# Context Value Protocol (Core-native equivalent of SPI ContextValue)
# =============================================================================


@runtime_checkable
class ProtocolContextValue(Protocol):
    """
    Protocol for context data values supporting validation and serialization.

    Context values are type-safe containers for data passed between nodes
    and services in the ONEX architecture.
    """

    async def validate_for_context(self) -> bool:
        """Validate the value for context usage."""
        ...

    def serialize_for_context(self) -> dict[str, object]:
        """Serialize the value for context transmission."""
        ...

    async def get_context_type_hint(self) -> str:
        """Get the type hint for this context value."""
        ...


# Type alias for backwards compatibility and simpler usage
ContextValue = ProtocolContextValue


# =============================================================================
# Core Protocol Markers (for runtime checkable interfaces)
# =============================================================================


@runtime_checkable
class ProtocolHasModelDump(Protocol):
    """
    Protocol for objects that support Pydantic model_dump method.

    This protocol ensures compatibility with Pydantic models and other
    objects that provide dictionary serialization via model_dump.
    """

    def model_dump(
        self, mode: str | None = None
    ) -> dict[str, str | int | float | bool | list[object] | dict[str, object]]:
        """Serialize the model to a dictionary."""
        ...


@runtime_checkable
class ProtocolModelJsonSerializable(Protocol):
    """
    Protocol for values that can be JSON serialized.

    Marker protocol for objects that can be safely serialized to JSON.
    """

    __omnibase_json_serializable_marker__: Literal[True]


@runtime_checkable
class ProtocolModelValidatable(Protocol):
    """
    Protocol for values that can validate themselves.

    Provides self-validation interface for objects with built-in
    validation logic.
    """

    def is_valid(self) -> bool:
        """Check if the value is valid."""
        ...

    async def get_errors(self) -> list[str]:
        """Get validation errors."""
        ...


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Type Variables
    "T",
    "T_co",
    "TInterface",
    "TImplementation",
    # Literal Types
    "LiteralLogLevel",
    "LiteralNodeType",
    "LiteralHealthStatus",
    "LiteralOperationStatus",
    "LiteralServiceLifecycle",
    "LiteralInjectionScope",
    "LiteralServiceResolutionStatus",
    "LiteralValidationLevel",
    "LiteralValidationMode",
    "LiteralValidationSeverity",
    "LiteralEventPriority",
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
