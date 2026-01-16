from __future__ import annotations

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
    observed_features completely replaces declared_features when non-empty
    (the two are NOT merged). Observed features represent runtime-probed
    reality, while declared features are static claims that may become stale.

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

import fnmatch
import re
from typing import TYPE_CHECKING, Annotated, Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, SkipValidation, field_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.types.type_json import JsonType

# ---------------------------------------------------------------------------
# TYPE SAFETY PATTERN FOR CIRCULAR IMPORT AVOIDANCE
# ---------------------------------------------------------------------------
# This module uses TYPE_CHECKING with SkipValidation for the `health` field
# to avoid a complex circular import chain:
#
#   model_health_status.py -> model_health_metadata.py -> model_health_attributes.py
#   -> model_custom_fields.py -> ... -> mixin_health_check.py -> model_health_status.py
#
# PATTERN EXPLANATION:
# 1. `from __future__ import annotations` defers annotation evaluation
# 2. TYPE_CHECKING import provides IDE/type checker support for ModelHealthStatus
# 3. SkipValidation allows Pydantic to skip validation at model instantiation
# 4. Static type checkers see the proper type: ModelHealthStatus | None
# 5. Runtime uses SkipValidation[Any] to accept any value
#
# TO GET FULL RUNTIME TYPE VALIDATION: After all modules are loaded, call
# `ModelProviderDescriptor.model_rebuild()` to resolve the forward reference
# and enable full Pydantic validation of the health field.
#
# WHY SkipValidation?
# The circular import prevents importing ModelHealthStatus at module load time.
# SkipValidation allows the model to be instantiated immediately while still
# providing proper type hints for static analysis. Call model_rebuild() after
# all modules are loaded (e.g., in application startup or test fixtures).
# ---------------------------------------------------------------------------
if TYPE_CHECKING:
    from omnibase_core.models.health.model_health_status import ModelHealthStatus

    # Type alias for static type checkers - shows proper type
    HealthStatusType = Annotated[ModelHealthStatus | None, SkipValidation]
else:
    # Runtime type alias - accepts any value, validation skipped until model_rebuild()
    HealthStatusType = Annotated[Any, SkipValidation]


# Capability naming pattern: lowercase alphanumeric with dots, at least one dot
# Examples: "database.relational", "cache.redis", "storage.s3"
_CAPABILITY_PATTERN = re.compile(r"^[a-z0-9]+(\.[a-z0-9]+)+$")

# Python identifier pattern: starts with letter or underscore, followed by
# alphanumeric or underscores. Used for validating adapter import paths.
# Examples: "MyClass", "_private", "module_name", "Class123"
_PYTHON_IDENTIFIER_PATTERN = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")

# Connection reference scheme pattern: lowercase alphanumeric, must start with letter
# Examples: "secrets", "env", "vault", "file", "http", "https", "s3"
_SCHEME_PATTERN = re.compile(r"^[a-z][a-z0-9]*$")


