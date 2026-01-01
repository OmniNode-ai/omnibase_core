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
- capabilities/: Capability provider protocols (OMN-1124)
- container/: DI container and service registry protocols
- event_bus/: Event-driven messaging protocols
- intents/: Intent-related protocols (ProtocolRegistrationRecord)
- notifications/: State transition notification protocols (OMN-1122)
- resolution/: Capability-based dependency resolution protocols (OMN-1123)
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
# Capabilities Module Exports
# =============================================================================
from omnibase_core.protocols.capabilities import ProtocolCapabilityProvider

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
    ProtocolFromEvent,
    ProtocolKafkaEventBusAdapter,
    ProtocolSyncEventBus,
)

# =============================================================================
# Handler Module Exports
# =============================================================================
from omnibase_core.protocols.handler import ProtocolHandlerContext

# =============================================================================
# Handlers Module Exports (Handler Type Resolution)
# =============================================================================
from omnibase_core.protocols.handlers import ProtocolHandlerTypeResolver

# =============================================================================
# HTTP Module Exports
# =============================================================================
from omnibase_core.protocols.http import ProtocolHttpClient, ProtocolHttpResponse

# =============================================================================
# Intents Module Exports
# =============================================================================
from omnibase_core.protocols.intents import ProtocolRegistrationRecord

# =============================================================================
# Notifications Module Exports
# =============================================================================
from omnibase_core.protocols.notifications import (
    ProtocolTransitionNotificationConsumer,
    ProtocolTransitionNotificationPublisher,
)

# =============================================================================
# Logger Module Exports
# =============================================================================
from omnibase_core.protocols.protocol_logger_like import ProtocolLoggerLike

# =============================================================================
# Resolution Module Exports (OMN-1123)
# =============================================================================
from omnibase_core.protocols.resolution import ProtocolDependencyResolver

# =============================================================================
# Runtime Module Exports
# =============================================================================
from omnibase_core.protocols.runtime import ProtocolHandler, ProtocolMessageHandler

# =============================================================================
# Schema Module Exports
# =============================================================================
from omnibase_core.protocols.schema import ProtocolSchemaLoader, ProtocolSchemaModel

# =============================================================================
# Types Module Exports
# =============================================================================
from omnibase_core.protocols.types import (
    ProtocolAction,
    ProtocolCompute,
    ProtocolConfigurable,
    ProtocolEffect,
    ProtocolExecutable,
    ProtocolIdentifiable,
    ProtocolLogEmitter,
    ProtocolMetadata,
    ProtocolMetadataProvider,
    ProtocolNameable,
    ProtocolNodeMetadata,
    ProtocolNodeMetadataBlock,
    ProtocolNodeResult,
    ProtocolOrchestrator,
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
    ProtocolContractValidationInvariantChecker,
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
    # Capabilities Module (OMN-1124)
    # ==========================================================================
    "ProtocolCapabilityProvider",
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
    "ProtocolFromEvent",
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
    # Node Protocols (ONEX Four-Node Architecture) - OMN-662
    "ProtocolCompute",
    "ProtocolEffect",
    "ProtocolOrchestrator",
    "ProtocolState",
    "ProtocolMetadata",
    "ProtocolServiceInstance",
    "ProtocolServiceMetadata",
    # ==========================================================================
    # Core Module
    # ==========================================================================
    "ProtocolCanonicalSerializer",
    # ==========================================================================
    # Logger Module
    # ==========================================================================
    "ProtocolLoggerLike",
    # ==========================================================================
    # Event Construction Protocol
    # ==========================================================================
    "ProtocolFromEvent",
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
    # Notifications Module (OMN-1122)
    # ==========================================================================
    "ProtocolTransitionNotificationPublisher",
    "ProtocolTransitionNotificationConsumer",
    # ==========================================================================
    # Resolution Module (OMN-1123)
    # ==========================================================================
    "ProtocolDependencyResolver",
    # ==========================================================================
    # Handler Module
    # ==========================================================================
    "ProtocolHandlerContext",
    # ==========================================================================
    # Handlers Module (Handler Type Resolution)
    # ==========================================================================
    "ProtocolHandlerTypeResolver",
    # ==========================================================================
    # Runtime Module
    # ==========================================================================
    "ProtocolHandler",
    "ProtocolMessageHandler",
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
    # Contract Validation Invariant Checker (OMN-1146)
    "ProtocolContractValidationInvariantChecker",
]
