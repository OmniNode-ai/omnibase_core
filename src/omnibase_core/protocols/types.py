"""
Core-native type protocols.

This module provides protocol definitions for common type constraints
and behaviors used across Core. These are Core-native equivalents of
the SPI type protocols.

Design Principles:
- Protocol-first: Use typing.Protocol for interface definitions
- Marker protocols: Use Literal[True] markers for runtime checks
- Minimal interfaces: Only define what Core actually needs
- Complete type hints: Full mypy strict mode compliance
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal, Protocol, runtime_checkable
from uuid import UUID

from omnibase_core.protocols.base import (
    ContextValue,
    LiteralLogLevel,
    ProtocolDateTime,
    ProtocolSemVer,
)

if TYPE_CHECKING:
    pass


# =============================================================================
# Identifiable Protocol
# =============================================================================


@runtime_checkable
class ProtocolIdentifiable(Protocol):
    """
    Protocol for objects that have an ID.

    Marker protocol with a sentinel attribute for runtime type checking.
    """

    __omnibase_identifiable_marker__: Literal[True]

    @property
    def id(self) -> str:
        """Get the object's unique identifier."""
        ...


# =============================================================================
# Nameable Protocol
# =============================================================================


@runtime_checkable
class ProtocolNameable(Protocol):
    """
    Protocol for objects that have a name.

    Marker protocol with a sentinel attribute for runtime type checking.
    """

    __omnibase_nameable_marker__: Literal[True]

    @property
    def name(self) -> str:
        """Get the object's name."""
        ...


# =============================================================================
# Configurable Protocol
# =============================================================================


@runtime_checkable
class ProtocolConfigurable(Protocol):
    """
    Protocol for objects that can be configured.

    Marker protocol with a sentinel attribute for runtime type checking.
    """

    __omnibase_configurable_marker__: Literal[True]

    def configure(self, **kwargs: ContextValue) -> None:
        """Apply configuration to the object."""
        ...


# =============================================================================
# Executable Protocol
# =============================================================================


@runtime_checkable
class ProtocolExecutable(Protocol):
    """
    Protocol for objects that can be executed.

    Marker protocol with a sentinel attribute for runtime type checking.
    """

    __omnibase_executable_marker__: Literal[True]

    async def execute(self) -> object:
        """Execute the object and return a result."""
        ...


# =============================================================================
# Metadata Provider Protocol
# =============================================================================


@runtime_checkable
class ProtocolMetadataProvider(Protocol):
    """
    Protocol for objects that provide metadata.

    Marker protocol with a sentinel attribute for runtime type checking.
    """

    __omnibase_metadata_provider_marker__: Literal[True]

    async def get_metadata(self) -> dict[str, str | int | bool | float]:
        """Get the object's metadata."""
        ...


# =============================================================================
# Validatable Protocol
# =============================================================================


@runtime_checkable
class ProtocolValidatable(Protocol):
    """
    Protocol for objects that can be validated.

    Defines the minimal interface that validation targets should implement
    to provide context and metadata for validation operations.
    """

    async def get_validation_context(self) -> dict[str, ContextValue]:
        """Get context for validation rules."""
        ...

    async def get_validation_id(self) -> str:
        """Get unique identifier for validation reporting."""
        ...


# =============================================================================
# Serializable Protocol
# =============================================================================


@runtime_checkable
class ProtocolSerializable(Protocol):
    """
    Protocol for objects that can be serialized to dictionary format.

    Provides standardized serialization contract for ONEX objects that need
    to be persisted, transmitted, or cached.
    """

    def model_dump(
        self,
    ) -> dict[
        str,
        str
        | int
        | float
        | bool
        | list[str | int | float | bool]
        | dict[str, str | int | float | bool],
    ]:
        """Serialize the object to a dictionary."""
        ...


# =============================================================================
# Log Emitter Protocol
# =============================================================================


@runtime_checkable
class ProtocolLogEmitter(Protocol):
    """
    Protocol for objects that can emit structured log events.

    Provides standardized logging interface for ONEX services.
    """

    def emit_log_event(
        self,
        level: LiteralLogLevel,
        message: str,
        data: object,
    ) -> None:
        """Emit a structured log event."""
        ...


# =============================================================================
# Supported Metadata Type Protocol
# =============================================================================


@runtime_checkable
class ProtocolSupportedMetadataType(Protocol):
    """
    Protocol for types that can be stored in ONEX metadata systems.

    This marker protocol defines the contract for objects that can be safely
    stored, serialized, and retrieved from metadata storage systems.
    """

    __omnibase_metadata_type_marker__: Literal[True]

    def __str__(self) -> str:
        """Convert to string for storage."""
        ...

    async def validate_for_metadata(self) -> bool:
        """Validate the value for metadata storage."""
        ...


# =============================================================================
# Schema Value Protocol
# =============================================================================


@runtime_checkable
class ProtocolSchemaValue(Protocol):
    """
    Protocol for schema value types.

    Allows working with schema values without depending on
    the concrete ModelSchemaValue class.
    """

    def to_value(self) -> object:
        """Convert to Python value."""
        ...

    @classmethod
    def from_value(cls, value: object) -> ProtocolSchemaValue:
        """Create from Python value."""
        ...


# =============================================================================
# Node Metadata Block Protocol
# =============================================================================


@runtime_checkable
class ProtocolNodeMetadataBlock(Protocol):
    """
    Protocol for node metadata block objects.

    Defines the structure of ONEX node metadata including identification,
    versioning, and lifecycle information.
    """

    uuid: str
    name: str
    description: str
    version: ProtocolSemVer
    metadata_version: ProtocolSemVer
    namespace: str
    created_at: ProtocolDateTime
    last_modified_at: ProtocolDateTime
    lifecycle: str
    protocol_version: ProtocolSemVer

    async def validate_metadata_block(self) -> bool:
        """Validate the metadata block."""
        ...

    def is_complete(self) -> bool:
        """Check if the metadata block is complete."""
        ...


