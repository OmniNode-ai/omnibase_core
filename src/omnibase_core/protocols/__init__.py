"""
Core-native Protocol ABCs.

This package provides Core-native protocol definitions to replace SPI protocol
dependencies. These protocols establish the contracts for Core components
without external dependencies on omnibase_spi.

Design Principles:
- Use typing.Protocol with @runtime_checkable for duck typing support
- Keep interfaces minimal - only define what Core actually needs
- Provide complete type hints for mypy strict mode compliance
- Use Literal types for enumerated values
- Use forward references where needed to avoid circular imports

Module Organization:
- base/: Common type aliases and base protocols (ContextValue, SemVer, etc.)
- container/: DI container and service registry protocols
- event_bus/: Event-driven messaging protocols
- intents/: Intent-related protocols (ProtocolRegistrationRecord)
- runtime/: Runtime handler protocols (ProtocolHandler)
- types/: Type constraint protocols (Configurable, Executable, etc.)
- core.py: Core operation protocols (CanonicalSerializer)
- schema/: Schema loading protocols
- validation/: Validation and compliance protocols

Usage:
    from omnibase_core.protocols import (
        ProtocolServiceRegistry,
        ProtocolEventBus,
        ProtocolConfigurable,
        ProtocolValidationResult,
    )

Migration from SPI:
    # Before (SPI import):
    from omnibase_spi.protocols.container import ProtocolServiceRegistry

    # After (Core-native):
    from omnibase_core.protocols import ProtocolServiceRegistry
"""

# =============================================================================
# Base Module Exports
# =============================================================================

from omnibase_core.protocols.base import (  # Literal Types; Protocols; Type Variables
    ContextValue,
    LiteralEventPriority,
    LiteralHealthStatus,
    LiteralInjectionScope,
    LiteralLogLevel,
    LiteralNodeType,
    LiteralOperationStatus,
    LiteralServiceLifecycle,
    LiteralServiceResolutionStatus,
    LiteralValidationLevel,
    LiteralValidationMode,
    LiteralValidationSeverity,
    ProtocolContextValue,
    ProtocolDateTime,
    ProtocolHasModelDump,
    ProtocolModelJsonSerializable,
    ProtocolModelValidatable,
    ProtocolSemVer,
    T,
    T_co,
    TImplementation,
    TInterface,
)

# =============================================================================
# Compute Module Exports
# =============================================================================
from omnibase_core.protocols.compute import (
    ProtocolAsyncCircuitBreaker,
    ProtocolCircuitBreaker,
    ProtocolComputeCache,
    ProtocolParallelExecutor,
    ProtocolTimingService,
)

# =============================================================================
# Container Module Exports
# =============================================================================
from omnibase_core.protocols.container import (
    ProtocolDependencyGraph,
    ProtocolInjectionContext,
    ProtocolManagedServiceInstance,
    ProtocolServiceDependency,
    ProtocolServiceFactory,
    ProtocolServiceRegistration,
    ProtocolServiceRegistrationMetadata,
    ProtocolServiceRegistry,
    ProtocolServiceRegistryConfig,
    ProtocolServiceRegistryStatus,
    ProtocolServiceValidator,
)

# =============================================================================
# Compute Module Exports
# =============================================================================
# =============================================================================
# Core Module Exports
# =============================================================================
from omnibase_core.protocols.core import ProtocolCanonicalSerializer

# =============================================================================
# Event Bus Module Exports
# =============================================================================
from omnibase_core.protocols.event_bus import (
    ProtocolAsyncEventBus,
    ProtocolEventBus,
    ProtocolEventBusBase,
    ProtocolEventBusHeaders,
    ProtocolEventBusLogEmitter,
    ProtocolEventBusRegistry,
    ProtocolEventEnvelope,
    ProtocolEventMessage,
    ProtocolKafkaEventBusAdapter,
    ProtocolSyncEventBus,
)

# =============================================================================
# HTTP Module Exports
# =============================================================================
from omnibase_core.protocols.http import ProtocolHttpClient, ProtocolHttpResponse

# =============================================================================
# Intents Module Exports
# =============================================================================
from omnibase_core.protocols.intents import ProtocolRegistrationRecord

# =============================================================================
# Runtime Module Exports
# =============================================================================
from omnibase_core.protocols.runtime import ProtocolHandler

# =============================================================================
# Schema Module Exports
# =============================================================================
from omnibase_core.protocols.schema import ProtocolSchemaLoader, ProtocolSchemaModel

