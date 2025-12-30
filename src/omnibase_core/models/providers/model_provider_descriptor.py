# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
Provider Descriptor Model.

Describes a concrete provider instance registered in the registry. Providers
are instances that offer specific capabilities, and resolution matches
capability requirements to available providers.

This module provides:
    - :class:`ModelProviderDescriptor`: Pydantic model describing a provider instance
    - Validation for capability naming patterns and connection references

Core Principle:
    "Providers are instances registered in the registry.
    Resolution matches capabilities to providers."

Feature Resolution Precedence:
    observed_features takes precedence over declared_features when both
    are present. Observed features represent runtime-probed reality,
    while declared features are static claims that may become stale.

Capability Naming Convention:
    Capabilities follow a hierarchical dotted notation using lowercase
    alphanumeric characters. Examples:
        - "database.relational"
        - "cache.redis"
        - "storage.s3"
        - "messaging.kafka"

Example Usage:
    >>> from uuid import uuid4
    >>> from omnibase_core.models.providers import ModelProviderDescriptor
    >>>
    >>> # Create a provider descriptor
    >>> descriptor = ModelProviderDescriptor(
    ...     provider_id=uuid4(),
    ...     capabilities=["database.relational", "database.postgresql"],
    ...     adapter="omnibase_infra.adapters.PostgresAdapter",
    ...     connection_ref="secrets://postgres/primary",
    ...     attributes={"version": "15.4", "region": "us-east-1"},
    ...     tags=["production", "primary"],
    ... )
    >>>
    >>> # Get effective features (observed takes precedence)
    >>> features = descriptor.get_effective_features()

See Also:
    - :class:`~omnibase_core.models.health.model_health_status.ModelHealthStatus`:
      Rich health status for providers
    - :class:`~omnibase_core.models.providers.model_capability_requirement.ModelCapabilityRequirement`:
      Capability requirements for resolution

.. versionadded:: 0.4.0
    Initial implementation as part of OMN-1153 provider registry models.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.types.json_types import JsonValue

if TYPE_CHECKING:
    from omnibase_core.models.health.model_health_status import ModelHealthStatus

    # Type alias for health field - uses ModelHealthStatus for type checking
    HealthStatusType = ModelHealthStatus | None
else:
    # At runtime, use Any to avoid circular import issues
    HealthStatusType = Any

# Capability naming pattern: lowercase alphanumeric with dots, at least one dot
# Examples: "database.relational", "cache.redis", "storage.s3"
_CAPABILITY_PATTERN = re.compile(r"^[a-z0-9]+(\.[a-z0-9]+)+$")


