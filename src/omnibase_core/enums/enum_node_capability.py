"""
Node capability enumeration for categorizing node capability types.

Provides strongly typed capability categories for node features
and functionality across the ONEX architecture.
"""

from __future__ import annotations

from enum import Enum


class EnumNodeCapability(str, Enum):
    """
    Strongly typed node capabilities.

    Inherits from str for JSON serialization compatibility while providing
    type safety and IDE support for node capability specification.
    """

    # Support capabilities (from ModelNodeCapability)
    SUPPORTS_DRY_RUN = "supports_dry_run"
    SUPPORTS_BATCH_PROCESSING = "supports_batch_processing"
    SUPPORTS_CUSTOM_HANDLERS = "supports_custom_handlers"
    SUPPORTS_CORRELATION_ID = "supports_correlation_id"
    SUPPORTS_EVENT_BUS = "supports_event_bus"
    SUPPORTS_SCHEMA_VALIDATION = "supports_schema_validation"
    SUPPORTS_ERROR_RECOVERY = "supports_error_recovery"
    SUPPORTS_EVENT_DISCOVERY = "supports_event_discovery"

    # Core functionality capabilities
    TELEMETRY_ENABLED = "telemetry_enabled"
    CACHING_ENABLED = "caching_enabled"
    MONITORING_ENABLED = "monitoring_enabled"
    RETRY_ENABLED = "retry_enabled"

    # Capability types (from capability factory)
    STANDARD = "standard"
    DEPRECATED = "deprecated"
    EXPERIMENTAL = "experimental"

    # Processing capabilities
    ASYNC_PROCESSING = "async_processing"
    STREAMING_SUPPORT = "streaming_support"
    PARALLEL_EXECUTION = "parallel_execution"

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value

    @classmethod
    def get_support_capabilities(cls) -> list[EnumNodeCapability]:
        """Get support-based capabilities."""
        return [
            cls.SUPPORTS_DRY_RUN,
            cls.SUPPORTS_BATCH_PROCESSING,
            cls.SUPPORTS_CUSTOM_HANDLERS,
            cls.SUPPORTS_CORRELATION_ID,
            cls.SUPPORTS_EVENT_BUS,
            cls.SUPPORTS_SCHEMA_VALIDATION,
            cls.SUPPORTS_ERROR_RECOVERY,
            cls.SUPPORTS_EVENT_DISCOVERY,
        ]

    @classmethod
    def get_core_capabilities(cls) -> list[EnumNodeCapability]:
        """Get core functionality capabilities."""
        return [
            cls.TELEMETRY_ENABLED,
            cls.CACHING_ENABLED,
            cls.MONITORING_ENABLED,
            cls.RETRY_ENABLED,
        ]

    @classmethod
    def get_processing_capabilities(cls) -> list[EnumNodeCapability]:
        """Get processing-based capabilities."""
        return [
            cls.ASYNC_PROCESSING,
            cls.STREAMING_SUPPORT,
            cls.PARALLEL_EXECUTION,
        ]

    @classmethod
    def get_capability_types(cls) -> list[EnumNodeCapability]:
        """Get capability type categories."""
        return [cls.STANDARD, cls.DEPRECATED, cls.EXPERIMENTAL]

    @classmethod
    def is_support_capability(cls, capability: EnumNodeCapability) -> bool:
        """Check if capability is a support-based capability."""
        return capability in cls.get_support_capabilities()

    @classmethod
    def is_core_capability(cls, capability: EnumNodeCapability) -> bool:
        """Check if capability is a core functionality capability."""
        return capability in cls.get_core_capabilities()

    @classmethod
    def is_deprecated(cls, capability: EnumNodeCapability) -> bool:
        """Check if capability is deprecated."""
        return capability == cls.DEPRECATED


# Export for use
__all__ = ["EnumNodeCapability"]