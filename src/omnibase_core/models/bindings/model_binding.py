"""
Binding Model for Capability Resolution.

Records the resolution of a capability dependency to a provider. A binding
represents the result of the resolution process, capturing what was requested,
what was resolved, and metadata about the resolution decision.

This module provides:
    - :class:`ModelBinding`: Pydantic model recording a resolved capability binding

Core Principle:
    "Bindings are the output of resolution - they record which provider
    was selected to satisfy a capability dependency."

Resolution Flow:
    1. Handler declares capability dependencies (ModelCapabilityDependency)
    2. Resolver matches dependencies to providers (ModelProviderDescriptor)
    3. Resolution produces bindings (ModelBinding) recording the match
    4. Bindings are used at runtime to inject the correct adapter

Capability Naming Convention:
    Capabilities follow the pattern: ``<domain>.<type>[.<variant>]``

    Examples:
        - ``database.relational`` - Any relational database
        - ``storage.vector`` - Vector storage capability
        - ``cache.distributed`` - Distributed cache

Example Usage:
    >>> from datetime import datetime, timezone
    >>> from omnibase_core.models.bindings import ModelBinding
    >>>
    >>> # Create a binding recording the resolution
    >>> binding = ModelBinding(
    ...     dependency_alias="db",
    ...     capability="database.relational",
    ...     resolved_provider="550e8400-e29b-41d4-a716-446655440000",
    ...     adapter="omnibase_infra.adapters.PostgresAdapter",
    ...     connection_ref="secrets://postgres/primary",
    ...     requirements_hash="a1b2c3d4e5f6",
    ...     resolution_profile="production",
    ...     resolved_at=datetime.now(timezone.utc),
    ...     resolution_notes=["Selected based on transaction support requirement"],
    ...     candidates_considered=3,
    ... )
    >>>
    >>> binding.dependency_alias
    'db'

Integration with Capability Resolution:
    ModelBinding is the output of the capability resolution process:

    .. code-block:: python

        # Resolution produces bindings
        bindings = resolver.resolve(
            dependencies=handler.capability_dependencies,
            resolution_profile="production",
        )

        # Bindings map aliases to providers
        for binding in bindings:
            print(f"{binding.dependency_alias} -> {binding.adapter}")

See Also:
    - :class:`~omnibase_core.models.capabilities.ModelCapabilityDependency`:
      Input to resolution (what is requested)
    - :class:`~omnibase_core.models.providers.ModelProviderDescriptor`:
      Provider registry entry (what is available)

Thread Safety:
    This model is immutable (frozen=True) after creation, making it
    thread-safe for concurrent read access.

.. versionadded:: 0.4.0
    Initial implementation as part of OMN-1155 capability resolution models.
"""

import logging
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError

_logger = logging.getLogger(__name__)


