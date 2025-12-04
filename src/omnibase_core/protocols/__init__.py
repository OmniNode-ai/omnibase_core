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
- base.py: Common type aliases and base protocols (ContextValue, SemVer, etc.)
- container.py: DI container and service registry protocols
- event_bus.py: Event-driven messaging protocols
- types.py: Type constraint protocols (Configurable, Executable, etc.)
- core.py: Core operation protocols (CanonicalSerializer)
- schema.py: Schema loading protocols
- validation.py: Validation and compliance protocols

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

from omnibase_core.protocols.base import (
    # Type Variables
    T,
    T_co,
    TImplementation,
    TInterface,
    # Literal Types
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
    # Protocols
    ProtocolContextValue,
    ProtocolDateTime,
    ProtocolHasModelDump,
    ProtocolModelJsonSerializable,
    ProtocolModelValidatable,
    ProtocolSemVer,
)

# =============================================================================
# Container Module Exports
# =============================================================================

from omnibase_core.protocols.container import (
    ProtocolDependencyGraph,
    ProtocolInjectionContext,
    ProtocolServiceDependency,
    ProtocolServiceFactory,
    ProtocolServiceInstance,
    ProtocolServiceRegistration,
    ProtocolServiceRegistrationMetadata,
    ProtocolServiceRegistry,
    ProtocolServiceRegistryConfig,
    ProtocolServiceRegistryStatus,
    ProtocolServiceValidator,
    ServiceHealthStatus,
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
    ProtocolKafkaEventBusAdapter,
    ProtocolSyncEventBus,
)

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
    ProtocolServiceMetadata,
    ProtocolState,
    ProtocolSupportedMetadataType,
    ProtocolValidatable,
    ProtocolWorkflowReducer,
)
from omnibase_core.protocols.types import (
    ProtocolServiceInstance as ProtocolDiscoveryServiceInstance,
)

# =============================================================================
# Core Module Exports
# =============================================================================

from omnibase_core.protocols.core import ProtocolCanonicalSerializer

# =============================================================================
# Schema Module Exports
# =============================================================================

from omnibase_core.protocols.schema import ProtocolSchemaLoader, ProtocolSchemaModel

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
# Compatibility Aliases (for migration from SPI)
# =============================================================================

# Container aliases
ProtocolDIServiceInstance = ProtocolServiceInstance
ProtocolDIServiceMetadata = ProtocolServiceRegistrationMetadata

# Type aliases for backwards compatibility
Configurable = ProtocolConfigurable
Executable = ProtocolExecutable
Identifiable = ProtocolIdentifiable
Nameable = ProtocolNameable
Serializable = ProtocolSerializable

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
    "ServiceHealthStatus",
    "ProtocolServiceRegistrationMetadata",
    "ProtocolServiceDependency",
    "ProtocolServiceRegistration",
    "ProtocolServiceInstance",
    "ProtocolDependencyGraph",
    "ProtocolInjectionContext",
    "ProtocolServiceRegistryStatus",
    "ProtocolServiceValidator",
    "ProtocolServiceFactory",
    "ProtocolServiceRegistryConfig",
    "ProtocolServiceRegistry",
    # Container Aliases
    "ProtocolDIServiceInstance",
    "ProtocolDIServiceMetadata",
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
    "ProtocolServiceMetadata",
    "ProtocolDiscoveryServiceInstance",
    # Type Aliases (backwards compatibility)
    "Configurable",
    "Executable",
    "Identifiable",
    "Nameable",
    "Serializable",
    # ==========================================================================
    # Core Module
    # ==========================================================================
    "ProtocolCanonicalSerializer",
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
