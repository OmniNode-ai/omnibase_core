"""
Core-native Protocol ABCs.

This package provides Core-native protocol definitions to replace SPI protocol
dependencies. These protocols establish the contracts for Core components
without external dependencies on omnibase_spi.

Design Principles:
- Use typing.Protocol with @runtime_checkable for duck typing support
- Keep interfaces minimal - only define what Core actually needs
- Provide complete type hints for mypy strict mode compliance
- Use canonical Enum types for enumerated values (from omnibase_core.enums)
- Use forward references where needed to avoid circular imports

Module Organization:
- base/: Common type aliases and base protocols (ContextValue, SemVer, etc.)
- capabilities/: Capability provider protocols (OMN-1124)
- container/: DI container and service registry protocols
- event_bus/: Event-driven messaging protocols
- intents/: Intent-related protocols (ProtocolRegistrationRecord)
- merge/: Contract merge engine protocols (OMN-1127)
- notifications/: State transition notification protocols (OMN-1122)
- resolution/: Capability-based dependency resolution protocols (OMN-1123)
- runtime/: Runtime handler protocols (ProtocolHandler)
- types/: Type constraint protocols (Configurable, Executable, etc.)
- protocol_core.py: Core operation protocols (CanonicalSerializer)
- schema/: Schema loading protocols
- services/: Service protocols (SecretService, etc.)
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

from omnibase_core.protocols.base import (  # Protocols; Type Variables
    ContextValue,
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
# Cache Module Exports
# =============================================================================
from omnibase_core.protocols.cache import ProtocolCacheBackend

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
    ProtocolToolCache,
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
from omnibase_core.protocols.handler import (
    ProtocolCapabilityDependency,
    ProtocolExecutionConstrainable,
    ProtocolExecutionConstraints,
    ProtocolHandlerBehaviorDescriptor,
    ProtocolHandlerContext,
    ProtocolHandlerContract,
)

# =============================================================================
# Handlers Module Exports (Handler Type Resolution)
# =============================================================================
from omnibase_core.protocols.handlers import ProtocolHandlerTypeResolver

# =============================================================================
# HTTP Module Exports
# =============================================================================
from omnibase_core.protocols.http import ProtocolHttpClient, ProtocolHttpResponse

# =============================================================================
# Infrastructure Module Exports
# =============================================================================
from omnibase_core.protocols.infrastructure import (
    ProtocolDatabaseConnection,
    ProtocolServiceDiscovery,
)

# =============================================================================
# Intents Module Exports
# =============================================================================
from omnibase_core.protocols.intents import ProtocolRegistrationRecord

# =============================================================================
# Merge Module Exports (OMN-1127)
# =============================================================================
from omnibase_core.protocols.merge import ProtocolMergeEngine

# =============================================================================
# Metrics Module Exports (OMN-1188)
# =============================================================================
from omnibase_core.protocols.metrics import ProtocolMetricsBackend

# =============================================================================
# Notifications Module Exports
# =============================================================================
from omnibase_core.protocols.notifications import (
    ProtocolTransitionNotificationConsumer,
    ProtocolTransitionNotificationPublisher,
)

# =============================================================================
# Logging Protocol Exports
# =============================================================================
from omnibase_core.protocols.protocol_context_aware_output_handler import (
    ProtocolContextAwareOutputHandler,
)

# =============================================================================
# Contract Validation Event Emitter (OMN-1151)
# =============================================================================
from omnibase_core.protocols.protocol_contract_validation_event_emitter import (
    ProtocolContractValidationEventEmitter,
)

# =============================================================================
# Core Module Exports
# =============================================================================
from omnibase_core.protocols.protocol_core import ProtocolCanonicalSerializer

# =============================================================================
# Generation Protocol Exports
# =============================================================================
from omnibase_core.protocols.protocol_generation_config import ProtocolGenerationConfig
from omnibase_core.protocols.protocol_import_tracker import ProtocolImportTracker
from omnibase_core.protocols.protocol_logger_like import ProtocolLoggerLike

# =============================================================================
# Data Protocol Exports
# =============================================================================
from omnibase_core.protocols.protocol_payload_data import (
    PayloadValue,
    ProtocolPayloadData,
)

# =============================================================================
# Replay Module Exports (OMN-1116, OMN-1204)
# =============================================================================
from omnibase_core.protocols.protocol_replay_progress_callback import (
    ProtocolReplayProgressCallback,
)
from omnibase_core.protocols.protocol_smart_log_formatter import (
    LogDataValue,
    ProtocolSmartLogFormatter,
)
from omnibase_core.protocols.replay import (
    ProtocolEffectRecorder,
    ProtocolRNGService,
    ProtocolTimeService,
)

# =============================================================================
# Resolution Module Exports (OMN-1123, OMN-1106)
# =============================================================================
from omnibase_core.protocols.resolution import (
    ProtocolDependencyResolver,
    ProtocolExecutionResolver,
)

# =============================================================================
# Runtime Module Exports
# =============================================================================
from omnibase_core.protocols.runtime import (
    ProtocolHandler,
    ProtocolHandlerRegistry,
    ProtocolMessageHandler,
)

# =============================================================================
# Schema Module Exports
# =============================================================================
from omnibase_core.protocols.schema import ProtocolSchemaLoader, ProtocolSchemaModel

# =============================================================================
# Services Module Exports
# =============================================================================
from omnibase_core.protocols.services import ProtocolSecretService

# =============================================================================
# Storage Module Exports (OMN-1149)
# =============================================================================
from omnibase_core.protocols.storage import ProtocolDiffStore

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
    # Protocols
    "ProtocolDateTime",
    "ProtocolSemVer",
    "ProtocolContextValue",
    "ContextValue",
    "ProtocolHasModelDump",
    "ProtocolModelJsonSerializable",
    "ProtocolModelValidatable",
    # ==========================================================================
    # Cache Module (OMN-1188)
    # ==========================================================================
    "ProtocolCacheBackend",
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
    # Data Protocols
    # ==========================================================================
    "ProtocolPayloadData",
    "PayloadValue",
    # ==========================================================================
    # Logging Protocols
    # ==========================================================================
    "ProtocolSmartLogFormatter",
    "ProtocolContextAwareOutputHandler",
    "ProtocolLoggerLike",
    "LogDataValue",
    # ==========================================================================
    # Generation Protocols
    # ==========================================================================
    "ProtocolGenerationConfig",
    "ProtocolImportTracker",
    # ==========================================================================
    # Compute Module
    # ==========================================================================
    "ProtocolAsyncCircuitBreaker",
    "ProtocolCircuitBreaker",
    "ProtocolComputeCache",
    "ProtocolParallelExecutor",
    "ProtocolTimingService",
    "ProtocolToolCache",
    # ==========================================================================
    # HTTP Module
    # ==========================================================================
    "ProtocolHttpClient",
    "ProtocolHttpResponse",
    # ==========================================================================
    # Infrastructure Module
    # ==========================================================================
    "ProtocolDatabaseConnection",
    "ProtocolServiceDiscovery",
    # ==========================================================================
    # Intents Module
    # ==========================================================================
    "ProtocolRegistrationRecord",
    # ==========================================================================
    # Merge Module (OMN-1127)
    # ==========================================================================
    "ProtocolMergeEngine",
    # ==========================================================================
    # Metrics Module (OMN-1188)
    # ==========================================================================
    "ProtocolMetricsBackend",
    # ==========================================================================
    # Notifications Module (OMN-1122)
    # ==========================================================================
    "ProtocolTransitionNotificationPublisher",
    "ProtocolTransitionNotificationConsumer",
    # ==========================================================================
    # Resolution Module (OMN-1123, OMN-1106)
    # ==========================================================================
    "ProtocolDependencyResolver",
    "ProtocolExecutionResolver",
    # ==========================================================================
    # Handler Module
    # ==========================================================================
    "ProtocolHandlerContext",
    # Handler Contracts (OMN-1164)
    "ProtocolCapabilityDependency",
    "ProtocolExecutionConstrainable",
    "ProtocolExecutionConstraints",
    "ProtocolHandlerBehaviorDescriptor",
    "ProtocolHandlerContract",
    # ==========================================================================
    # Handlers Module (Handler Type Resolution)
    # ==========================================================================
    "ProtocolHandlerTypeResolver",
    # ==========================================================================
    # Runtime Module
    # ==========================================================================
    "ProtocolHandler",
    "ProtocolHandlerRegistry",
    "ProtocolMessageHandler",
    # ==========================================================================
    # Schema Module
    # ==========================================================================
    "ProtocolSchemaModel",
    "ProtocolSchemaLoader",
    # ==========================================================================
    # Services Module
    # ==========================================================================
    "ProtocolSecretService",
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
    # Contract Validation Event Emitter (OMN-1151)
    "ProtocolContractValidationEventEmitter",
    # ==========================================================================
    # Replay Module (OMN-1116, OMN-1204)
    # ==========================================================================
    "ProtocolEffectRecorder",
    "ProtocolReplayProgressCallback",
    "ProtocolRNGService",
    "ProtocolTimeService",
    # ==========================================================================
    # Storage Module (OMN-1149)
    # ==========================================================================
    "ProtocolDiffStore",
]
