"""
Protocol for representing a capability dependency for a handler.

Domain: Handler contract type definitions for capability requirements.

This module defines ProtocolCapabilityDependency which declares that a handler
requires or optionally uses a specific capability provided by the runtime.

See Also:
    - protocol_handler_contract.py: Aggregates capability dependencies
    - ProtocolServiceRegistry: Provides capability discovery
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ProtocolCapabilityDependency(Protocol):
    """
    Protocol for representing a capability dependency for a handler.

    A capability dependency declares that a handler requires or optionally
    uses a specific capability provided by the runtime environment. This
    enables dependency injection, capability checking at registration time,
    and graceful degradation when optional capabilities are unavailable.

    Capability dependencies support:
        - Required vs optional capabilities
        - Semantic version constraints for version matching
        - Runtime capability discovery and injection
        - Handler validation before execution

    This protocol is useful for:
        - Handler registration validation
        - Dependency injection configuration
        - Feature flag integration
        - Graceful degradation strategies
        - Capability-based security models

    Attributes:
        capability_name: Identifier for the required capability.
        required: Whether the capability must be present for the handler to work.
        version_constraint: Optional semantic version constraint string.

    Example:
        ```python
        class DatabaseCapabilityDep:
            '''Dependency on PostgreSQL database capability.'''

            @property
            def capability_name(self) -> str:
                return "database.postgresql"

            @property
            def required(self) -> bool:
                return True  # Handler cannot function without database

            @property
            def version_constraint(self) -> str | None:
                return ">=14.0.0"  # Requires PostgreSQL 14+

        class CacheCapabilityDep:
            '''Optional dependency on Redis cache.'''

            @property
            def capability_name(self) -> str:
                return "cache.redis"

            @property
            def required(self) -> bool:
                return False  # Handler works without cache, just slower

            @property
            def version_constraint(self) -> str | None:
                return None  # Any version acceptable

        db_dep = DatabaseCapabilityDep()
        cache_dep = CacheCapabilityDep()

        assert isinstance(db_dep, ProtocolCapabilityDependency)

        # Runtime checks capabilities before handler execution
        if db_dep.required and not runtime.has_capability(db_dep.capability_name):
            raise MissingCapabilityError(db_dep.capability_name)
        ```

    Note:
        Capability names should follow a hierarchical naming convention
        (e.g., "database.postgresql", "cache.redis", "messaging.kafka")
        to enable namespace-based capability discovery and grouping.

    See Also:
        ProtocolHandlerContract: Aggregates capability dependencies.
        ProtocolServiceRegistry: Provides capability discovery.
    """

    @property
    def capability_name(self) -> str:
        """
        Name of the required capability.

        The capability name serves as a unique identifier for the capability
        within the runtime environment. Names should follow a hierarchical
        dotted notation for organization and discovery.

        Naming Convention:
            - Format: "{category}.{specific}" or "{category}.{subcategory}.{specific}"
            - Examples: "database.postgresql", "cache.redis", "auth.oauth2.google"
            - Case: lowercase with dots as separators

        Common Capability Categories:
            - "database.*": Database connections (postgresql, mysql, mongodb)
            - "cache.*": Caching systems (redis, memcached)
            - "messaging.*": Message brokers (kafka, rabbitmq)
            - "storage.*": Object storage (s3, gcs, azure)
            - "auth.*": Authentication providers
            - "metrics.*": Metrics and monitoring systems

        Returns:
            String identifier for the capability (e.g., "database.postgresql").
        """
        ...

    @property
    def required(self) -> bool:
        """
        Whether this capability is required (vs optional).

        Required capabilities must be available for the handler to function.
        Optional capabilities enhance handler functionality but the handler
        can operate without them, possibly with reduced functionality.

        Behavior by Setting:
            - True (required): Handler registration fails if capability missing
            - False (optional): Handler proceeds, may use fallback behavior

        Returns:
            True if the capability is required, False if optional.
        """
        ...

    @property
    def version_constraint(self) -> str | None:
        """
        Optional semantic version constraint for the capability.

        Version constraints follow semantic versioning (semver) syntax to
        specify compatible capability versions. This enables handlers to
        declare minimum versions, exact versions, or version ranges.

        Supported Constraint Syntax:
            - ">=1.0.0": Version 1.0.0 or higher
            - ">=1.0.0,<2.0.0": Version 1.x only
            - "==1.2.3": Exact version match
            - "^1.0.0": Compatible with 1.0.0 (same as >=1.0.0,<2.0.0)
            - "~1.2.0": Approximately 1.2.0 (same as >=1.2.0,<1.3.0)

        Examples:
            - ">=14.0.0" for PostgreSQL 14+
            - ">=6.0.0,<8.0.0" for Redis 6.x or 7.x
            - None for any version acceptable

        Returns:
            Semantic version constraint string, or None if any version
            is acceptable. Constraint syntax follows Python packaging
            version specifier conventions (PEP 440).
        """
        ...


__all__ = ["ProtocolCapabilityDependency"]
