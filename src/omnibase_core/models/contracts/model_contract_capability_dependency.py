"""
Capability Dependency Model for Handler Contracts.

This module defines ModelCapabilityDependency, which declares dependencies on
capabilities using the vendor-agnostic requirements pattern. Contracts declare
capabilities and constraints; the registry resolves to concrete providers.

Core Principle:
    "Contracts declare capabilities + constraints. Registry resolves to providers."

Vendors never appear in consumer contracts. Dependencies are expressed as
capability requirements with graduated strictness (must/prefer/forbid/hints).

Example:
    >>> dep = ModelCapabilityDependency(
    ...     alias="db",
    ...     capability="database.relational",
    ...     requirements=ModelRequirementSet(
    ...         must={"supports_transactions": True},
    ...         prefer={"max_latency_ms": 20},
    ...     ),
    ...     selection_policy="auto_if_unique",
    ... )
    >>> dep.alias
    'db'

See Also:
    - OMN-1117: Handler Contract Model & YAML Schema
    - ModelRequirementSet: Requirement specification with must/prefer/forbid/hints
    - ModelDependencySpec: Discovery-based dependency specification

.. versionadded:: 0.4.1
"""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.models.capabilities.model_capability_requirement_set import (
    ModelRequirementSet,
)

# Selection policy determines how the registry resolves multiple matching providers
SelectionPolicy = Literal["auto_if_unique", "best_score", "require_explicit"]


class ModelCapabilityDependency(BaseModel):
    """
    Vendor-agnostic capability dependency declaration.

    Declares a dependency on a capability (not a vendor) with graduated
    requirements. The registry resolves capability requirements to concrete
    provider instances at runtime.

    Attributes:
        alias: Local name for binding in handler code (e.g., "db", "cache").
            Used to reference the resolved provider in the handler implementation.
        capability: Capability identifier (e.g., "database.relational", "vector_store").
            Uses dot-notation for hierarchical capabilities.
        requirements: Requirement set with must/prefer/forbid/hints.
            Wraps ModelRequirementSet for capability-specific constraints.
        selection_policy: Policy for selecting among multiple matching providers.
            - auto_if_unique: Auto-select if exactly one match, else require explicit
            - best_score: Select highest-scoring match based on requirements
            - require_explicit: Always require explicit provider configuration
        strict: If True, missing capability is a fatal error. If False, handler
            can operate in degraded mode without this capability.
        version_range: Optional semver range for capability version matching
            (e.g., ">=1.0.0 <2.0.0", "^1.2.3").
        vendor_hints: Optional non-binding hints about vendor preferences.
            Does not affect matching, only for documentation/debugging.
        description: Human-readable description of why this capability is needed.

    Example:
        >>> # Database dependency with transaction support
        >>> db_dep = ModelCapabilityDependency(
        ...     alias="db",
        ...     capability="database.relational",
        ...     requirements=ModelRequirementSet(
        ...         must={"supports_transactions": True},
        ...         prefer={"max_latency_ms": 20},
        ...         forbid={"deprecated": True},
        ...     ),
        ...     selection_policy="auto_if_unique",
        ...     strict=True,
        ... )

        >>> # Optional cache dependency
        >>> cache_dep = ModelCapabilityDependency(
        ...     alias="cache",
        ...     capability="cache.distributed",
        ...     requirements=ModelRequirementSet(
        ...         prefer={"eviction_policy": "lru"},
        ...     ),
        ...     strict=False,  # Handler can work without cache
        ...     description="Optional distributed cache for performance",
        ... )

    Thread Safety:
        This model is immutable (frozen=True) and safe for concurrent access.

    See Also:
        - ModelRequirementSet: The requirement specification model
        - ModelDependencySpec: Discovery-based dependency specification
        - OMN-1117: Handler Contract Model & YAML Schema
    """

    alias: str = Field(
        ...,
        min_length=1,
        max_length=64,
        pattern=r"^[a-z][a-z0-9_]*$",
        description="Local name for binding in handler code (lowercase snake_case)",
    )

    capability: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Capability identifier using dot-notation (e.g., 'database.relational')",
    )

    requirements: ModelRequirementSet = Field(
        default_factory=ModelRequirementSet,
        description="Requirement set with must/prefer/forbid/hints constraints",
    )

    selection_policy: SelectionPolicy = Field(
        default="auto_if_unique",
        description="Policy for selecting among multiple matching providers",
    )

    strict: bool = Field(
        default=True,
        description="If True, missing capability is fatal. If False, allows degraded mode.",
    )

    version_range: str | None = Field(  # string-version-ok: semver range expression
        default=None,
        description="Optional semver range for capability version (e.g., '>=1.0.0 <2.0.0')",
    )

    # ONEX_EXCLUDE: dict_str_any - vendor hints are arbitrary key-value pairs
    vendor_hints: dict[str, Any] = Field(
        default_factory=dict,
        description="Non-binding vendor preference hints (documentation only)",
    )

    description: str | None = Field(
        default=None,
        max_length=500,
        description="Human-readable description of why this capability is needed",
    )

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
        str_strip_whitespace=True,
    )

    @field_validator("capability")
    @classmethod
    def validate_capability_format(cls, v: str) -> str:
        """
        Validate capability uses dot-notation and has valid segments.

        Args:
            v: The capability string.

        Returns:
            The validated capability string.

        Raises:
            ValueError: If capability format is invalid.
        """
        if not v or not v.strip():
            raise ValueError("capability cannot be empty")

        # Must contain at least one segment
        segments = v.split(".")
        for segment in segments:
            if not segment:
                raise ValueError(f"capability '{v}' contains empty segment")
            if not segment[0].isalpha():
                raise ValueError(
                    f"capability segment '{segment}' must start with a letter"
                )
            if not all(c.isalnum() or c == "_" for c in segment):
                raise ValueError(
                    f"capability segment '{segment}' must be alphanumeric with underscores"
                )

        return v

    def matches_provider(
        self,
        # ONEX_EXCLUDE: dict_str_any - provider capability mapping
        provider: dict[str, Any],
    ) -> tuple[bool, float, list[str]]:
        """
        Check if a provider satisfies this capability dependency.

        Delegates to the requirements set for matching logic.

        Args:
            provider: Provider capability mapping to check.

        Returns:
            Tuple of (matches: bool, score: float, warnings: list[str]).
        """
        return self.requirements.matches(provider)

    def is_optional(self) -> bool:
        """
        Check if this dependency is optional (strict=False).

        Returns:
            True if handler can operate without this capability.
        """
        return not self.strict


__all__ = [
    "ModelCapabilityDependency",
    "SelectionPolicy",
]
