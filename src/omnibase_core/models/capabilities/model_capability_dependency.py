# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
Capability Dependency Model for Vendor-Agnostic Dependency Declaration.

Provides a way to declare dependencies on capabilities (not vendors) in
handler contracts. The core principle is:

    "Contracts declare capabilities + constraints. Registry resolves to providers."

Vendors never appear in consumer contracts. Dependencies are expressed as
capability requirements that the registry resolves to concrete providers
at runtime.

Capability Naming Convention:
    Capabilities follow the pattern: ``<domain>.<type>[.<variant>]``

    - Tokens contain lowercase letters, digits, and underscores
    - Dots are semantic separators between tokens
    - Hyphens are NOT allowed (use underscores for multi-word tokens)

    Examples:
        - ``database.relational`` - Any relational database
        - ``database.document`` - Document/NoSQL database
        - ``storage.vector`` - Vector storage capability
        - ``storage.vector.qdrant`` - Qdrant-compatible vector store
        - ``messaging.event_bus`` - Event bus capability
        - ``cache.key_value`` - Key-value cache capability
        - ``cache.distributed`` - Distributed cache
        - ``secrets.vault`` - Secrets management
        - ``http.client`` - HTTP client capability

Selection Policies:
    - ``auto_if_unique`` - Auto-select if exactly one provider matches
    - ``best_score`` - Select highest-scoring provider based on preferences
    - ``require_explicit`` - Never auto-select; require explicit binding

Example Usage:
    >>> from omnibase_core.models.capabilities import (
    ...     ModelCapabilityDependency,
    ...     ModelRequirementSet,
    ... )
    >>>
    >>> # Database dependency with requirements
    >>> db_dep = ModelCapabilityDependency(
    ...     alias="db",
    ...     capability="database.relational",
    ...     requirements=ModelRequirementSet(
    ...         must={"supports_transactions": True},
    ...         prefer={"max_latency_ms": 20},
    ...         forbid={"scope": "public_internet"},
    ...     ),
    ...     selection_policy="auto_if_unique",
    ... )
    >>>
    >>> # Vector store with hints for preference
    >>> vectors_dep = ModelCapabilityDependency(
    ...     alias="vectors",
    ...     capability="storage.vector",
    ...     requirements=ModelRequirementSet(
    ...         must={"dimensions": 1536},
    ...         hints={"engine_preference": ["qdrant", "milvus"]},
    ...     ),
    ... )

Thread Safety:
    This model is immutable (frozen=True) after creation, making it
    thread-safe for concurrent read access.

