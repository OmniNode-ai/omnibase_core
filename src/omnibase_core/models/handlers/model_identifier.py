"""
Structured Identifier Model.

Generic structured identifier model following the `namespace:name` pattern
used throughout the ONEX framework for handler types, capabilities, and
command types.

Example Usage:
    >>> from omnibase_core.models.handlers.model_identifier import ModelIdentifier
    >>> # Create from structured fields
    >>> id1 = ModelIdentifier(namespace="onex", name="compute")
    >>> assert str(id1) == "onex:compute"
    >>>
    >>> # Parse from canonical string form
    >>> id2 = ModelIdentifier.parse("vendor:custom@v2")
    >>> assert id2.namespace == "vendor"
    >>> assert id2.name == "custom"
    >>> assert id2.variant == "v2"
    >>>
    >>> # Use as dict keys (hashable and equatable)
    >>> cache = {id1: "cached_value"}
    >>> assert id1 in cache
"""

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer

# Regex pattern for valid namespace and name components
# Must start with a letter, followed by letters, numbers, underscores, or hyphens
_IDENTIFIER_COMPONENT_PATTERN = re.compile(r"^[a-zA-Z][a-zA-Z0-9_-]*$")

# Regex pattern for parsing canonical string format: namespace:name[@variant]
# Captures: namespace, name, and optional variant
_CANONICAL_PATTERN = re.compile(
    r"^(?P<namespace>[a-zA-Z][a-zA-Z0-9_-]*):(?P<name>[a-zA-Z][a-zA-Z0-9_-]*)(?:@(?P<variant>[a-zA-Z0-9][a-zA-Z0-9_-]*))?$"
)

# Regex pattern for valid variant components
# More permissive than namespace/name: can start with letter OR number (e.g., "v2", "2024")
# Precompiled for performance since variant validation runs on every identifier creation
_VARIANT_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$")