class ModelProviderDescriptor(BaseModel):
    """Describes a concrete provider instance registered in the registry.

    Providers are instances that offer specific capabilities. Resolution
    matches capability requirements to available providers.

    Core Principle:
        "Providers are instances registered in the registry.
        Resolution matches capabilities to providers."

    Feature Resolution Precedence:
        observed_features completely replaces declared_features when non-empty
        (the two are NOT merged). Observed features represent runtime-probed
        reality, while declared features are static claims that may become stale.

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
        **Why from_attributes=True is Required**

        This model uses ``from_attributes=True`` in its ConfigDict to ensure
        pytest-xdist compatibility. The technical reason involves Python's class
        identity behavior in parallel test execution:

        1. **Parallel Worker Isolation**: When running tests with pytest-xdist
           (e.g., ``pytest -n4``), each worker process runs in its own Python
           interpreter with its own module imports.

        2. **Class Identity Mismatch**: Each worker imports
           ``ModelProviderDescriptor`` independently, creating separate class
           objects. While these classes are functionally identical, Python's
           ``isinstance()`` check and Pydantic's default validation fail
           because ``WorkerA.ModelProviderDescriptor is not WorkerB.ModelProviderDescriptor``.

        3. **from_attributes=True Solution**: This flag enables Pydantic's
           "duck typing" mode for model construction. Instead of requiring exact
           class identity, Pydantic checks if the source object has matching
           attribute names and constructs a new instance from those values.
           This allows fixtures created in one worker to be validated in another.

        **Example of the Problem (without from_attributes=True)**::

            # Worker A creates: descriptor = ModelProviderDescriptor(...)
            # Worker B receives descriptor via pytest fixture
            # Worker B's Pydantic rejects it: "expected ModelProviderDescriptor,
            # got <models.providers.model_provider_descriptor.ModelProviderDescriptor>"

        See CLAUDE.md "Pydantic from_attributes=True for Value Objects" section
        for the project convention and additional models using this pattern.

        **Thread Safety**: This model is frozen (immutable) after creation,
        making it thread-safe for concurrent read access from multiple threads
        or async tasks. Use ``model_copy()`` to create modified copies when
        needed.
    """

    # from_attributes=True enables pytest-xdist compatibility (class identity across workers)
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

    attributes: dict[str, JsonType] = Field(
        default_factory=dict,
        description="Static attributes (version, region, deployment tier, etc.)",
    )

    declared_features: dict[str, JsonType] = Field(
        default_factory=dict,
        description=(
            "Features the adapter claims to support (static declaration). "
            "Completely replaced by observed_features when non-empty (NOT merged)."
        ),
    )

    observed_features: dict[str, JsonType] = Field(
        default_factory=dict,
        description=(
            "Runtime-probed capabilities. When non-empty, completely replaces "
            "declared_features (the two are NOT merged)."
        ),
    )

    tags: list[str] = Field(
        default_factory=list,
        description="Tags for filtering (e.g., 'production', 'us-east', 'primary')",
    )

    # See TYPE SAFETY PATTERN documentation block at module level for details.
    # Uses SkipValidation to allow instantiation without model_rebuild().
    # Static type checkers see: ModelHealthStatus | None
    # Runtime accepts any value until model_rebuild() is called.
    health: HealthStatusType = Field(
        default=None,
        description=(
            "Current health status of this provider. Uses forward reference with "
            "SkipValidation to avoid circular import. Call model_rebuild() after "
            "all modules are loaded for full Pydantic validation."
        ),
    )

    @field_validator("health", mode="before")
    @classmethod
    def validate_health(cls, v: Any) -> Any:
        """Validate health field accepts ModelHealthStatus or None.

        Uses lazy import to avoid circular import issues with the health module.

        Args:
            v: Value to validate (should be ModelHealthStatus, None, or dict).

        Returns:
            The validated value.

        Raises:
            ModelOnexError: If value is not None, ModelHealthStatus, or a dict
                that can be converted to ModelHealthStatus.
        """
        if v is None:
            return None

        # Lazy import to avoid circular dependency
        from omnibase_core.models.health.model_health_status import ModelHealthStatus

        # Duck-type check for ModelHealthStatus (handles pytest-xdist class identity issues)
        # Check class name and verify module is from expected package (health module or test stubs)
        if type(v).__name__ == "ModelHealthStatus":
            module = getattr(type(v), "__module__", "")
            # Accept if from health module or test modules (stubs)
            if "model_health_status" in module or "test" in module or not module:
                return v

        if isinstance(v, dict):
            # Allow dict-based construction for Pydantic compatibility
            try:
                return ModelHealthStatus(**v)
            except Exception as e:
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=f"Failed to construct health status from dict: {e}",
                    context={"health_dict": v, "error": str(e)},
                ) from e

        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=(
                f"health must be ModelHealthStatus, dict, or None, "
                f"got {type(v).__name__}"
            ),
            context={"health_type": type(v).__name__},
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
                context={"capabilities": v},
            )

        validated: set[str] = set()
        for cap in v:
            if not isinstance(cap, str):
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=f"Capability must be a string, got {type(cap).__name__}",
                    context={
                        "capability": cap,
                        "capability_type": type(cap).__name__,
                        "all_capabilities": v,
                    },
                )

            stripped = cap.strip()
            if not stripped:
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message="Capability cannot be empty or whitespace-only",
                    context={"capability": cap, "all_capabilities": v},
                )

            if not _CAPABILITY_PATTERN.match(stripped):
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=(
                        f"Invalid capability '{stripped}': must be lowercase "
                        "alphanumeric with dots, containing at least one dot "
                        "(e.g., 'database.relational', 'cache.redis')"
                    ),
                    context={"capability": stripped, "all_capabilities": v},
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
                    context={
                        "tag": tag,
                        "tag_type": type(tag).__name__,
                        "all_tags": v,
                    },
                )

            stripped = tag.strip()
            if not stripped:
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message="Tag cannot be empty or whitespace-only",
                    context={"tag": tag, "all_tags": v},
                )

            validated.add(stripped)

        return sorted(validated)

    @field_validator("connection_ref")
    @classmethod
    def validate_connection_ref(cls, v: str) -> str:
        """Validate connection reference format.

        Connection references must follow the pattern: scheme://path

        The scheme must be lowercase alphanumeric (starting with a letter),
        and the path must be non-empty.

        Common Supported Schemes:
            - secrets:// - Secret management (e.g., secrets://postgres/primary)
            - env:// - Environment variables (e.g., env://DATABASE_URL)
            - vault:// - HashiCorp Vault (e.g., vault://secret/data/db)
            - file:// - File system paths (e.g., file:///etc/config.yaml)
            - http:// / https:// - HTTP endpoints
            - s3:// - S3 bucket references

        Custom schemes are also accepted as long as they follow the
        lowercase alphanumeric pattern (starting with a letter).

        Args:
            v: Connection reference string to validate.

        Returns:
            The validated connection reference (unchanged if valid).

        Raises:
            ModelOnexError: If the connection reference format is invalid.
                This includes: missing "://" separator, empty scheme,
                scheme not matching the lowercase alphanumeric pattern,
                or empty path. Error code is VALIDATION_ERROR.

        Examples:
            Valid: "secrets://postgres/primary", "env://DB_URL", "s3://bucket/key"
            Invalid: "://no-scheme", "SECRETS://path", "secrets://"
        """
        if "://" not in v:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=(
                    f"Invalid connection_ref '{v}': must contain scheme separator "
                    "'://' (e.g., 'secrets://postgres/primary', 'env://DB_URL')"
                ),
                context={"connection_ref": v},
            )

        # Split on first occurrence of "://" to get scheme and path
        scheme, path = v.split("://", 1)

        # Validate scheme is non-empty and matches pattern
        if not scheme:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=(
                    f"Invalid connection_ref '{v}': scheme cannot be empty. "
                    "Must start with a valid scheme "
                    "(e.g., 'secrets://path', 'env://VAR')"
                ),
                context={"connection_ref": v, "scheme": scheme, "path": path},
            )

        if not _SCHEME_PATTERN.match(scheme):
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=(
                    f"Invalid connection_ref '{v}': scheme '{scheme}' must be "
                    "lowercase alphanumeric, starting with a letter "
                    "(e.g., 'secrets', 'env', 'vault', 'file', 'http', 's3')"
                ),
                context={"connection_ref": v, "scheme": scheme, "path": path},
            )

        # Validate path is non-empty
        if not path:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=(
                    f"Invalid connection_ref '{v}': path cannot be empty. "
                    "Must have content after '://' "
                    "(e.g., 'secrets://postgres/primary', 'env://DB_URL')"
                ),
                context={"connection_ref": v, "scheme": scheme, "path": path},
            )

        return v

    @field_validator("adapter")
    @classmethod
    def validate_adapter(cls, v: str) -> str:
        """Validate adapter is a valid Python import path.

        Adapter paths must look like valid Python module import paths,
        containing at least one dot and having each segment be a valid
        Python identifier (alphanumeric + underscore, not starting with number).

        Args:
            v: Adapter import path string to validate.

        Returns:
            The validated adapter path (unchanged if valid).

        Raises:
            ModelOnexError: If the adapter path does not contain at least one
                dot, or if any segment is not a valid Python identifier.
                Error code is VALIDATION_ERROR.

        Examples:
            Valid: "omnibase_infra.adapters.PostgresAdapter", "test.Adapter",
                   "my_module.sub.Class", "_private.Module"
            Invalid: "NoDotsHere", "123.invalid", "has spaces.invalid"
        """
        if "." not in v:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=(
                    f"Invalid adapter '{v}': must be a valid Python import path "
                    "containing at least one dot "
                    "(e.g., 'omnibase_infra.adapters.PostgresAdapter', 'test.Adapter')"
                ),
                context={"adapter": v},
            )

        parts = v.split(".")
        for part in parts:
            if not _PYTHON_IDENTIFIER_PATTERN.match(part):
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=(
                        f"Invalid adapter '{v}': segment '{part}' is not a valid "
                        "Python identifier. Each segment must start with a letter "
                        "or underscore and contain only alphanumeric characters "
                        "or underscores."
                    ),
                    context={"adapter": v, "invalid_segment": part},
                )

        return v

    def get_effective_features(self) -> dict[str, JsonType]:
        """Get effective features with observed completely replacing declared.

        Returns observed_features if non-empty, otherwise returns declared_features.
        This implements full replacement semantics: the two dictionaries are NOT
        merged. When observed_features has any entries, declared_features is
        completely ignored. This prevents stale declared features from polluting
        fresh observed data.

        Returns:
            Dictionary of effective features. Returns observed_features if it
            contains any entries (completely replacing declared_features),
            otherwise returns declared_features.

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

    def has_capability(self, capability: str) -> bool:
        """Check if provider has a specific capability.

        Performs an exact match against the provider's capability list.

        Args:
            capability: Exact capability identifier to check.

        Returns:
            True if the provider has this exact capability, False otherwise.

        Examples:
            >>> from uuid import uuid4
            >>> desc = ModelProviderDescriptor(
            ...     provider_id=uuid4(),
            ...     capabilities=["database.relational", "database.postgresql"],
            ...     adapter="test.Adapter",
            ...     connection_ref="env://TEST",
            ... )
            >>> desc.has_capability("database.relational")
            True
            >>> desc.has_capability("cache.redis")
            False
        """
        return capability in self.capabilities

    def matches_any_capability(self, patterns: list[str]) -> bool:
        """Check if provider matches any capability pattern.

        Supports glob-style patterns with '*' wildcard for flexible matching.
        This is useful for capability requirement resolution where consumers
        may specify patterns like "database.*" to match any database provider.

        Args:
            patterns: List of capability patterns to match against.
                Supports glob wildcards (e.g., "database.*" matches
                "database.relational", "database.postgresql").

        Returns:
            True if any pattern matches any capability, False otherwise.
            Returns False if patterns list is empty.

        Examples:
            >>> from uuid import uuid4
            >>> desc = ModelProviderDescriptor(
            ...     provider_id=uuid4(),
            ...     capabilities=["database.relational", "database.postgresql"],
            ...     adapter="test.Adapter",
            ...     connection_ref="env://TEST",
            ... )
            >>> desc.matches_any_capability(["database.*"])
            True
            >>> desc.matches_any_capability(["cache.*"])
            False
            >>> desc.matches_any_capability(["database.relational"])
            True
            >>> desc.matches_any_capability([])
            False
        """
        return any(
            fnmatch.fnmatch(cap, pattern)
            for pattern in patterns
            for cap in self.capabilities
        )

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


__all__ = ["HealthStatusType", "ModelProviderDescriptor"]