# =============================================================================
# Node Metadata Protocol
# =============================================================================


@runtime_checkable
class ProtocolNodeMetadata(Protocol):
    """
    Protocol for ONEX node metadata objects.

    Defines the essential metadata structure for nodes in the ONEX
    distributed system.
    """

    node_id: str
    node_type: str
    metadata: dict[str, ContextValue]

    async def validate_node_metadata(self) -> bool:
        """Validate the node metadata."""
        ...

    def is_complete(self) -> bool:
        """Check if the metadata is complete."""
        ...


# =============================================================================
# Action Protocol
# =============================================================================


@runtime_checkable
class ProtocolAction(Protocol):
    """
    Protocol for reducer actions.

    Defines the interface for action objects used in reducer dispatch operations.
    """

    type: str
    payload: object | None
    timestamp: ProtocolDateTime

    async def validate_action(self) -> bool:
        """Validate action structure and payload."""
        ...

    def is_executable(self) -> bool:
        """Check if action can be executed."""
        ...


# =============================================================================
# Node Result Protocol
# =============================================================================


@runtime_checkable
class ProtocolNodeResult(Protocol):
    """
    Protocol for node workflow results.

    Defines the interface for result objects from dispatch_async operations.
    """

    value: ContextValue | None
    is_success: bool
    is_failure: bool
    error: object | None
    trust_score: float
    provenance: list[str]
    metadata: dict[str, ContextValue]
    events: list[object]
    state_delta: dict[str, ContextValue]

    async def validate_result(self) -> bool:
        """Validate result structure."""
        ...

    def is_successful(self) -> bool:
        """Check if result represents success."""
        ...


# =============================================================================
# Workflow Reducer Protocol
# =============================================================================


@runtime_checkable
class ProtocolWorkflowReducer(Protocol):
    """
    Protocol for workflow reducer nodes.

    Defines the interface for nodes that implement the reducer pattern
    with synchronous and asynchronous dispatch capabilities.
    """

    def initial_state(self) -> ProtocolState:
        """Returns the initial state for the reducer."""
        ...

    def dispatch(self, state: ProtocolState, action: ProtocolAction) -> ProtocolState:
        """Synchronous state transition for simple operations."""
        ...

    async def dispatch_async(
        self,
        state: ProtocolState,
        action: ProtocolAction,
    ) -> ProtocolNodeResult:
        """Asynchronous workflow-based state transition."""
        ...


# =============================================================================
# State Protocol
# =============================================================================


@runtime_checkable
class ProtocolState(Protocol):
    """
    Protocol for reducer state.

    Defines the interface for state objects used in reducer nodes.
    """

    metadata: ProtocolMetadata
    version: int
    last_updated: ProtocolDateTime

    async def validate_state(self) -> bool:
        """Validate the state."""
        ...

    def is_consistent(self) -> bool:
        """Check if the state is consistent."""
        ...


# =============================================================================
# Metadata Protocol
# =============================================================================


@runtime_checkable
class ProtocolMetadata(Protocol):
    """
    Protocol for structured metadata.

    Attribute-based for data compatibility.
    """

    data: dict[str, ContextValue]
    version: ProtocolSemVer
    created_at: ProtocolDateTime
    updated_at: ProtocolDateTime | None

    async def validate_metadata(self) -> bool:
        """Validate the metadata."""
        ...

    def is_up_to_date(self) -> bool:
        """Check if the metadata is up to date."""
        ...


# =============================================================================
# Service Instance Protocol
# =============================================================================


@runtime_checkable
class ProtocolServiceInstance(Protocol):
    """
    Protocol for service instance information.

    Used for service discovery and health monitoring.
    """

    service_id: UUID
    service_name: str
    host: str
    port: int
    metadata: ProtocolServiceMetadata
    health_status: str
    last_seen: ProtocolDateTime

    async def validate_service_instance(self) -> bool:
        """Validate the service instance."""
        ...

    def is_available(self) -> bool:
        """Check if the service is available."""
        ...


# =============================================================================
# Service Metadata Protocol
# =============================================================================


@runtime_checkable
class ProtocolServiceMetadata(Protocol):
    """
    Protocol for service metadata.

    Contains metadata about a service including capabilities and tags.
    """

    data: dict[str, ContextValue]
    version: ProtocolSemVer
    capabilities: list[str]
    tags: list[str]

    async def validate_service_metadata(self) -> bool:
        """Validate the service metadata."""
        ...

    def has_capabilities(self) -> bool:
        """Check if the service has capabilities."""
        ...


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Marker Protocols
    "ProtocolIdentifiable",
    "ProtocolNameable",
    "ProtocolConfigurable",
    "ProtocolExecutable",
    "ProtocolMetadataProvider",
    "ProtocolValidatable",
    "ProtocolSerializable",
    "ProtocolLogEmitter",
    "ProtocolSupportedMetadataType",
    # Schema
    "ProtocolSchemaValue",
    # Node Metadata
    "ProtocolNodeMetadataBlock",
    "ProtocolNodeMetadata",
    # Action and Result
    "ProtocolAction",
    "ProtocolNodeResult",
    # Workflow Reducer
    "ProtocolWorkflowReducer",
    # State
    "ProtocolState",
    "ProtocolMetadata",
    # Service
    "ProtocolServiceInstance",
    "ProtocolServiceMetadata",
]