.. versionadded:: 0.4.0
"""

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, field_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.capabilities.model_requirement_set import ModelRequirementSet
from omnibase_core.models.errors.model_onex_error import ModelOnexError

# Regex pattern for valid capability names
# Must be lowercase letters and digits, dot-separated tokens
# At least two tokens (one dot required): domain.type[.variant]
# Note: Single-character tokens are intentionally allowed (e.g., "a.b") to support
# short, idiomatic names common in capability systems. The min_length=3 field
# constraint ensures the overall capability has reasonable length ("a.b" is valid).
#
# Why hyphens are excluded: Dots serve as semantic separators (domain.type.variant),
# so allowing hyphens within tokens (e.g., "event-bus") would create ambiguity about
# token boundaries. Use underscores instead for multi-word tokens (e.g., "event_bus",
# "key_value"). This keeps the grammar unambiguous: dots separate, underscores join.
_CAPABILITY_PATTERN = re.compile(r"^[a-z0-9_]+(\.[a-z0-9_]+)+$")

# Regex pattern for valid alias names
# More permissive: lowercase letters, digits, underscores
# Single token (no dots), must start with letter
# Note: Single-character aliases are intentionally allowed (e.g., "a", "x") to support
# terse binding names in handler code. Common short aliases include "db", "c" (cache).
_ALIAS_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")

# Type alias for selection policies
SelectionPolicy = Literal["auto_if_unique", "best_score", "require_explicit"]


class ModelCapabilityDependency(BaseModel):
    """
    Declares a dependency on a capability with requirements.

    This model represents a vendor-agnostic dependency declaration used in
    handler contracts. Instead of depending on specific vendors (e.g., "postgres",
    "redis"), contracts declare dependencies on capabilities with requirements
    that the registry resolves to providers at runtime.

    Attributes:
        alias: Local name for binding in the handler context. Used to reference
            the resolved provider in handler code (e.g., "db", "cache", "vectors").
            Must be lowercase letters, digits, or underscores, starting with a letter.
        capability: Capability identifier following the naming convention
            ``<domain>.<type>[.<variant>]``. Tokens may contain lowercase letters,
            digits, and underscores (no hyphens). Examples: "database.relational",
            "storage.vector", "cache.key_value".
        requirements: Constraint set defining must/prefer/forbid/hints for
            provider matching. See ModelRequirementSet for details.
        selection_policy: How to select among matching providers:
            - ``auto_if_unique``: Auto-select if exactly one matches
            - ``best_score``: Select highest-scoring based on preferences
            - ``require_explicit``: Never auto-select; require explicit binding
        strict: Controls enforcement of ``prefer`` constraints:
            - ``True``: Unmet preferences cause match failure
            - ``False``: Unmet preferences generate warnings only
            Note: ``must`` and ``forbid`` always hard-filter regardless of strict.

    Resolver Behavior:
        The resolver is responsible for matching dependencies to concrete providers.
        It operates in two phases:

        **Phase 1 - Filtering** (hard constraints):
            - Apply ``must`` requirements: provider must have all specified attributes
              with matching values. Providers missing any ``must`` attribute are excluded.
            - Apply ``forbid`` requirements: provider must NOT have the specified
              attribute values. Any match on ``forbid`` excludes the provider.

        **Phase 2 - Selection** (based on selection_policy):
            The remaining providers after filtering are selected according to policy.

    Selection Policy Semantics:
        **auto_if_unique** (default):
            Best for: Dependencies where only one provider is expected.

            1. After filtering, count remaining providers
            2. If exactly one provider remains, select it automatically
            3. If zero match: resolution fails (no provider available)
            4. If multiple match: resolution is ambiguous

            Ambiguity handling is resolver-specific. Common behaviors:
            - Return an "ambiguous" status requiring user resolution
            - Raise an error with the list of matching providers
            - Fall back to a secondary strategy (e.g., alphabetical first)

            .. todo::
                See ``docs/architecture/CAPABILITY_RESOLUTION.md`` for canonical
                resolver behavior semantics (planned documentation).

        **best_score**:
            Best for: Dependencies where multiple providers may match and
            preferences should guide selection.

            1. After filtering, score each remaining provider
            2. For each ``prefer`` constraint:
               - If provider has matching value: add points to score
               - Scoring weight is implementation-specific (typically +1 per match)
            3. Select the provider with highest score
            4. Ties are broken using ``hints`` (advisory):
               - Hints like ``{"vendor_preference": ["postgres", "mysql"]}``
                 provide ordered preferences for tie-breaking
               - If still tied, behavior is resolver-specific (e.g., first registered)

        **require_explicit**:
            Best for: Security-sensitive dependencies that should never be
            auto-resolved (e.g., secrets, credentials, production databases).

            1. Never auto-select, even if only one provider matches filtering
            2. Always require explicit provider binding via:
               - Configuration file (binding section)
               - Runtime API call
               - User prompt/selection
            3. Fail resolution until explicit binding is provided

    Examples:
        Database with transactions required:

        >>> dep = ModelCapabilityDependency(
        ...     alias="db",
        ...     capability="database.relational",
        ...     requirements=ModelRequirementSet(
        ...         must={"supports_transactions": True},
        ...     ),
        ... )
        >>> dep.alias
        'db'

        Cache with region preference:

        >>> cache_dep = ModelCapabilityDependency(
        ...     alias="cache",
        ...     capability="cache.distributed",
        ...     requirements=ModelRequirementSet(
        ...         prefer={"region": "us-east-1"},
        ...     ),
        ...     selection_policy="best_score",
        ...     strict=False,  # Allow fallback if region unavailable
        ... )

        Explicit binding required (security-sensitive):

        >>> secrets_dep = ModelCapabilityDependency(
        ...     alias="secrets",
        ...     capability="secrets.vault",
        ...     requirements=ModelRequirementSet(
        ...         must={"encryption": "aes-256"},
        ...     ),
        ...     selection_policy="require_explicit",
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    # Private cache for parsed capability parts - PrivateAttr allows mutation on frozen models.
    # Caching is safe because the model is frozen (immutable after creation) -
    # the capability field never changes, so the parsed parts are stable.
    # tuple[str, str, str | None] = (domain, capability_type, variant)
    _cached_capability_parts: tuple[str, str, str | None] | None = PrivateAttr(
        default=None
    )

    alias: str = Field(
        ...,
        description="Local name for binding (e.g., 'db', 'cache', 'vectors')",
        min_length=1,
        max_length=64,
    )

    capability: str = Field(
        ...,
        description="Capability identifier (e.g., 'database.relational', 'storage.vector')",
        min_length=3,
        max_length=128,
    )

    requirements: ModelRequirementSet = Field(
        default_factory=ModelRequirementSet,
        description="Constraint set for provider matching (must/prefer/forbid/hints)",
    )

    selection_policy: SelectionPolicy = Field(
        default="auto_if_unique",
        description="How to select among matching providers",
    )

    strict: bool = Field(
        default=True,
        description="Whether unmet prefer constraints cause failure (True) or warnings (False)",
    )

    @field_validator("alias")
    @classmethod
    def validate_alias(cls, v: str) -> str:
        """
        Validate that alias follows naming rules.

        The alias must:
            - Start with a lowercase letter
            - Contain only lowercase letters, digits, or underscores
            - Be 1-64 characters

        Args:
            v: The alias string to validate.

        Returns:
            The validated alias string.

        Raises:
            ModelOnexError: If the alias format is invalid.

        Examples:
            Valid: "db", "my_cache", "vector_store_1"
            Invalid: "DB", "1cache", "my-cache", "cache.main"
        """
        if not _ALIAS_PATTERN.match(v):
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=(
                    f"Invalid alias '{v}': must start with a lowercase letter "
                    "and contain only lowercase letters, digits, or underscores"
                ),
            )
        return v

    @field_validator("capability")
    @classmethod
    def validate_capability(cls, v: str) -> str:
        """
        Validate that capability follows naming convention.

        The capability must follow the pattern: ``<domain>.<type>[.<variant>]``
            - All lowercase letters, digits, and underscores
            - Dot-separated tokens (at least one dot required)
            - No consecutive dots, leading/trailing dots
            - No hyphens (use underscores for multi-word tokens)

        .. important:: Dot Requirement

            At least one dot is **REQUIRED** in capability names. Single-token
            names like "logging" or "database" are invalid. Always use the
            two-part format: "core.logging", "database.relational", etc.

            This ensures capabilities are namespaced by domain, preventing
            naming collisions and enabling hierarchical capability matching.

        Args:
            v: The capability string to validate.

        Returns:
            The validated capability string.

        Raises:
            ModelOnexError: If the capability format is invalid.

        Examples:
            Valid capabilities (note: all have at least one dot):

            - "database.relational" - domain=database, type=relational
            - "storage.vector.qdrant" - domain=storage, type=vector, variant=qdrant
            - "cache.key_value" - domain=cache, type=key_value (underscore OK)
            - "core.logging" - domain=core, type=logging

            Invalid capabilities:

            - "Database.Relational" - uppercase not allowed
            - "database" - **missing dot** (single token not allowed)
            - "logging" - **missing dot** (must be "core.logging" or similar)
            - "event-bus.handler" - hyphens not allowed (use "event_bus.handler")
        """
        if not _CAPABILITY_PATTERN.match(v):
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=(
                    f"Invalid capability '{v}': must follow pattern '<domain>.<type>[.<variant>]' "
                    "with lowercase letters/digits/underscores and at least one dot separator "
                    "(use underscores, not hyphens, for multi-word tokens)"
                ),
            )
        return v

    def _get_capability_parts(self) -> tuple[str, str, str | None]:
        """Get or create the cached parsed capability parts.

        This internal method manages the cache for capability parsing. Caching is
        safe because the model is frozen (immutable) - the capability field never
        changes after construction, so the parsed parts are stable.

        Returns:
            tuple[str, str, str | None]: (domain, capability_type, variant)
        """
        if self._cached_capability_parts is None:
            # Safe: field_validator guarantees capability matches _CAPABILITY_PATTERN,
            # which requires at least two tokens (pattern: ^[a-z0-9]+(\.[a-z0-9]+)+$)
            parts = self.capability.split(".")
            domain = parts[0]
            capability_type = parts[1]
            variant = ".".join(parts[2:]) if len(parts) > 2 else None
            self._cached_capability_parts = (domain, capability_type, variant)
        return self._cached_capability_parts

    @property
    def domain(self) -> str:
        """
        Extract the domain (first token) from the capability.

        Returns:
            The domain portion of the capability.

        Note:
            This property safely accesses index [0] without bounds checking because
            the ``capability`` field is validated by ``validate_capability()`` which
            guarantees the string matches ``_CAPABILITY_PATTERN`` - requiring at least
            two dot-separated tokens. The validation invariant ensures the split
            always produces at least 2 elements.

        Performance Note:
            The capability string is parsed once and cached. Subsequent accesses
            to domain, capability_type, and variant reuse the cached parts.

        Examples:
            >>> dep = ModelCapabilityDependency(alias="db", capability="database.relational")
            >>> dep.domain
            'database'
        """
        # Safe: Pydantic validation guarantees capability has at least one dot,
        # so split() always returns at least 2 elements.
        return self._get_capability_parts()[0]

    @property
    def capability_type(self) -> str:
        """
        Extract the type (second token) from the capability.

        Returns:
            The type portion of the capability.

        Note:
            This property safely accesses index [1] without bounds checking because
            the ``capability`` field is validated by ``validate_capability()`` which
            guarantees the string matches ``_CAPABILITY_PATTERN`` - requiring at least
            two dot-separated tokens. The validation invariant ensures the split
            always produces at least 2 elements.

        Performance Note:
            The capability string is parsed once and cached. Subsequent accesses
            to domain, capability_type, and variant reuse the cached parts.

        Examples:
            >>> dep = ModelCapabilityDependency(alias="db", capability="database.relational")
            >>> dep.capability_type
            'relational'
        """
        # Safe: Pydantic validation guarantees capability has at least one dot,
        # so split() always returns at least 2 elements.
        return self._get_capability_parts()[1]

    @property
    def variant(self) -> str | None:
        """
        Extract the variant (third+ tokens) from the capability if present.

        Returns:
            The variant portion if present, None otherwise. Two-part capabilities
            like "database.relational" have no variant (returns None). Three-part
            or longer capabilities like "cache.kv.redis" have a variant ("redis").

        Note:
            This property safely accesses index [2] because ``_get_capability_parts()``
            always returns a 3-tuple ``(domain, type, variant)`` where variant is
            None for two-part capabilities. The tuple structure is guaranteed by the
            parsing logic which is safe due to the ``validate_capability()`` invariant.

        Performance Note:
            The capability string is parsed once and cached. Subsequent accesses
            to domain, capability_type, and variant reuse the cached parts.

        Examples:
            >>> dep1 = ModelCapabilityDependency(alias="db", capability="database.relational")
            >>> dep1.variant is None
            True
            >>> dep2 = ModelCapabilityDependency(alias="c", capability="cache.kv.redis")
            >>> dep2.variant
            'redis'
        """
        # Safe: _get_capability_parts() always returns a 3-tuple; variant is None
        # for two-part capabilities, or the joined remaining tokens for 3+ parts.
        return self._get_capability_parts()[2]

    @property
    def has_requirements(self) -> bool:
        """
        Check if this dependency has any requirements.

        Returns:
            True if requirements are non-empty, False otherwise.
        """
        return not self.requirements.is_empty

    @property
    def requires_explicit_binding(self) -> bool:
        """
        Check if this dependency requires explicit provider binding.

        Returns:
            True if selection_policy is "require_explicit", False otherwise.
        """
        return self.selection_policy == "require_explicit"

    def __repr__(self) -> str:
        """
        Return detailed representation for debugging.

        Returns:
            String representation with key attributes.
        """
        parts = [
            f"alias={self.alias!r}",
            f"capability={self.capability!r}",
        ]
        if self.has_requirements:
            parts.append(f"requirements={self.requirements!r}")
        if self.selection_policy != "auto_if_unique":
            parts.append(f"selection_policy={self.selection_policy!r}")
        if not self.strict:
            parts.append("strict=False")
        return f"ModelCapabilityDependency({', '.join(parts)})"

    def __str__(self) -> str:
        """
        Return concise string representation.

        Returns:
            String in format 'alias -> capability'.
        """
        return f"{self.alias} -> {self.capability}"


__all__ = ["ModelCapabilityDependency", "SelectionPolicy"]
