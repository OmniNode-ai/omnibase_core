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

    Examples:
        - ``database.relational`` - Any relational database
        - ``database.document`` - Document/NoSQL database
        - ``storage.vector`` - Vector storage capability
        - ``storage.vector.qdrant`` - Qdrant-compatible vector store
        - ``messaging.eventbus`` - Event bus capability
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

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.capabilities.model_requirement_set import ModelRequirementSet
from omnibase_core.models.errors.model_onex_error import ModelOnexError

# Regex pattern for valid capability names
# Must be lowercase letters and digits, dot-separated tokens
# At least two tokens (one dot required): domain.type[.variant]
_CAPABILITY_PATTERN = re.compile(r"^[a-z0-9]+(\.[a-z0-9]+)+$")

# Regex pattern for valid alias names
# More permissive: lowercase letters, digits, underscores
# Single token (no dots), must start with letter
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
            ``<domain>.<type>[.<variant>]``. Examples: "database.relational",
            "storage.vector", "cache.distributed".
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

    Selection Policy Semantics:
        **auto_if_unique**:
            1. Filter providers by must/forbid requirements
            2. If exactly one provider matches, select it automatically
            3. If multiple match, resolution is unresolved (error or escalate)

        **best_score**:
            1. Filter providers by must/forbid requirements
            2. Score remaining providers using prefer requirements
            3. Select highest-scoring provider
            4. Ties broken using hints (advisory only)

        **require_explicit**:
            1. Never auto-select, even if only one provider matches
            2. Always require explicit provider binding via config/user

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
        # Note: Empty check handled by min_length=1 constraint on field
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
            - All lowercase letters and digits
            - Dot-separated tokens (at least one dot required)
            - No consecutive dots, leading/trailing dots

        Args:
            v: The capability string to validate.

        Returns:
            The validated capability string.

        Raises:
            ModelOnexError: If the capability format is invalid.

        Examples:
            Valid: "database.relational", "storage.vector.qdrant", "cache.kv.redis"
            Invalid: "Database.Relational", "database", "database..relational"
        """
        # Note: Empty check handled by min_length=3 constraint on field
        if not _CAPABILITY_PATTERN.match(v):
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=(
                    f"Invalid capability '{v}': must follow pattern '<domain>.<type>[.<variant>]' "
                    "with lowercase letters/digits and at least one dot separator"
                ),
            )
        return v

    @property
    def domain(self) -> str:
        """
        Extract the domain (first token) from the capability.

        Returns:
            The domain portion of the capability.

        Examples:
            >>> dep = ModelCapabilityDependency(alias="db", capability="database.relational")
            >>> dep.domain
            'database'
        """
        return self.capability.split(".")[0]

    @property
    def capability_type(self) -> str:
        """
        Extract the type (second token) from the capability.

        Returns:
            The type portion of the capability.

        Examples:
            >>> dep = ModelCapabilityDependency(alias="db", capability="database.relational")
            >>> dep.capability_type
            'relational'
        """
        return self.capability.split(".")[1]

    @property
    def variant(self) -> str | None:
        """
        Extract the variant (third+ tokens) from the capability if present.

        Returns:
            The variant portion if present, None otherwise.

        Examples:
            >>> dep1 = ModelCapabilityDependency(alias="db", capability="database.relational")
            >>> dep1.variant is None
            True
            >>> dep2 = ModelCapabilityDependency(alias="c", capability="cache.kv.redis")
            >>> dep2.variant
            'redis'
        """
        parts = self.capability.split(".")
        if len(parts) > 2:
            return ".".join(parts[2:])
        return None

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
