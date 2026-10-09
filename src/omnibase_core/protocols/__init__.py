# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

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

from __future__ import annotations

# =============================================================================
# Base Module Exports
# =============================================================================
import importlib.util
from typing import TYPE_CHECKING

if TYPE_CHECKING:
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
    # Crypto Module Exports (OMN-1898)
    # =============================================================================
    from omnibase_core.protocols.crypto import ProtocolKeyProvider

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
    from omnibase_core.protocols.protocol_generation_config import (
        ProtocolGenerationConfig,
    )
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
    # Crypto Module (OMN-1898)
    # ==========================================================================
    "ProtocolKeyProvider",
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


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "ContextValue": ("omnibase_core.protocols.base", "ContextValue"),
    "ProtocolContextValue": ("omnibase_core.protocols.base", "ProtocolContextValue"),
    "ProtocolDateTime": ("omnibase_core.protocols.base", "ProtocolDateTime"),
    "ProtocolHasModelDump": ("omnibase_core.protocols.base", "ProtocolHasModelDump"),
    "ProtocolModelJsonSerializable": (
        "omnibase_core.protocols.base",
        "ProtocolModelJsonSerializable",
    ),
    "ProtocolModelValidatable": (
        "omnibase_core.protocols.base",
        "ProtocolModelValidatable",
    ),
    "ProtocolSemVer": ("omnibase_core.protocols.base", "ProtocolSemVer"),
    "T": ("omnibase_core.protocols.base", "T"),
    "T_co": ("omnibase_core.protocols.base", "T_co"),
    "TImplementation": ("omnibase_core.protocols.base", "TImplementation"),
    "TInterface": ("omnibase_core.protocols.base", "TInterface"),
    "ProtocolCacheBackend": ("omnibase_core.protocols.cache", "ProtocolCacheBackend"),
    "ProtocolCapabilityProvider": (
        "omnibase_core.protocols.capabilities",
        "ProtocolCapabilityProvider",
    ),
    "ProtocolAsyncCircuitBreaker": (
        "omnibase_core.protocols.compute",
        "ProtocolAsyncCircuitBreaker",
    ),
    "ProtocolCircuitBreaker": (
        "omnibase_core.protocols.compute",
        "ProtocolCircuitBreaker",
    ),
    "ProtocolComputeCache": ("omnibase_core.protocols.compute", "ProtocolComputeCache"),
    "ProtocolParallelExecutor": (
        "omnibase_core.protocols.compute",
        "ProtocolParallelExecutor",
    ),
    "ProtocolTimingService": (
        "omnibase_core.protocols.compute",
        "ProtocolTimingService",
    ),
    "ProtocolToolCache": ("omnibase_core.protocols.compute", "ProtocolToolCache"),
    "ProtocolDependencyGraph": (
        "omnibase_core.protocols.container",
        "ProtocolDependencyGraph",
    ),
    "ProtocolInjectionContext": (
        "omnibase_core.protocols.container",
        "ProtocolInjectionContext",
    ),
    "ProtocolManagedServiceInstance": (
        "omnibase_core.protocols.container",
        "ProtocolManagedServiceInstance",
    ),
    "ProtocolServiceDependency": (
        "omnibase_core.protocols.container",
        "ProtocolServiceDependency",
    ),
    "ProtocolServiceFactory": (
        "omnibase_core.protocols.container",
        "ProtocolServiceFactory",
    ),
    "ProtocolServiceRegistration": (
        "omnibase_core.protocols.container",
        "ProtocolServiceRegistration",
    ),
    "ProtocolServiceRegistrationMetadata": (
        "omnibase_core.protocols.container",
        "ProtocolServiceRegistrationMetadata",
    ),
    "ProtocolServiceRegistry": (
        "omnibase_core.protocols.container",
        "ProtocolServiceRegistry",
    ),
    "ProtocolServiceRegistryConfig": (
        "omnibase_core.protocols.container",
        "ProtocolServiceRegistryConfig",
    ),
    "ProtocolServiceRegistryStatus": (
        "omnibase_core.protocols.container",
        "ProtocolServiceRegistryStatus",
    ),
    "ProtocolServiceValidator": (
        "omnibase_core.protocols.container",
        "ProtocolServiceValidator",
    ),
    "ProtocolKeyProvider": ("omnibase_core.protocols.crypto", "ProtocolKeyProvider"),
    "ProtocolAsyncEventBus": (
        "omnibase_core.protocols.event_bus",
        "ProtocolAsyncEventBus",
    ),
    "ProtocolEventBus": ("omnibase_core.protocols.event_bus", "ProtocolEventBus"),
    "ProtocolEventBusBase": (
        "omnibase_core.protocols.event_bus",
        "ProtocolEventBusBase",
    ),
    "ProtocolEventBusHeaders": (
        "omnibase_core.protocols.event_bus",
        "ProtocolEventBusHeaders",
    ),
    "ProtocolEventBusLogEmitter": (
        "omnibase_core.protocols.event_bus",
        "ProtocolEventBusLogEmitter",
    ),
    "ProtocolEventBusRegistry": (
        "omnibase_core.protocols.event_bus",
        "ProtocolEventBusRegistry",
    ),
    "ProtocolEventEnvelope": (
        "omnibase_core.protocols.event_bus",
        "ProtocolEventEnvelope",
    ),
    "ProtocolEventMessage": (
        "omnibase_core.protocols.event_bus",
        "ProtocolEventMessage",
    ),
    "ProtocolFromEvent": ("omnibase_core.protocols.event_bus", "ProtocolFromEvent"),
    "ProtocolKafkaEventBusAdapter": (
        "omnibase_core.protocols.event_bus",
        "ProtocolKafkaEventBusAdapter",
    ),
    "ProtocolSyncEventBus": (
        "omnibase_core.protocols.event_bus",
        "ProtocolSyncEventBus",
    ),
    "ProtocolCapabilityDependency": (
        "omnibase_core.protocols.handler",
        "ProtocolCapabilityDependency",
    ),
    "ProtocolExecutionConstrainable": (
        "omnibase_core.protocols.handler",
        "ProtocolExecutionConstrainable",
    ),
    "ProtocolExecutionConstraints": (
        "omnibase_core.protocols.handler",
        "ProtocolExecutionConstraints",
    ),
    "ProtocolHandlerBehaviorDescriptor": (
        "omnibase_core.protocols.handler",
        "ProtocolHandlerBehaviorDescriptor",
    ),
    "ProtocolHandlerContext": (
        "omnibase_core.protocols.handler",
        "ProtocolHandlerContext",
    ),
    "ProtocolHandlerContract": (
        "omnibase_core.protocols.handler",
        "ProtocolHandlerContract",
    ),
    "ProtocolHandlerTypeResolver": (
        "omnibase_core.protocols.handlers",
        "ProtocolHandlerTypeResolver",
    ),
    "ProtocolHttpClient": ("omnibase_core.protocols.http", "ProtocolHttpClient"),
    "ProtocolHttpResponse": ("omnibase_core.protocols.http", "ProtocolHttpResponse"),
    "ProtocolDatabaseConnection": (
        "omnibase_core.protocols.infrastructure",
        "ProtocolDatabaseConnection",
    ),
    "ProtocolServiceDiscovery": (
        "omnibase_core.protocols.infrastructure",
        "ProtocolServiceDiscovery",
    ),
    "ProtocolRegistrationRecord": (
        "omnibase_core.protocols.intents",
        "ProtocolRegistrationRecord",
    ),
    "ProtocolMergeEngine": ("omnibase_core.protocols.merge", "ProtocolMergeEngine"),
    "ProtocolMetricsBackend": (
        "omnibase_core.protocols.metrics",
        "ProtocolMetricsBackend",
    ),
    "ProtocolTransitionNotificationConsumer": (
        "omnibase_core.protocols.notifications",
        "ProtocolTransitionNotificationConsumer",
    ),
    "ProtocolTransitionNotificationPublisher": (
        "omnibase_core.protocols.notifications",
        "ProtocolTransitionNotificationPublisher",
    ),
    "ProtocolContextAwareOutputHandler": (
        "omnibase_core.protocols.protocol_context_aware_output_handler",
        "ProtocolContextAwareOutputHandler",
    ),
    "ProtocolContractValidationEventEmitter": (
        "omnibase_core.protocols.protocol_contract_validation_event_emitter",
        "ProtocolContractValidationEventEmitter",
    ),
    "ProtocolCanonicalSerializer": (
        "omnibase_core.protocols.protocol_core",
        "ProtocolCanonicalSerializer",
    ),
    "ProtocolGenerationConfig": (
        "omnibase_core.protocols.protocol_generation_config",
        "ProtocolGenerationConfig",
    ),
    "ProtocolImportTracker": (
        "omnibase_core.protocols.protocol_import_tracker",
        "ProtocolImportTracker",
    ),
    "ProtocolLoggerLike": (
        "omnibase_core.protocols.protocol_logger_like",
        "ProtocolLoggerLike",
    ),
    "PayloadValue": ("omnibase_core.protocols.protocol_payload_data", "PayloadValue"),
    "ProtocolPayloadData": (
        "omnibase_core.protocols.protocol_payload_data",
        "ProtocolPayloadData",
    ),
    "ProtocolReplayProgressCallback": (
        "omnibase_core.protocols.protocol_replay_progress_callback",
        "ProtocolReplayProgressCallback",
    ),
    "LogDataValue": (
        "omnibase_core.protocols.protocol_smart_log_formatter",
        "LogDataValue",
    ),
    "ProtocolSmartLogFormatter": (
        "omnibase_core.protocols.protocol_smart_log_formatter",
        "ProtocolSmartLogFormatter",
    ),
    "ProtocolEffectRecorder": (
        "omnibase_core.protocols.replay",
        "ProtocolEffectRecorder",
    ),
    "ProtocolRNGService": ("omnibase_core.protocols.replay", "ProtocolRNGService"),
    "ProtocolTimeService": ("omnibase_core.protocols.replay", "ProtocolTimeService"),
    "ProtocolDependencyResolver": (
        "omnibase_core.protocols.resolution",
        "ProtocolDependencyResolver",
    ),
    "ProtocolExecutionResolver": (
        "omnibase_core.protocols.resolution",
        "ProtocolExecutionResolver",
    ),
    "ProtocolHandlerRegistry": (
        "omnibase_core.protocols.runtime",
        "ProtocolHandlerRegistry",
    ),
    "ProtocolMessageHandler": (
        "omnibase_core.protocols.runtime",
        "ProtocolMessageHandler",
    ),
    "ProtocolSchemaLoader": ("omnibase_core.protocols.schema", "ProtocolSchemaLoader"),
    "ProtocolSchemaModel": ("omnibase_core.protocols.schema", "ProtocolSchemaModel"),
    "ProtocolSecretService": (
        "omnibase_core.protocols.services",
        "ProtocolSecretService",
    ),
    "ProtocolDiffStore": ("omnibase_core.protocols.storage", "ProtocolDiffStore"),
    "ProtocolAction": ("omnibase_core.protocols.types", "ProtocolAction"),
    "ProtocolCompute": ("omnibase_core.protocols.types", "ProtocolCompute"),
    "ProtocolConfigurable": ("omnibase_core.protocols.types", "ProtocolConfigurable"),
    "ProtocolEffect": ("omnibase_core.protocols.types", "ProtocolEffect"),
    "ProtocolExecutable": ("omnibase_core.protocols.types", "ProtocolExecutable"),
    "ProtocolIdentifiable": ("omnibase_core.protocols.types", "ProtocolIdentifiable"),
    "ProtocolLogEmitter": ("omnibase_core.protocols.types", "ProtocolLogEmitter"),
    "ProtocolMetadata": ("omnibase_core.protocols.types", "ProtocolMetadata"),
    "ProtocolMetadataProvider": (
        "omnibase_core.protocols.types",
        "ProtocolMetadataProvider",
    ),
    "ProtocolNameable": ("omnibase_core.protocols.types", "ProtocolNameable"),
    "ProtocolNodeMetadata": ("omnibase_core.protocols.types", "ProtocolNodeMetadata"),
    "ProtocolNodeMetadataBlock": (
        "omnibase_core.protocols.types",
        "ProtocolNodeMetadataBlock",
    ),
    "ProtocolNodeResult": ("omnibase_core.protocols.types", "ProtocolNodeResult"),
    "ProtocolOrchestrator": ("omnibase_core.protocols.types", "ProtocolOrchestrator"),
    "ProtocolSchemaValue": ("omnibase_core.protocols.types", "ProtocolSchemaValue"),
    "ProtocolSerializable": ("omnibase_core.protocols.types", "ProtocolSerializable"),
    "ProtocolServiceInstance": (
        "omnibase_core.protocols.types",
        "ProtocolServiceInstance",
    ),
    "ProtocolServiceMetadata": (
        "omnibase_core.protocols.types",
        "ProtocolServiceMetadata",
    ),
    "ProtocolState": ("omnibase_core.protocols.types", "ProtocolState"),
    "ProtocolSupportedMetadataType": (
        "omnibase_core.protocols.types",
        "ProtocolSupportedMetadataType",
    ),
    "ProtocolValidatable": ("omnibase_core.protocols.types", "ProtocolValidatable"),
    "ProtocolWorkflowReducer": (
        "omnibase_core.protocols.types",
        "ProtocolWorkflowReducer",
    ),
    "ProtocolArchitectureCompliance": (
        "omnibase_core.protocols.validation",
        "ProtocolArchitectureCompliance",
    ),
    "ProtocolComplianceReport": (
        "omnibase_core.protocols.validation",
        "ProtocolComplianceReport",
    ),
    "ProtocolComplianceRule": (
        "omnibase_core.protocols.validation",
        "ProtocolComplianceRule",
    ),
    "ProtocolComplianceValidator": (
        "omnibase_core.protocols.validation",
        "ProtocolComplianceValidator",
    ),
    "ProtocolComplianceViolation": (
        "omnibase_core.protocols.validation",
        "ProtocolComplianceViolation",
    ),
    "ProtocolContractValidationInvariantChecker": (
        "omnibase_core.protocols.validation",
        "ProtocolContractValidationInvariantChecker",
    ),
    "ProtocolONEXStandards": (
        "omnibase_core.protocols.validation",
        "ProtocolONEXStandards",
    ),
    "ProtocolQualityValidator": (
        "omnibase_core.protocols.validation",
        "ProtocolQualityValidator",
    ),
    "ProtocolValidationDecorator": (
        "omnibase_core.protocols.validation",
        "ProtocolValidationDecorator",
    ),
    "ProtocolValidationError": (
        "omnibase_core.protocols.validation",
        "ProtocolValidationError",
    ),
    "ProtocolValidationResult": (
        "omnibase_core.protocols.validation",
        "ProtocolValidationResult",
    ),
    "ProtocolValidator": ("omnibase_core.protocols.validation", "ProtocolValidator"),
}


def __getattr__(name: str) -> object:
    target = _LAZY_IMPORTS.get(name)
    if target is None:
        # A submodule that the old eager __init__ loaded as a side effect
        # stays reachable as ``package.submodule``: import it on first access.
        if (
            name.isidentifier()
            and not name.startswith("__")
            and importlib.util.find_spec(f"{__name__}.{name}") is not None
        ):
            return importlib.import_module(f"{__name__}.{name}")
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = importlib.import_module(target[0])
    value = module if target[1] is None else getattr(module, target[1])
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted({*globals(), *_LAZY_IMPORTS})