class ModelIdentifier(BaseModel):
    """
    Generic structured identifier model for ONEX components.

    Follows the `namespace:name` pattern used for handler types, capabilities,
    command types, and other extensible identifiers throughout the framework.

    The canonical string format is:
        - Basic: `namespace:name` (e.g., "onex:compute", "vendor:custom")
        - With variant: `namespace:name@variant` (e.g., "onex:handler@v2")

    Attributes:
        namespace: Namespace for isolation (e.g., "onex", "vendor", "custom").
            Must start with a letter, followed by letters, numbers, underscores,
            or hyphens.
        name: Identifier name within the namespace.
            Must follow the same character rules as namespace.
        variant: Optional variant qualifier for versioning or specialization.
            When present, appended to canonical form with '@' separator.
        version: Optional semantic version for versioned identifiers.
            Not included in the canonical string form but useful for
            compatibility checks.

    Examples:
        Create an identifier directly:

        >>> id1 = ModelIdentifier(namespace="onex", name="compute")
        >>> str(id1)
        'onex:compute'

        Create with variant:

        >>> id2 = ModelIdentifier(namespace="vendor", name="handler", variant="async")
        >>> str(id2)
        'vendor:handler@async'

        Parse from canonical string:

        >>> id3 = ModelIdentifier.parse("onex:effect@streaming")
        >>> id3.namespace
        'onex'
        >>> id3.name
        'effect'
        >>> id3.variant
        'streaming'

        Use as dict keys:

        >>> cache = {}
        >>> key1 = ModelIdentifier(namespace="onex", name="compute")
        >>> key2 = ModelIdentifier(namespace="onex", name="compute")
        >>> cache[key1] = "value"
        >>> cache[key2]  # Same logical key
        'value'

    Note:
        This model is frozen (immutable) and can be safely used as dict keys
        or in sets due to its __hash__ and __eq__ implementations.
    """

    # from_attributes=True allows Pydantic to accept objects with matching
    # attributes even when class identity differs (e.g., in pytest-xdist
    # parallel execution where model classes are imported in separate workers)
    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    namespace: str = Field(
        ...,
        description="Namespace for isolation (e.g., 'onex', 'vendor')",
        min_length=1,
    )

    name: str = Field(
        ...,
        description="Identifier name within namespace",
        min_length=1,
    )

    variant: str | None = Field(
        default=None,
        description="Optional variant qualifier (e.g., 'v2', 'async')",
    )

    version: ModelSemVer | None = Field(
        default=None,
        description="Optional semantic version for versioned identifiers",
    )

    @field_validator("namespace")
    @classmethod
    def validate_namespace(cls, v: str) -> str:
        """
        Validate that namespace follows identifier naming rules.

        The namespace must:
            - Not be empty
            - Start with a letter (a-z, A-Z)
            - Contain only letters, numbers, underscores, or hyphens

        Args:
            v: The namespace string to validate.

        Returns:
            The validated namespace string (unchanged if valid).

        Raises:
            ModelOnexError: If the namespace is empty or contains invalid
                characters. Error code is VALIDATION_ERROR.

        Examples:
            Valid namespaces: "onex", "vendor", "my-namespace", "ns_v2"
            Invalid namespaces: "", "123start", "has spaces", "has.dots"
        """
        if not v:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="Namespace cannot be empty",
            )
        if not _IDENTIFIER_COMPONENT_PATTERN.match(v):
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=(
                    f"Invalid namespace '{v}': must start with a letter and "
                    "contain only letters, numbers, underscores, or hyphens"
                ),
            )
        return v

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """
        Validate that name follows identifier naming rules.

        The name must:
            - Not be empty
            - Start with a letter (a-z, A-Z)
            - Contain only letters, numbers, underscores, or hyphens

        Args:
            v: The name string to validate.

        Returns:
            The validated name string (unchanged if valid).

        Raises:
            ModelOnexError: If the name is empty or contains invalid
                characters. Error code is VALIDATION_ERROR.

        Examples:
            Valid names: "compute", "my-handler", "effect_v2", "Transformer"
            Invalid names: "", "123start", "has spaces", "has.dots"
        """
        if not v:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="Name cannot be empty",
            )
        if not _IDENTIFIER_COMPONENT_PATTERN.match(v):
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=(
                    f"Invalid name '{v}': must start with a letter and "
                    "contain only letters, numbers, underscores, or hyphens"
                ),
            )
        return v

    @field_validator("variant")
    @classmethod
    def validate_variant(cls, v: str | None) -> str | None:
        """
        Validate that variant follows identifier naming rules if present.

        Unlike namespace and name, variants have more permissive rules:
            - Can be None (no variant)
            - Cannot be empty string (use None instead)
            - Can start with a letter OR a number (e.g., "v2", "2024")
            - Can contain letters, numbers, underscores, or hyphens

        Args:
            v: The variant string to validate, or None.

        Returns:
            The validated variant string (unchanged if valid), or None.

        Raises:
            ModelOnexError: If the variant is an empty string or contains
                invalid characters. Error code is VALIDATION_ERROR.

        Examples:
            Valid variants: None, "v2", "async", "2024", "beta-1"
            Invalid variants: "", "has spaces", "has.dots"
        """
        if v is None:
            return None
        if not v:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="Variant cannot be empty string (use None instead)",
            )
        # Variant can start with a number (e.g., "v2", "2024")
        # Uses precompiled _VARIANT_PATTERN for performance
        if not _VARIANT_PATTERN.match(v):
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=(
                    f"Invalid variant '{v}': must start with a letter or number and "
                    "contain only letters, numbers, underscores, or hyphens"
                ),
            )
        return v

    @classmethod
    def parse(cls, value: str) -> "ModelIdentifier":
        """
        Parse an identifier from its canonical string form.

        Canonical formats:
            - Basic: `namespace:name` (e.g., "onex:compute")
            - With variant: `namespace:name@variant` (e.g., "onex:handler@v2")

        Args:
            value: The canonical string to parse.

        Returns:
            ModelIdentifier instance with parsed components.

        Raises:
            ModelOnexError: If the string format is invalid.

        Examples:
            >>> ModelIdentifier.parse("onex:compute")
            ModelIdentifier(namespace='onex', name='compute', variant=None, version=None)

            >>> id = ModelIdentifier.parse("vendor:handler@async")
            >>> id.namespace
            'vendor'
            >>> id.name
            'handler'
            >>> id.variant
            'async'
        """
        if not value:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.PARSING_ERROR,
                message="Cannot parse empty string as identifier",
            )

        match = _CANONICAL_PATTERN.match(value)
        if not match:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.PARSING_ERROR,
                message=(
                    f"Invalid identifier format: '{value}'. "
                    "Expected format: 'namespace:name' or 'namespace:name@variant'"
                ),
            )

        return cls(
            namespace=match.group("namespace"),
            name=match.group("name"),
            variant=match.group("variant"),
        )

    def __str__(self) -> str:
        """
        Return the canonical string form of the identifier.

        Returns:
            String in format 'namespace:name' or 'namespace:name@variant'.

        Examples:
            >>> str(ModelIdentifier(namespace="onex", name="compute"))
            'onex:compute'
            >>> str(ModelIdentifier(namespace="vendor", name="handler", variant="v2"))
            'vendor:handler@v2'
        """
        base = f"{self.namespace}:{self.name}"
        if self.variant:
            return f"{base}@{self.variant}"
        return base

    def __repr__(self) -> str:
        """
        Return detailed representation for debugging.

        The representation includes all non-None fields in a format suitable
        for debugging and logging. Unlike __str__, this shows the full
        structure including field names.

        Returns:
            String representation in format:
            ``ModelIdentifier(namespace='x', name='y', variant='z', version=...)``

        Examples:
            >>> id1 = ModelIdentifier(namespace="onex", name="compute")
            >>> repr(id1)
            "ModelIdentifier(namespace='onex', name='compute')"

            >>> id2 = ModelIdentifier(namespace="vendor", name="handler", variant="v2")
            >>> repr(id2)
            "ModelIdentifier(namespace='vendor', name='handler', variant='v2')"
        """
        parts = [
            f"namespace={self.namespace!r}",
            f"name={self.name!r}",
        ]
        if self.variant:
            parts.append(f"variant={self.variant!r}")
        if self.version:
            parts.append(f"version={self.version!r}")
        return f"ModelIdentifier({', '.join(parts)})"

    def __eq__(self, other: object) -> bool:
        """
        Check equality with another ModelIdentifier.

        Two identifiers are equal if they have the same namespace, name,
        and variant. Version is NOT considered for equality to allow
        version-agnostic lookups.

        Args:
            other: Object to compare with.

        Returns:
            True if equal, False otherwise.
            NotImplemented if other is not a ModelIdentifier.
        """
        if not isinstance(other, ModelIdentifier):
            return NotImplemented
        return (
            self.namespace == other.namespace
            and self.name == other.name
            and self.variant == other.variant
        )

    def __ne__(self, other: object) -> bool:
        """
        Check inequality with another ModelIdentifier.

        This is the inverse of __eq__. Two identifiers are not equal if they
        differ in namespace, name, or variant. Version is NOT considered.

        Args:
            other: Object to compare with.

        Returns:
            True if not equal, False if equal.
            NotImplemented if other is not a ModelIdentifier.
        """
        result = self.__eq__(other)
        if result is NotImplemented:
            return NotImplemented
        return not result

    def __hash__(self) -> int:
        """
        Return hash for use in sets and as dict keys.

        Hash is computed from namespace, name, and variant.
        Version is excluded (consistent with __eq__).

        Returns:
            Integer hash value.
        """
        return hash((self.namespace, self.name, self.variant))

    @property
    def qualified_name(self) -> str:
        """
        Get the fully qualified name (same as __str__).

        This property provides a consistent interface with other ONEX models
        that use qualified_name (e.g., ModelEventType, ModelNodeReference).

        Returns:
            The canonical string form.
        """
        return str(self)

    def matches(self, other: "ModelIdentifier") -> bool:
        """
        Check if this identifier matches another for lookup/routing purposes.

        Matching considers namespace and name. If this identifier has a
        variant, it must match exactly; otherwise, any variant is accepted.

        Note:
            **Asymmetric Semantics**: ``A.matches(B)`` may differ from ``B.matches(A)``.

            **Quick Reference** (given base=onex:compute, v2=onex:compute@v2)::

                base.matches(v2)  -> True   # Pattern matches any variant
                v2.matches(base)  -> False  # Specific requires exact match
                v2.matches(v2)    -> True   # Same variant matches
                v2.matches(v3)    -> False  # Different variants don't match

            This is intentional for lookup scenarios:

            - **Query without variant** (pattern): Matches any variant of that name.
              Think of it as "I want any version of this handler."
            - **Query with variant** (specific): Only matches that exact variant.
              Think of it as "I want exactly this version, nothing else."

            The asymmetry enables flexible routing:

            - Use variant-less identifier to find all variants of a handler
            - Use variant-specific identifier to pin to an exact implementation

        Args:
            other: Identifier to compare against.

        Returns:
            True if this identifier matches the other according to the rules above.

        Examples:
            Variant-less (pattern) matches any variant:

            >>> base = ModelIdentifier(namespace="onex", name="compute")
            >>> v2 = ModelIdentifier(namespace="onex", name="compute", variant="v2")
            >>> v3 = ModelIdentifier(namespace="onex", name="compute", variant="v3")
            >>> base.matches(v2)  # Pattern matches specific
            True
            >>> base.matches(v3)  # Pattern matches any variant
            True

            Variant-specific requires exact match:

            >>> v2.matches(base)  # Specific does NOT match variant-less
            False
            >>> v2.matches(v3)    # Different variants don't match
            False
            >>> v2.matches(v2)    # Same variant matches
            True

            Practical usage - finding handlers:

            >>> # Registry lookup: "give me any compute handler"
            >>> query = ModelIdentifier(namespace="onex", name="compute")
            >>> handlers = [h for h in registry if query.matches(h.identifier)]
            >>>
            >>> # Pinned lookup: "give me exactly the v2 handler"
            >>> pinned = ModelIdentifier(namespace="onex", name="compute", variant="v2")
            >>> handler = next(h for h in registry if pinned.matches(h.identifier))
        """
        if self.namespace != other.namespace or self.name != other.name:
            return False
        if self.variant is not None:
            return self.variant == other.variant
        return True

    def with_variant(self, variant: str) -> "ModelIdentifier":
        """
        Create a new identifier with the specified variant.

        Args:
            variant: The variant to set.

        Returns:
            New ModelIdentifier with the variant applied.

        Examples:
            >>> base = ModelIdentifier(namespace="onex", name="compute")
            >>> versioned = base.with_variant("v2")
            >>> str(versioned)
            'onex:compute@v2'
        """
        return ModelIdentifier(
            namespace=self.namespace,
            name=self.name,
            variant=variant,
            version=self.version,
        )

    def with_version(self, version: ModelSemVer) -> "ModelIdentifier":
        """
        Create a new identifier with the specified version.

        Args:
            version: The semantic version to set.

        Returns:
            New ModelIdentifier with the version applied.

        Examples:
            >>> from omnibase_core.models.primitives.model_semver import ModelSemVer
            >>> base = ModelIdentifier(namespace="onex", name="compute")
            >>> versioned = base.with_version(ModelSemVer(major=1, minor=0, patch=0))
            >>> versioned.version
            ModelSemVer(major=1, minor=0, patch=0)
        """
        return ModelIdentifier(
            namespace=self.namespace,
            name=self.name,
            variant=self.variant,
            version=version,
        )


__all__ = ["ModelIdentifier"]
