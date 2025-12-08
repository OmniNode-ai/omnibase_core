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
from typing import Literal, TypeVar

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
