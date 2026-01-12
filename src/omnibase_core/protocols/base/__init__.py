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

Note on Literal Type Aliases:
    Several Literal type aliases have been replaced with canonical enums
    (per OMN-1308 enum governance). The enum types are exported with their
    original Literal* names as deprecated aliases. New code should import
    the enum types directly from omnibase_core.enums.

    Replaced:
    - LiteralLogLevel -> EnumLogLevel
    - LiteralHealthStatus -> EnumHealthStatus
    - LiteralOperationStatus -> EnumOperationStatus
    - LiteralValidationLevel -> EnumValidationLevel
    - LiteralValidationSeverity -> EnumSeverity
    - LiteralEventPriority -> EnumEventPriority

    Kept as Literals (no canonical enum equivalent):
    - LiteralNodeType (UPPERCASE values, EnumNodeKind uses lowercase)
    - LiteralServiceLifecycle
    - LiteralInjectionScope
    - LiteralServiceResolutionStatus
    - LiteralValidationMode
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal, TypeVar

# =============================================================================
# Canonical Enum Imports (replacing Literal types per OMN-1308)
# =============================================================================
from omnibase_core.enums.enum_event_priority import EnumEventPriority
from omnibase_core.enums.enum_health_status import EnumHealthStatus
from omnibase_core.enums.enum_log_level import EnumLogLevel
from omnibase_core.enums.enum_operation_status import EnumOperationStatus

# Canonical severity enum (OMN-1311)
from omnibase_core.enums.enum_severity import EnumSeverity
from omnibase_core.enums.enum_validation_level import EnumValidationLevel

# =============================================================================
# Type Variables
# =============================================================================

T = TypeVar("T")
T_co = TypeVar("T_co", covariant=True)
TInterface = TypeVar("TInterface")
TImplementation = TypeVar("TImplementation")


# =============================================================================
# Deprecated Type Aliases (Literal* names pointing to Enums)
# =============================================================================

# These deprecated aliases allow existing code importing LiteralXxx types
# to continue working. New code should import enums directly.
LiteralLogLevel = EnumLogLevel
LiteralHealthStatus = EnumHealthStatus
LiteralOperationStatus = EnumOperationStatus
LiteralValidationLevel = EnumValidationLevel
LiteralValidationSeverity = EnumSeverity
LiteralEventPriority = EnumEventPriority


# =============================================================================
# Literal Type Aliases (no canonical enum equivalent)
# =============================================================================

# Node types in ONEX 4-node architecture
# Note: Uses UPPERCASE values; EnumNodeKind uses lowercase. Keep as Literal
# until casing is unified in a future ticket.
LiteralNodeType = Literal["COMPUTE", "EFFECT", "REDUCER", "ORCHESTRATOR"]

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

# Validation modes
LiteralValidationMode = Literal[
    "strict", "lenient", "smoke", "regression", "integration"
]


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
    # Canonical Enums (preferred for new code)
    "EnumLogLevel",
    "EnumHealthStatus",
    "EnumOperationStatus",
    "EnumValidationLevel",
    "EnumSeverity",
    "EnumEventPriority",
    # Backward-Compatible Type Aliases (point to enums above)
    "LiteralLogLevel",
    "LiteralHealthStatus",
    "LiteralOperationStatus",
    "LiteralValidationLevel",
    "LiteralValidationSeverity",
    "LiteralEventPriority",
    # Literal Types (no canonical enum equivalent)
    "LiteralNodeType",
    "LiteralServiceLifecycle",
    "LiteralInjectionScope",
    "LiteralServiceResolutionStatus",
    "LiteralValidationMode",
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
