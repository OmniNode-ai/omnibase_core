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

    - Tokens contain lowercase letters, digits, underscores, and hyphens
    - Dots are semantic separators between tokens
    - Hyphens and underscores are allowed within tokens for multi-word names

    Examples:
        - ``database.relational`` - Any relational database
        - ``database.document`` - Document/NoSQL database
        - ``storage.vector`` - Vector storage capability
        - ``storage.vector.qdrant`` - Qdrant-compatible vector store
        - ``messaging.event_bus`` - Event bus capability
        - ``llm.text-embedding.v1`` - Text embedding capability (hyphen OK)
        - ``cache.key-value`` - Key-value cache capability (hyphen OK)
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
from omnibase_core.models.capabilities.model_capability_requirement_set import (
    ModelRequirementSet,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError

# Regex pattern for valid capability names
# Must be lowercase letters, digits, underscores, and hyphens, with dot-separated tokens
# At least two tokens (one dot required): domain.type[.variant]
# Note: Single-character tokens are intentionally allowed (e.g., "a.b") to support
# short, idiomatic names common in capability systems. The min_length=3 field
# constraint ensures the overall capability has reasonable length ("a.b" is valid).
#
# Both hyphens and underscores are allowed within tokens for multi-word names
# (e.g., "text-embedding", "event_bus", "key-value"). Dots remain the semantic
# separators between domain/type/variant levels.
_CAPABILITY_PATTERN = re.compile(r"^[a-z0-9_-]+(\.[a-z0-9_-]+)+$")

# Regex pattern for valid alias names
# More permissive: lowercase letters, digits, underscores
# Single token (no dots), must start with letter
# Note: Single-character aliases are intentionally allowed (e.g., "a", "x") to support
# terse binding names in handler code. Common short aliases include "db", "c" (cache).
_ALIAS_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")

# Semver validation patterns
# Matches versions like 1.0.0, 1.0.0-alpha, 1.0.0+build
_SEMVER_VERSION = r"(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)(?:-[\da-zA-Z-]+(?:\.[\da-zA-Z-]+)*)?(?:\+[\da-zA-Z-]+(?:\.[\da-zA-Z-]+)*)?"
# Matches operators: >=, <=, >, <, =
_SEMVER_OPERATOR = r"(?:>=|<=|>|<|=)"
# Single constraint: operator + version (e.g., ">=1.0.0")
_SEMVER_CONSTRAINT = rf"(?:{_SEMVER_OPERATOR})?{_SEMVER_VERSION}"
# Caret syntax: ^1.2.3
_SEMVER_CARET = rf"\^{_SEMVER_VERSION}"
# Tilde syntax: ~1.2.3
_SEMVER_TILDE = rf"~{_SEMVER_VERSION}"
# Full pattern: space-separated constraints, caret, or tilde
_SEMVER_RANGE_PATTERN = re.compile(
    rf"^(?:{_SEMVER_CONSTRAINT}(?:\s+{_SEMVER_CONSTRAINT})*|{_SEMVER_CARET}|{_SEMVER_TILDE})$"
)

# Type alias for selection policies
type SelectionPolicy = Literal["auto_if_unique", "best_score", "require_explicit"]


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
            digits, underscores, and hyphens. Examples: "database.relational",
            "storage.vector", "cache.key-value", "llm.text-embedding.v1".
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
        version_range: Optional semver version constraint for the capability.
            When specified, only providers whose capability version satisfies
            the range will be considered. Supports:
            - Simple versions: "1.0.0"
            - Operators: ">=1.0.0", "<=2.0.0", ">1.0.0", "<2.0.0", "=1.0.0"
            - Ranges: ">=1.0.0 <2.0.0" (space-separated constraints)
            - Caret: "^1.2.3" (compatible with major version)
            - Tilde: "~1.2.3" (approximately equivalent to minor version)
            - Pre-release: "1.0.0-alpha", "1.0.0-beta.1"
            - Build metadata: "1.0.0+build.123"

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

            .. seealso::
                ``docs/architecture/CAPABILITY_RESOLUTION.md`` for canonical
                resolver behavior semantics and ambiguity handling strategies.

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

    # string-version-ok: This is a semver RANGE expression (e.g., ">=1.0.0 <2.0.0"), not a single version
    version_range: str | None = Field(
        default=None,
        description="Optional semver range for capability version (e.g., '>=1.0.0 <2.0.0', '^1.2.3', '~1.2.3')",
        max_length=128,
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

        Note:
            Length validation (min_length=1, max_length=64) is enforced by Pydantic's
            field constraints BEFORE this validator runs. This validator only validates
            the FORMAT (regex pattern), not the length. Empty strings are already
            rejected by the min_length=1 constraint, so no explicit empty check needed.

        Examples:
            Valid: "db", "my_cache", "vector_store_1"
            Invalid: "DB", "1cache", "my-cache", "cache.main"
        """
        # Validation invariant: Pydantic's min_length=1 rejects empty strings before
        # this validator runs. We only validate the format pattern here.
        if not _ALIAS_PATTERN.match(v):
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=(
                    f"Invalid alias '{v}': must start with a lowercase letter "
                    "and contain only lowercase letters, digits, or underscores"
                ),
                field="alias",
                invalid_value=v,
                pattern=_ALIAS_PATTERN.pattern,
            )
        return v

    @field_validator("capability")
    @classmethod
    def validate_capability(cls, v: str) -> str:
        """
        Validate that capability follows naming convention.

        The capability must follow the pattern: ``<domain>.<type>[.<variant>]``
            - All lowercase letters, digits, underscores, and hyphens
            - Dot-separated tokens (at least one dot required)
            - No consecutive dots, leading/trailing dots

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

        Note:
            Length validation (min_length=3, max_length=128) is enforced by Pydantic's
            field constraints BEFORE this validator runs. This validator only validates
            the FORMAT (regex pattern), not the length. Strings shorter than 3 characters
            are already rejected by the min_length=3 constraint, so no explicit length
            check needed.

        Examples:
            Valid capabilities (note: all have at least one dot):

            - "database.relational" - domain=database, type=relational
            - "storage.vector.qdrant" - domain=storage, type=vector, variant=qdrant
            - "cache.key_value" - domain=cache, type=key_value (underscore OK)
            - "llm.text-embedding.v1" - domain=llm, type=text-embedding (hyphen OK)
            - "cache.key-value" - domain=cache, type=key-value (hyphen OK)
            - "core.logging" - domain=core, type=logging

            Invalid capabilities:

            - "Database.Relational" - uppercase not allowed
            - "database" - **missing dot** (single token not allowed)
            - "logging" - **missing dot** (must be "core.logging" or similar)
        """
        # Validation invariant: Pydantic's min_length=3 rejects short strings before
        # this validator runs. We only validate the format pattern here.
        if not _CAPABILITY_PATTERN.match(v):
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=(
                    f"Invalid capability '{v}': must follow pattern '<domain>.<type>[.<variant>]' "
                    "with lowercase letters/digits/underscores/hyphens and at least one dot separator"
                ),
                field="capability",
                invalid_value=v,
                pattern=_CAPABILITY_PATTERN.pattern,
            )
        return v

    @field_validator("version_range")
    @classmethod
    def validate_version_range(cls, v: str | None) -> str | None:
        """
        Validate that version_range follows semver range syntax.

        Supports:
            - Simple versions: "1.0.0"
            - Operators: ">=1.0.0", "<=2.0.0", ">1.0.0", "<2.0.0", "=1.0.0"
            - Ranges: ">=1.0.0 <2.0.0" (space-separated)
            - Caret: "^1.2.3" (compatible with)
            - Tilde: "~1.2.3" (approximately equivalent)
            - Pre-release: "1.0.0-alpha", "1.0.0-beta.1"
            - Build metadata: "1.0.0+build.123"

        Args:
            v: The version range string to validate, or None.

        Returns:
            The validated version range string (stripped), or None.

        Raises:
            ModelOnexError: If the version range format is invalid.
        """
        if v is None:
            return None

        v = v.strip()
        if not v:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="version_range cannot be empty string; use None for no constraint",
                field="version_range",
                invalid_value=v,
            )

        if not _SEMVER_RANGE_PATTERN.match(v):
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=(
                    f"Invalid version_range '{v}': must be valid semver range "
                    "(e.g., '>=1.0.0 <2.0.0', '^1.2.3', '~1.2.3')"
                ),
                field="version_range",
                invalid_value=v,
                pattern=_SEMVER_RANGE_PATTERN.pattern,
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
            # which requires at least two tokens (pattern: ^[a-z0-9_-]+(\.[a-z0-9_-]+)+$)
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
        if self.version_range is not None:
            parts.append(f"version_range={self.version_range!r}")
        return f"ModelCapabilityDependency({', '.join(parts)})"

    def __str__(self) -> str:
        """
        Return concise string representation.

        Returns:
            String in format 'alias -> capability'.
        """
        return f"{self.alias} -> {self.capability}"

    def __hash__(self) -> int:
        """
        Enable use in sets and as dict keys for dependency deduplication.

        Hash is computed from immutable identity fields (capability, alias).
        The requirements (must/prefer/forbid/hints), selection_policy, and
        strict flag are NOT included since two dependencies with the same
        identity but different configuration should hash to the same value
        for deduplication purposes.

        Note:
            While Pydantic frozen models with dict fields are not automatically
            hashable (dicts are unhashable), this custom __hash__ uses only
            immutable string fields, making the hash stable and safe.

            The hash contract is maintained: equal objects have equal hashes.
            Hash collisions between objects with same identity but different
            requirements are intentional and acceptable.

        Examples:
            Using dependencies in sets for deduplication:

            >>> dep1 = ModelCapabilityDependency(alias="db", capability="database.relational")
            >>> dep2 = ModelCapabilityDependency(alias="db", capability="database.relational")
            >>> dep3 = ModelCapabilityDependency(alias="cache", capability="cache.kv")
            >>> deps = {dep1, dep2, dep3}
            >>> len(deps)  # dep1 and dep2 deduplicate
            2

            Using dependencies as dict keys for caching:

            >>> dep = ModelCapabilityDependency(alias="db", capability="database.relational")
            >>> cache = {dep: "resolved_provider"}
            >>> cache[dep]
            'resolved_provider'

        Returns:
            Hash value computed from (capability, alias) tuple.
        """
        return hash((self.capability, self.alias))


__all__ = ["ModelCapabilityDependency", "SelectionPolicy"]