class ModelBinding(BaseModel):
    """Records the resolution of a capability dependency to a provider.

    A binding captures the complete result of capability resolution, including:
    - What was requested (dependency_alias, capability)
    - What was selected (resolved_provider, adapter, connection_ref)
    - Resolution context (requirements_hash, resolution_profile, resolved_at)
    - Audit information (resolution_notes, candidates_considered)

    Bindings are immutable records that can be cached, serialized, and used
    to reconstruct the resolution state for debugging or replay.

    Attributes:
        dependency_alias: The alias from ModelCapabilityDependency that was
            resolved. This is the local name used in handler code to reference
            the resolved provider (e.g., "db", "cache", "vectors").
        capability: The capability identifier that was requested. Follows
            the dotted notation pattern (e.g., "database.relational").
        resolved_provider: The UUID of the selected provider as a string. Uses
            string representation for JSON serialization compatibility.
        adapter: Python import path for the adapter class that provides
            the capability (e.g., "omnibase_infra.adapters.PostgresAdapter").
        connection_ref: Reference to connection configuration for the
            provider (e.g., "secrets://postgres/primary").
        requirements_hash: Hash of the requirements that were used for
            resolution. Used for cache invalidation - if requirements
            change, cached bindings become invalid.
        resolution_profile: Identifier of the profile that influenced resolution.
            Profiles can affect provider selection, scoring, and preferences.
        resolved_at: Timestamp when this binding was created. Used for
            cache expiration and audit trails.
        resolution_notes: List of human-readable notes explaining why this
            provider was selected. Useful for debugging and auditing.
        candidates_considered: Number of providers that were evaluated
            during resolution. Useful for performance analysis and debugging.

    Examples:
        Basic binding creation:

        >>> from datetime import datetime, timezone
        >>> binding = ModelBinding(
        ...     dependency_alias="db",
        ...     capability="database.relational",
        ...     resolved_provider="550e8400-e29b-41d4-a716-446655440000",
        ...     adapter="omnibase_infra.adapters.PostgresAdapter",
        ...     connection_ref="secrets://postgres/primary",
        ...     requirements_hash="sha256:abc123",
        ...     resolution_profile="production",
        ...     resolved_at=datetime.now(timezone.utc),
        ... )

        Binding with audit trail:

        >>> binding_with_notes = ModelBinding(
        ...     dependency_alias="cache",
        ...     capability="cache.distributed",
        ...     resolved_provider="660e8400-e29b-41d4-a716-446655440001",
        ...     adapter="omnibase_infra.adapters.RedisAdapter",
        ...     connection_ref="secrets://redis/primary",
        ...     requirements_hash="sha256:def456",
        ...     resolution_profile="production",
        ...     resolved_at=datetime.now(timezone.utc),
        ...     resolution_notes=[
        ...         "Selected redis provider for cache.distributed",
        ...         "Matched region preference: us-east-1",
        ...         "Highest score among 3 candidates",
        ...     ],
        ...     candidates_considered=3,
        ... )

    Note:
        **Why from_attributes=True is Required**

        This model uses ``from_attributes=True`` in its ConfigDict to ensure
        pytest-xdist compatibility. When running tests with pytest-xdist,
        each worker process imports classes independently, creating separate
        class objects. Without ``from_attributes=True``, Pydantic rejects
        valid instances due to class identity differences across workers.

        See CLAUDE.md "Pydantic from_attributes=True for Value Objects" section
        for the project convention.

        **Thread Safety**: This model is frozen (immutable) after creation,
        making it thread-safe for concurrent read access from multiple threads
        or async tasks. Use ``model_copy()`` to create modified copies when
        needed.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    # What was resolved
    dependency_alias: str = Field(
        ...,
        description=(
            "Local name from ModelCapabilityDependency.alias that was resolved "
            "(e.g., 'db', 'cache', 'vectors')"
        ),
        min_length=1,
        max_length=64,
    )

    capability: str = Field(
        ...,
        description=(
            "Capability identifier that was requested "
            "(e.g., 'database.relational', 'storage.vector')"
        ),
        min_length=3,
        max_length=128,
    )

    # What it resolved to
    resolved_provider: str = Field(
        ...,
        description=(
            "UUID of the selected provider as a string for JSON serialization "
            "(e.g., '550e8400-e29b-41d4-a716-446655440000')"
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
            "Connection reference for the provider "
            "(e.g., 'secrets://postgres/primary', 'env://DB_URL')"
        ),
        min_length=1,
    )

    # Resolution metadata
    requirements_hash: str = Field(
        ...,
        description=(
            "Hash of requirements used for resolution. "
            "Cache key for invalidation when requirements change."
        ),
        min_length=1,
    )

    resolution_profile: str = Field(
        ...,
        description=(
            "Identifier of the profile that influenced resolution. "
            "Profiles affect provider selection and scoring."
        ),
        min_length=1,
    )

    resolved_at: datetime = Field(
        ...,
        description="Timestamp when this binding was created (UTC recommended)",
    )

    # Audit trail
    resolution_notes: list[str] = Field(
        default_factory=list,
        description=(
            "Human-readable notes explaining why this provider was selected. "
            "Useful for debugging and auditing resolution decisions."
        ),
    )

    candidates_considered: int = Field(
        default=0,
        description=(
            "Number of providers evaluated during resolution. "
            "Useful for performance analysis."
        ),
        ge=0,
    )

    @field_validator("dependency_alias", mode="after")
    @classmethod
    def validate_dependency_alias(cls, v: str) -> str:
        """Validate that dependency_alias is non-empty after stripping.

        Args:
            v: The alias string to validate.

        Returns:
            The validated alias string (stripped of whitespace).

        Raises:
            ModelOnexError: If the alias is empty or whitespace-only.

        Note:
            Length validation (min_length=1, max_length=64) is enforced by
            Pydantic's field constraints. This validator handles whitespace.
        """
        stripped = v.strip()
        if not stripped:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="dependency_alias cannot be empty or whitespace-only",
                context={"dependency_alias": v},
            )
        return stripped

    @field_validator("capability", mode="after")
    @classmethod
    def validate_capability(cls, v: str) -> str:
        """Validate that capability is non-empty after stripping.

        Args:
            v: The capability string to validate.

        Returns:
            The validated capability string (stripped of whitespace).

        Raises:
            ModelOnexError: If the capability is empty or whitespace-only.

        Note:
            This validator only ensures non-empty. Full capability format
            validation is done at the dependency level (ModelCapabilityDependency).
        """
        stripped = v.strip()
        if not stripped:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="capability cannot be empty or whitespace-only",
                context={"capability": v},
            )
        return stripped

    @field_validator("resolved_provider", mode="after")
    @classmethod
    def validate_resolved_provider(cls, v: str) -> str:
        """Validate that resolved_provider is non-empty after stripping.

        Args:
            v: The provider ID string to validate.

        Returns:
            The validated provider ID string (stripped of whitespace).

        Raises:
            ModelOnexError: If the resolved_provider is empty or whitespace-only.

        Note:
            This validator only ensures non-empty. UUID format validation
            is intentionally not enforced to allow flexibility in ID formats.
        """
        stripped = v.strip()
        if not stripped:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="resolved_provider cannot be empty or whitespace-only",
                context={"resolved_provider": v},
            )
        return stripped

    @field_validator("adapter", mode="after")
    @classmethod
    def validate_adapter(cls, v: str) -> str:
        """Validate that adapter is non-empty after stripping.

        Args:
            v: The adapter path string to validate.

        Returns:
            The validated adapter string (stripped of whitespace).

        Raises:
            ModelOnexError: If the adapter is empty or whitespace-only.

        Note:
            Full import path validation (dots, identifiers) is done at the
            provider level (ModelProviderDescriptor).
        """
        stripped = v.strip()
        if not stripped:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="adapter cannot be empty or whitespace-only",
                context={"adapter": v},
            )
        return stripped

    @field_validator("connection_ref", mode="after")
    @classmethod
    def validate_connection_ref(cls, v: str) -> str:
        """Validate that connection_ref is non-empty after stripping.

        Args:
            v: The connection reference string to validate.

        Returns:
            The validated connection reference (stripped of whitespace).

        Raises:
            ModelOnexError: If the connection_ref is empty or whitespace-only.

        Note:
            Full connection reference format validation (scheme://) is done
            at the provider level (ModelProviderDescriptor).
        """
        stripped = v.strip()
        if not stripped:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="connection_ref cannot be empty or whitespace-only",
                context={"connection_ref": v},
            )
        return stripped

    @field_validator("requirements_hash", mode="after")
    @classmethod
    def validate_requirements_hash(cls, v: str) -> str:
        """Validate that requirements_hash is non-empty after stripping.

        Args:
            v: The hash string to validate.

        Returns:
            The validated hash string (stripped of whitespace).

        Raises:
            ModelOnexError: If the requirements_hash is empty or whitespace-only.
        """
        stripped = v.strip()
        if not stripped:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="requirements_hash cannot be empty or whitespace-only",
                context={"requirements_hash": v},
            )
        return stripped

    @field_validator("resolution_profile", mode="after")
    @classmethod
    def validate_resolution_profile(cls, v: str) -> str:
        """Validate that resolution_profile is non-empty after stripping.

        Args:
            v: The profile ID string to validate.

        Returns:
            The validated profile ID string (stripped of whitespace).

        Raises:
            ModelOnexError: If the resolution_profile is empty or whitespace-only.
        """
        stripped = v.strip()
        if not stripped:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="resolution_profile cannot be empty or whitespace-only",
                context={"resolution_profile": v},
            )
        return stripped

    @field_validator("resolution_notes", mode="before")
    @classmethod
    def validate_resolution_notes(cls, v: Any) -> list[str]:
        """Validate and filter resolution notes.

        Strips whitespace from each note and removes empty notes.

        Note:
            Uses ``Any`` type hint because ``mode="before"`` receives raw input
            before Pydantic type coercion. The input could be any type.

        Args:
            v: Raw input value (expected to be a list of strings).

        Returns:
            List of non-empty notes with whitespace stripped.

        Raises:
            ModelOnexError: If input is not a list or contains non-string items.
        """
        if v is None:
            return []

        if not isinstance(v, list):
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"resolution_notes must be a list, got {type(v).__name__}",
                context={"value": v, "type": type(v).__name__},
            )

        validated: list[str] = []
        for note in v:
            if not isinstance(note, str):
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=f"resolution_note must be a string, got {type(note).__name__}",
                    context={"note": note, "note_type": type(note).__name__},
                )
            stripped = note.strip()
            if stripped:  # Only include non-empty notes
                validated.append(stripped)

        # Log when notes are filtered for visibility
        filtered_count = len(v) - len(validated)
        if filtered_count > 0:
            _logger.debug(
                "Filtered %d empty/whitespace resolution notes",
                filtered_count,
            )

        return validated

    def __repr__(self) -> str:
        """Return a concise representation for debugging.

        Returns:
            String representation showing alias, capability, and resolved_provider.

        Examples:
            >>> from datetime import datetime, timezone
            >>> binding = ModelBinding(
            ...     dependency_alias="db",
            ...     capability="database.relational",
            ...     resolved_provider="550e8400-e29b-41d4-a716-446655440000",
            ...     adapter="test.Adapter",
            ...     connection_ref="env://TEST",
            ...     requirements_hash="hash123",
            ...     resolution_profile="prod",
            ...     resolved_at=datetime.now(timezone.utc),
            ... )
            >>> "db -> database.relational" in repr(binding)
            True
        """
        return (
            f"ModelBinding("
            f"alias={self.dependency_alias!r}, "
            f"capability={self.capability!r}, "
            f"resolved_provider={self.resolved_provider!r})"
        )

    def __str__(self) -> str:
        """Return concise string representation.

        Returns:
            String in format 'alias -> capability @ resolved_provider'.

        Examples:
            >>> from datetime import datetime, timezone
            >>> binding = ModelBinding(
            ...     dependency_alias="db",
            ...     capability="database.relational",
            ...     resolved_provider="550e8400",
            ...     adapter="test.Adapter",
            ...     connection_ref="env://TEST",
            ...     requirements_hash="hash123",
            ...     resolution_profile="prod",
            ...     resolved_at=datetime.now(timezone.utc),
            ... )
            >>> str(binding)
            'db -> database.relational @ 550e8400'
        """
        return (
            f"{self.dependency_alias} -> {self.capability} @ {self.resolved_provider}"
        )

    def __eq__(self, other: object) -> bool:
        """Compare bindings by identity fields for deduplication consistency.

        Compares only identity fields (dependency_alias, capability, resolved_provider)
        to match ``__hash__`` behavior. This ensures the hash/equality contract
        is satisfied: if ``hash(a) == hash(b)``, then ``a == b`` must also be
        possible to return True.

        Metadata fields (resolved_at, resolution_notes, candidates_considered,
        adapter, connection_ref, requirements_hash, resolution_profile) are intentionally
        NOT compared. Two bindings representing the same logical resolution
        (same alias, capability, and provider) are considered equal even if they
        have different timestamps or audit metadata.

        This design enables proper deduplication in sets and dicts where we want
        to treat bindings with the same identity as duplicates regardless of
        when they were created or what notes were attached.

        Args:
            other: Object to compare against.

        Returns:
            True if other is a ModelBinding with matching identity fields.
            NotImplemented if other is not a ModelBinding (enables Python's
            comparison protocol to try the reverse comparison).

        Examples:
            >>> from datetime import datetime, timezone
            >>> t1 = datetime(2024, 1, 1, tzinfo=timezone.utc)
            >>> t2 = datetime(2024, 6, 1, tzinfo=timezone.utc)
            >>> b1 = ModelBinding(
            ...     dependency_alias="db", capability="database.relational",
            ...     resolved_provider="uuid-1", adapter="pkg.Adapter",
            ...     connection_ref="env://DB", requirements_hash="h1",
            ...     resolution_profile="prod", resolved_at=t1,
            ... )
            >>> b2 = ModelBinding(
            ...     dependency_alias="db", capability="database.relational",
            ...     resolved_provider="uuid-1", adapter="pkg.Adapter",
            ...     connection_ref="env://DB", requirements_hash="h1",
            ...     resolution_profile="prod", resolved_at=t2,  # Different timestamp
            ... )
            >>> b1 == b2  # Same identity, different metadata
            True
            >>> hash(b1) == hash(b2)
            True

        See Also:
            ``__hash__``: Uses the same identity fields for consistency.
        """
        if not isinstance(other, ModelBinding):
            return NotImplemented
        return (
            self.dependency_alias == other.dependency_alias
            and self.capability == other.capability
            and self.resolved_provider == other.resolved_provider
        )

    def __hash__(self) -> int:
        """Enable use in sets and as dict keys for binding deduplication.

        Hash is computed from identity fields (dependency_alias, capability,
        resolved_provider). Metadata fields (resolved_at, resolution_notes, etc.) are
        not included since two bindings with the same resolution but different
        timestamps should hash to the same value for deduplication purposes.

        This method is paired with ``__eq__`` which compares the same fields,
        ensuring the hash/equality contract is satisfied: objects that compare
        equal have the same hash value.

        Returns:
            Hash value computed from (dependency_alias, capability, resolved_provider).

        See Also:
            ``__eq__``: Uses the same identity fields for consistency.
        """
        return hash((self.dependency_alias, self.capability, self.resolved_provider))


__all__ = ["ModelBinding"]