# =============================================================================
# Types Module Exports
# =============================================================================
from omnibase_core.protocols.types import (
    ProtocolAction,
    ProtocolConfigurable,
    ProtocolExecutable,
    ProtocolIdentifiable,
    ProtocolLogEmitter,
    ProtocolMetadata,
    ProtocolMetadataProvider,
    ProtocolNameable,
    ProtocolNodeMetadata,
    ProtocolNodeMetadataBlock,
    ProtocolNodeResult,
    ProtocolSchemaValue,
    ProtocolSerializable,
    ProtocolServiceInstance,
    ProtocolServiceMetadata,
    ProtocolState,
    ProtocolSupportedMetadataType,
    ProtocolValidatable,
    ProtocolWorkflowReducer,
)

# =============================================================================
# Validation Module Exports
# =============================================================================
from omnibase_core.protocols.validation import (
    ProtocolArchitectureCompliance,
    ProtocolComplianceReport,
    ProtocolComplianceRule,
    ProtocolComplianceValidator,
    ProtocolComplianceViolation,
    ProtocolONEXStandards,
    ProtocolQualityValidator,
    ProtocolValidationDecorator,
    ProtocolValidationError,
    ProtocolValidationResult,
    ProtocolValidator,
)

# =============================================================================
# All Exports
# =============================================================================

__all__ = [
    # ==========================================================================
    # Base Module
    # ==========================================================================
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
    # Protocols
    "ProtocolDateTime",
    "ProtocolSemVer",
    "ProtocolContextValue",
    "ContextValue",
    "ProtocolHasModelDump",
    "ProtocolModelJsonSerializable",
    "ProtocolModelValidatable",
    # ==========================================================================
    # Container Module
    # ==========================================================================
    "ProtocolServiceRegistrationMetadata",
    "ProtocolServiceDependency",
    "ProtocolServiceRegistration",
    "ProtocolManagedServiceInstance",
    "ProtocolDependencyGraph",
    "ProtocolInjectionContext",
    "ProtocolServiceRegistryStatus",
    "ProtocolServiceValidator",
    "ProtocolServiceFactory",
    "ProtocolServiceRegistryConfig",
    "ProtocolServiceRegistry",
    # ==========================================================================
    # Event Bus Module
    # ==========================================================================
    "ProtocolEventMessage",
    "ProtocolEventBusHeaders",
    "ProtocolKafkaEventBusAdapter",
    "ProtocolEventBus",
    "ProtocolEventBusBase",
    "ProtocolSyncEventBus",
    "ProtocolAsyncEventBus",
    "ProtocolEventEnvelope",
    "ProtocolEventBusRegistry",
    "ProtocolEventBusLogEmitter",
    # ==========================================================================
    # Types Module
    # ==========================================================================
    "ProtocolIdentifiable",
    "ProtocolNameable",
    "ProtocolConfigurable",
    "ProtocolExecutable",
    "ProtocolMetadataProvider",
    "ProtocolValidatable",
    "ProtocolSerializable",
    "ProtocolLogEmitter",
    "ProtocolSupportedMetadataType",
    "ProtocolSchemaValue",
    "ProtocolNodeMetadataBlock",
    "ProtocolNodeMetadata",
    "ProtocolAction",
    "ProtocolNodeResult",
    "ProtocolWorkflowReducer",
    "ProtocolState",
    "ProtocolMetadata",
    "ProtocolServiceInstance",
    "ProtocolServiceMetadata",
    # ==========================================================================
    # Core Module
    # ==========================================================================
    "ProtocolCanonicalSerializer",
    # ==========================================================================
    # Compute Module
    # ==========================================================================
    "ProtocolAsyncCircuitBreaker",
    "ProtocolCircuitBreaker",
    "ProtocolComputeCache",
    "ProtocolParallelExecutor",
    "ProtocolTimingService",
    # ==========================================================================
    # HTTP Module
    # ==========================================================================
    "ProtocolHttpClient",
    "ProtocolHttpResponse",
    # ==========================================================================
    # Intents Module
    # ==========================================================================
    "ProtocolRegistrationRecord",
    # ==========================================================================
    # Runtime Module
    # ==========================================================================
    "ProtocolHandler",
    # ==========================================================================
    # Schema Module
    # ==========================================================================
    "ProtocolSchemaModel",
    "ProtocolSchemaLoader",
    # ==========================================================================
    # Validation Module
    # ==========================================================================
    "ProtocolValidationError",
    "ProtocolValidationResult",
    "ProtocolValidator",
    "ProtocolValidationDecorator",
    "ProtocolComplianceRule",
    "ProtocolComplianceViolation",
    "ProtocolONEXStandards",
    "ProtocolArchitectureCompliance",
    "ProtocolComplianceReport",
    "ProtocolComplianceValidator",
    "ProtocolQualityValidator",
]