class ModelProviderDescriptor(BaseModel):
    """Describes a concrete provider instance registered in the registry.

    Providers are instances that offer specific capabilities. Resolution
    matches capability requirements to available providers.

    Core Principle:
        "Providers are instances registered in the registry.
        Resolution matches capabilities to providers."

    Feature Resolution Precedence:
        observed_features takes precedence over declared_features when both
        are present. Observed features represent runtime-probed reality,
        while declared features are static claims that may become stale.

    Attributes:
        provider_id: Unique UUID identifier for this provider instance.
        capabilities: List of capability identifiers this provider offers.
            Each capability must follow the dotted notation pattern
            (e.g., "database.relational", "cache.redis").
        adapter: Python import path for the adapter class
            (e.g., "omnibase_infra.adapters.PostgresAdapter").
        connection_ref: Reference to connection configuration. Must contain
            a scheme separator "://" (e.g., "secrets://postgres/primary").
        attributes: Static attributes describing the provider (version, region,
            deployment tier, etc.). Immutable after registration.
        declared_features: Features the adapter claims to support. Static
            declaration that may become stale over time.
        observed_features: Runtime-probed capabilities that reflect the
            actual state of the provider. Takes precedence over declared_features.
        tags: Tags for filtering and categorization
            (e.g., "production", "us-east", "primary").
        health: Current health status of this provider. Updated by health
            probes and monitoring systems. Uses ModelHealthStatus for rich
            health tracking including scores, metrics, and issue tracking.

    Examples:
        Create a database provider descriptor:

        >>> from uuid import uuid4
        >>> descriptor = ModelProviderDescriptor(
        ...     provider_id=uuid4(),
        ...     capabilities=["database.relational", "database.postgresql"],
        ...     adapter="omnibase_infra.adapters.PostgresAdapter",
        ...     connection_ref="secrets://postgres/primary",
        ...     attributes={"version": "15.4", "max_connections": 100},
        ...     declared_features={"supports_json": True, "supports_arrays": True},
        ...     tags=["production", "us-east-1"],
        ... )

        Get effective features with precedence:

        >>> # When observed_features is empty, declared_features is used
        >>> descriptor.get_effective_features()
        {'supports_json': True, 'supports_arrays': True}
        >>>
        >>> # When observed_features has data, it takes precedence
        >>> # (even if declared_features also has data)

    Note:
        This model is frozen (immutable) after creation, making it thread-safe
        for concurrent read access. Use model_copy() to create modified copies.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    provider_id: UUID = Field(
        ...,
        description="Unique identifier for this provider instance",
    )

    capabilities: list[str] = Field(
        ...,
        description=(
            "Capability identifiers this provider offers. Each capability must "
            "follow the dotted notation pattern (e.g., 'database.relational'). "
            "At least one capability is required."
        ),
        min_length=1,
    )

    adapter: str = Field(
        ...,
        description=(
            "Python import path for the adapter class "
            "(e.g., 'omnibase_infra.adapters.PostgresAdapter')"
        ),
        min_length=1,
    )

    connection_ref: str = Field(
        ...,
        description=(
            "Reference to connection configuration. Must contain a scheme "
            "separator '://' (e.g., 'secrets://postgres/primary')"
        ),
        min_length=1,
    )

    attributes: dict[str, JsonValue] = Field(
        default_factory=dict,
        description="Static attributes (version, region, deployment tier, etc.)",
    )

    declared_features: dict[str, JsonValue] = Field(
        default_factory=dict,
        description="Features the adapter claims to support (static declaration)",
    )

    observed_features: dict[str, JsonValue] = Field(
        default_factory=dict,
        description="Runtime-probed capabilities (preferred over declared_features)",
    )

    tags: list[str] = Field(
        default_factory=list,
        description="Tags for filtering (e.g., 'production', 'us-east', 'primary')",
    )

    health: HealthStatusType = Field(
        default=None,
        description="Current health status of this provider",
    )

    @field_validator("capabilities", mode="before")
    @classmethod
    def validate_capabilities(cls, v: list[str]) -> list[str]:
        """Validate and normalize capability identifiers.

        Validates that each capability follows the dotted notation pattern
        (lowercase alphanumeric with dots, at least one dot). Also strips
        whitespace, deduplicates, rejects empty strings, and returns a
        sorted unique list.

        Args:
            v: List of capability strings to validate.

        Returns:
            Sorted list of unique, validated capability strings.

        Raises:
            ModelOnexError: If any capability is empty, contains only whitespace,
                or does not match the required pattern. Error code is VALIDATION_ERROR.

        Examples:
            Valid capabilities: ["database.relational", "cache.redis"]
            Invalid capabilities: ["DATABASE.RELATIONAL", "noDot", "", "  "]
        """
        if not v:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="At least one capability is required",
            )

        validated: set[str] = set()
        for cap in v:
            if not isinstance(cap, str):
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=f"Capability must be a string, got {type(cap).__name__}",
                )

            stripped = cap.strip()
            if not stripped:
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message="Capability cannot be empty or whitespace-only",
                )

            if not _CAPABILITY_PATTERN.match(stripped):
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=(
                        f"Invalid capability '{stripped}': must be lowercase "
                        "alphanumeric with dots, containing at least one dot "
                        "(e.g., 'database.relational', 'cache.redis')"
                    ),
                )

            validated.add(stripped)

        return sorted(validated)

    @field_validator("tags", mode="before")
    @classmethod
    def validate_tags(cls, v: list[str]) -> list[str]:
        """Validate and normalize tags.

        Strips whitespace, deduplicates, rejects empty strings, and returns
        a sorted list.

        Args:
            v: List of tag strings to validate.

        Returns:
            Sorted list of unique, validated tag strings.

        Raises:
            ModelOnexError: If any tag is empty or contains only whitespace.
                Error code is VALIDATION_ERROR.

        Examples:
            Valid: ["production", "us-east", "primary"]
            Invalid: ["", "  "]
        """
        if not v:
            return []

        validated: set[str] = set()
        for tag in v:
            if not isinstance(tag, str):
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=f"Tag must be a string, got {type(tag).__name__}",
                )

            stripped = tag.strip()
            if not stripped:
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message="Tag cannot be empty or whitespace-only",
                )

            validated.add(stripped)

        return sorted(validated)

    @field_validator("connection_ref")
    @classmethod
    def validate_connection_ref(cls, v: str) -> str:
        """Validate connection reference contains scheme pattern.

        Connection references must contain "://" to indicate a valid
        scheme (e.g., "secrets://", "env://", "vault://").

        Args:
            v: Connection reference string to validate.

        Returns:
            The validated connection reference (unchanged if valid).

        Raises:
            ModelOnexError: If the connection reference does not contain
                the "://" scheme separator. Error code is VALIDATION_ERROR.

        Examples:
            Valid: "secrets://postgres/primary", "env://DB_URL"
            Invalid: "postgres/primary", "just-a-string"
        """
        if "://" not in v:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=(
                    f"Invalid connection_ref '{v}': must contain scheme separator "
                    "'://' (e.g., 'secrets://postgres/primary', 'env://DB_URL')"
                ),
            )
        return v

    def get_effective_features(self) -> dict[str, JsonValue]:
        """Get effective features with observed taking precedence over declared.

        Returns observed_features if non-empty, otherwise returns declared_features.
        This implements the feature resolution precedence where runtime-probed
        capabilities (observed) are preferred over static declarations (declared).

        Returns:
            Dictionary of effective features. Returns observed_features if it
            contains any entries, otherwise returns declared_features.

        Examples:
            >>> from uuid import uuid4
            >>> # With observed features
            >>> desc = ModelProviderDescriptor(
            ...     provider_id=uuid4(),
            ...     capabilities=["db.sql"],
            ...     adapter="test.Adapter",
            ...     connection_ref="env://TEST",
            ...     declared_features={"feature_a": True},
            ...     observed_features={"feature_b": True},
            ... )
            >>> desc.get_effective_features()
            {'feature_b': True}
            >>>
            >>> # Without observed features, falls back to declared
            >>> desc2 = ModelProviderDescriptor(
            ...     provider_id=uuid4(),
            ...     capabilities=["db.sql"],
            ...     adapter="test.Adapter",
            ...     connection_ref="env://TEST",
            ...     declared_features={"feature_a": True},
            ... )
            >>> desc2.get_effective_features()
            {'feature_a': True}
        """
        if self.observed_features:
            return self.observed_features
        return self.declared_features

    def __repr__(self) -> str:
        """Return a concise representation for debugging.

        Returns:
            String representation showing provider_id and capabilities count.

        Examples:
            >>> from uuid import UUID
            >>> desc = ModelProviderDescriptor(
            ...     provider_id=UUID("12345678-1234-5678-1234-567812345678"),
            ...     capabilities=["database.relational", "database.postgresql"],
            ...     adapter="omnibase_infra.adapters.PostgresAdapter",
            ...     connection_ref="secrets://postgres/primary",
            ... )
            >>> repr(desc)
            "ModelProviderDescriptor(provider_id=UUID('12345678-1234-5678-1234-567812345678'), capabilities=2)"
        """
        return (
            f"ModelProviderDescriptor("
            f"provider_id={self.provider_id!r}, "
            f"capabilities={len(self.capabilities)})"
        )


__all__ = ["ModelProviderDescriptor"]
