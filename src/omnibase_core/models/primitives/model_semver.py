"""
Semantic Version Model

Pydantic model for semantic versioning following SemVer 2.0.0 specification.

See: https://semver.org/spec/v2.0.0.html
"""

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.types.type_serializable_value import SerializedDict

# Full SemVer 2.0.0 regex pattern
# Format: MAJOR.MINOR.PATCH[-PRERELEASE][+BUILD]
# - MAJOR, MINOR, PATCH: non-negative integers without leading zeros (except 0)
# - PRERELEASE: dot-separated identifiers (alphanumeric + hyphen, numeric only must not have leading zeros)
# - BUILD: dot-separated identifiers (alphanumeric + hyphen)
_SEMVER_PATTERN = re.compile(
    r"^(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)"
    r"(?:-(?P<prerelease>(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)"
    r"(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
    r"(?:\+(?P<build>[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
)

# Pattern for validating individual prerelease identifiers
_PRERELEASE_NUMERIC_PATTERN = re.compile(r"^(0|[1-9]\d*)$")
_PRERELEASE_ALPHANUMERIC_PATTERN = re.compile(r"^[0-9a-zA-Z-]+$")

# Pattern to detect purely numeric strings with leading zeros (e.g., "01", "007", "00")
# Per SemVer 2.0.0 spec: "Numeric identifiers MUST NOT include leading zeroes."
# These are INVALID - not just treated as alphanumeric strings.
_NUMERIC_WITH_LEADING_ZEROS_PATTERN = re.compile(r"^0\d+$")

# Pattern for validating build metadata identifiers
_BUILD_IDENTIFIER_PATTERN = re.compile(r"^[0-9a-zA-Z-]+$")


def _parse_prerelease_identifier(identifier: str) -> str | int:
    """Parse a single prerelease identifier.

    Per SemVer spec:
    - Numeric identifiers must not have leading zeros
    - Returns int for numeric, str for alphanumeric

    Raises:
        ModelOnexError: If identifier is a numeric string with leading zeros
            (e.g., "007", "01", "00"). Per SemVer 2.0.0 spec, these are invalid.
    """
    # Check for invalid numeric identifiers with leading zeros (e.g., "007", "01")
    # Per SemVer spec: "Numeric identifiers MUST NOT include leading zeroes."
    if _NUMERIC_WITH_LEADING_ZEROS_PATTERN.match(identifier):
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"Invalid prerelease identifier '{identifier}': numeric identifiers must not have leading zeros",
        )
    if _PRERELEASE_NUMERIC_PATTERN.match(identifier):
        return int(identifier)
    return identifier


def _compare_prerelease_identifier(a: str | int, b: str | int) -> int:
    """Compare two prerelease identifiers per SemVer spec.

    Rules:
    - Numeric < alphanumeric
    - Numeric compared as integers
    - Alphanumeric compared lexically (ASCII sort order)

    Returns:
        -1 if a < b, 0 if a == b, 1 if a > b
    """
    if isinstance(a, int) and isinstance(b, int):
        # Both numeric: compare as integers
        if a < b:
            return -1
        if a > b:
            return 1
        return 0
    elif isinstance(a, int):
        # Numeric < alphanumeric
        return -1
    elif isinstance(b, int):
        # Alphanumeric > numeric
        return 1
    else:
        # Both alphanumeric (both str): compare lexically
        # Type narrowing: at this point, a and b are both str
        a_str: str = a
        b_str: str = b
        if a_str < b_str:
            return -1
        if a_str > b_str:
            return 1
        return 0


class ModelSemVer(BaseModel):
    """
    Semantic version model following SemVer 2.0.0 specification.

    Full SemVer format: MAJOR.MINOR.PATCH[-prerelease][+build]

    Preferred usage (structured format):
        >>> version = ModelSemVer(major=0, minor=4, patch=0)
        >>> assert str(version) == "0.4.0"
        >>> assert version.major == 0 and version.minor == 4

    With prerelease and build metadata:
        >>> version = ModelSemVer(major=1, minor=0, patch=0, prerelease=("alpha", 1))
        >>> assert str(version) == "1.0.0-alpha.1"
        >>> assert version.is_prerelease() is True

    For parsing external input, use the parse() class method:
        >>> version = ModelSemVer.parse("1.0.0-alpha.1+build.123")
        >>> assert version.prerelease == ("alpha", 1)
        >>> assert version.build == ("build", "123")

    Precedence rules (per SemVer spec):
        - prerelease < no prerelease (1.0.0-alpha < 1.0.0)
        - Numeric identifiers < alphanumeric (1.0.0-1 < 1.0.0-alpha)
        - Build metadata is IGNORED for precedence

    Note:
        String version literals like "1.0.0" are deprecated.
        Always use structured format: ModelSemVer(major=X, minor=Y, patch=Z)

        This model is frozen (immutable) and hashable, suitable for use as dict
        keys or in sets. Hash is based on major, minor, patch, and prerelease;
        build metadata is excluded (see __hash__ docstring for details).
    """

    # from_attributes=True allows Pydantic to accept objects with matching
    # attributes even when class identity differs (e.g., in pytest-xdist
    # parallel execution where model classes are imported in separate workers)
    model_config = ConfigDict(frozen=True, extra="ignore", from_attributes=True)

    major: int = Field(ge=0, description="Major version number")
    minor: int = Field(ge=0, description="Minor version number")
    patch: int = Field(ge=0, description="Patch version number")
    prerelease: tuple[str | int, ...] | None = Field(
        default=None,
        description="Prerelease identifiers (dot-separated in string form)",
    )
    build: tuple[str, ...] | None = Field(
        default=None,
        description="Build metadata identifiers (ignored for precedence)",
    )

    @field_validator("major", "minor", "patch")
    @classmethod
    def validate_non_negative(cls, v: int) -> int:
        """Validate version numbers are non-negative."""
        if v < 0:
            msg = "Version numbers must be non-negative"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )
        return v

    @field_validator("prerelease", mode="before")
    @classmethod
    def validate_prerelease(
        cls, v: tuple[str | int, ...] | list[str | int] | None
    ) -> tuple[str | int, ...] | None:
        """Validate and normalize prerelease identifiers.

        Per SemVer 2.0.0 spec, purely numeric identifiers are stored as int type
        for proper numeric comparison (e.g., "1" -> 1, so 1 < 2 < 10, not "1" < "10" < "2").
        """
        if v is None:
            return None
        if isinstance(v, list):
            v = tuple(v)
        if not isinstance(v, tuple):
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Prerelease must be a tuple, got {type(v).__name__}",
            )
        if len(v) == 0:
            return None  # Empty tuple treated as no prerelease
        # Validate and normalize each identifier
        normalized: list[str | int] = []
        for identifier in v:
            if isinstance(identifier, int):
                if identifier < 0:
                    raise ModelOnexError(
                        error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                        message=f"Numeric prerelease identifier cannot be negative: {identifier}",
                    )
                normalized.append(identifier)
            elif isinstance(identifier, str):
                if not _PRERELEASE_ALPHANUMERIC_PATTERN.match(identifier):
                    raise ModelOnexError(
                        error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                        message=f"Invalid prerelease identifier: {identifier}",
                    )
                # Per SemVer 2.0.0 spec: "Numeric identifiers MUST NOT include leading zeroes."
                # Reject purely numeric strings with leading zeros (e.g., "007", "01", "00")
                if _NUMERIC_WITH_LEADING_ZEROS_PATTERN.match(identifier):
                    raise ModelOnexError(
                        error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                        message=f"Invalid prerelease identifier '{identifier}': numeric identifiers must not have leading zeros",
                    )
                # Per SemVer 2.0.0 spec: purely numeric identifiers should be stored as int
                # This ensures proper numeric comparison (1 < 2 < 10, not "1" < "10" < "2")
                if _PRERELEASE_NUMERIC_PATTERN.match(identifier):
                    normalized.append(int(identifier))
                else:
                    normalized.append(identifier)
            else:
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=f"Prerelease identifier must be str or int, got {type(identifier).__name__}",
                )
        return tuple(normalized)

    @field_validator("build", mode="before")
    @classmethod
    def validate_build(
        cls, v: tuple[str, ...] | list[str] | None
    ) -> tuple[str, ...] | None:
        """Validate and normalize build metadata identifiers."""
        if v is None:
            return None
        if isinstance(v, list):
            v = tuple(v)
        if not isinstance(v, tuple):
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Build must be a tuple, got {type(v).__name__}",
            )
        if len(v) == 0:
            return None  # Empty tuple treated as no build metadata
        # Validate each identifier
        for identifier in v:
            if not isinstance(identifier, str):
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=f"Build identifier must be str, got {type(identifier).__name__}",
                )
            if not _BUILD_IDENTIFIER_PATTERN.match(identifier):
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=f"Invalid build metadata identifier: {identifier}",
                )
        return v

    def __str__(self) -> str:
        """
        Return the version as a SemVer 2.0.0 string.

        Format: ``MAJOR.MINOR.PATCH[-prerelease][+build]``

        The prerelease identifiers (if present) are joined with dots and
        prefixed with a hyphen. Build metadata (if present) is joined with
        dots and prefixed with a plus sign.

        Returns:
            Version string in SemVer format (e.g., "1.2.3", "1.0.0-alpha.1",
            "1.0.0-beta+build.123")

        Example:
            >>> version = ModelSemVer(major=1, minor=2, patch=3)
            >>> str(version)
            '1.2.3'
            >>> str(ModelSemVer(major=1, minor=0, patch=0, prerelease=("alpha", 1)))
            '1.0.0-alpha.1'
        """
        result = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            result += "-" + ".".join(str(p) for p in self.prerelease)
        if self.build:
            result += "+" + ".".join(self.build)
        return result

    def to_string(self) -> str:
        """Convert to semantic version string."""
        return str(self)

    def is_prerelease(self) -> bool:
        """Check if this is a pre-release version."""
        return self.prerelease is not None

    def precedence_key(
        self,
    ) -> tuple[int, int, int, int, tuple[tuple[int, str | int], ...]]:
        """Return a tuple for ordering that ignores build metadata.

        Per SemVer spec:
        - Build metadata SHOULD be ignored when determining version precedence
        - Prerelease versions have lower precedence than normal versions

        The returned tuple can be used for sorting and comparison:
        - (major, minor, patch, is_release, prerelease_comparators)
        - is_release=1 (release) sorts after is_release=0 (prerelease)

        Use this method when you need to compare or sort versions by precedence,
        where build metadata differences should be treated as equivalent.

        Example:
            >>> v1 = ModelSemVer.parse("1.0.0+build.123")
            >>> v2 = ModelSemVer.parse("1.0.0+build.456")
            >>> v1.precedence_key() == v2.precedence_key()  # Same precedence
            True
            >>> v1.exact_key() == v2.exact_key()  # Different exact identity
            False

        Returns:
            Tuple suitable for comparison operations.
        """
        if self.prerelease is None:
            # No prerelease: sort after all prereleases
            # Use is_release=1 to sort after prereleases (is_release=0)
            return (self.major, self.minor, self.patch, 1, ())
        else:
            # Has prerelease: include typed comparators
            # Use is_release=0 to sort before release versions
            # Each identifier gets (type_order, value) where:
            # - type_order=0 for int (sorts before strings)
            # - type_order=1 for str
            comparators: list[tuple[int, str | int]] = []
            for p in self.prerelease:
                if isinstance(p, int):
                    comparators.append((0, p))
                else:
                    comparators.append((1, p))
            return (self.major, self.minor, self.patch, 0, tuple(comparators))

    def exact_key(
        self,
    ) -> tuple[int, int, int, tuple[str | int, ...] | None, tuple[str, ...] | None]:
        """Return a tuple for exact identity comparison (includes build metadata).

        Unlike precedence_key(), this includes build metadata for cases where
        exact version identity matters, such as caching or deduplication where
        different builds of the same version should be tracked separately.

        Example:
            >>> v1 = ModelSemVer.parse("1.0.0+build.123")
            >>> v2 = ModelSemVer.parse("1.0.0+build.456")
            >>> # For sorting/comparison, use precedence_key():
            >>> v1.precedence_key() == v2.precedence_key()  # Same precedence
            True
            >>> # For exact caching where build metadata matters, use exact_key():
            >>> cache = {}
            >>> cache[v1.exact_key()] = "data for build 123"
            >>> cache[v2.exact_key()] = "data for build 456"
            >>> len(cache)  # Two separate entries
            2

        Returns:
            Tuple including all version components.
        """
        return (self.major, self.minor, self.patch, self.prerelease, self.build)

    def bump_major(self) -> "ModelSemVer":
        """Bump major version, reset minor and patch to 0, clear prerelease and build."""
        return ModelSemVer(major=self.major + 1, minor=0, patch=0)

    def bump_minor(self) -> "ModelSemVer":
        """Bump minor version, reset patch to 0, clear prerelease and build."""
        return ModelSemVer(major=self.major, minor=self.minor + 1, patch=0)

    def bump_patch(self) -> "ModelSemVer":
        """Bump patch version, clear prerelease and build."""
        return ModelSemVer(major=self.major, minor=self.minor, patch=self.patch + 1)

    def __eq__(self, other: object) -> bool:
        """Check equality with another ModelSemVer.

        Per SemVer spec, build metadata SHOULD be ignored for precedence.
        Two versions with same major.minor.patch and prerelease are equal
        even if build metadata differs.
        """
        if not isinstance(other, ModelSemVer):
            return NotImplemented
        return (
            self.major == other.major
            and self.minor == other.minor
            and self.patch == other.patch
            and self.prerelease == other.prerelease
        )

    def __ne__(self, other: object) -> bool:
        """Check inequality with another ModelSemVer.

        Explicit implementation for clarity, though Python 3 provides a default.
        """
        result = self.__eq__(other)
        if result is NotImplemented:
            return NotImplemented
        return not result

    def __lt__(self, other: object) -> bool:
        """Check if this version is less than another (per SemVer spec).

        Precedence rules:
        1. Compare major.minor.patch numerically
        2. Prerelease version < normal version (1.0.0-alpha < 1.0.0)
        3. Prerelease identifiers compared left to right:
           - Numeric identifiers compared as integers
           - Alphanumeric identifiers compared lexically
           - Numeric < alphanumeric
           - Fewer identifiers < more identifiers (if all preceding are equal)
        4. Build metadata is IGNORED

        Returns:
            bool: True if self < other
            NotImplemented: If other is not a ModelSemVer instance
        """
        if not isinstance(other, ModelSemVer):
            return NotImplemented
        return self.precedence_key() < other.precedence_key()

    def __le__(self, other: object) -> bool:
        """Check if this version is less than or equal to another."""
        if not isinstance(other, ModelSemVer):
            return NotImplemented
        return self.precedence_key() <= other.precedence_key()

    def __gt__(self, other: object) -> bool:
        """Check if this version is greater than another."""
        if not isinstance(other, ModelSemVer):
            return NotImplemented
        return self.precedence_key() > other.precedence_key()

    def __ge__(self, other: object) -> bool:
        """Check if this version is greater than or equal to another."""
        if not isinstance(other, ModelSemVer):
            return NotImplemented
        return self.precedence_key() >= other.precedence_key()

    def __hash__(self) -> int:
        """Return hash value for use in sets and as dict keys.

        Hash is based on major, minor, patch, and prerelease.
        Build metadata is excluded (consistent with __eq__).

        Warning:
            Using ModelSemVer instances directly as dict keys or in sets will
            ignore build metadata differences. Two versions that differ only in
            build metadata will hash to the same value and compare as equal.
            If build metadata matters for caching or deduplication, use
            exact_key() as the dict key instead.

        Example:
            >>> v1 = ModelSemVer.parse("1.0.0+build.123")
            >>> v2 = ModelSemVer.parse("1.0.0+build.456")
            >>> # Direct use as dict key ignores build metadata:
            >>> cache = {v1: "data"}
            >>> cache[v2] = "overwritten"  # v2 overwrites v1's entry!
            >>> len(cache)
            1
            >>> # Use exact_key() when build metadata matters:
            >>> cache = {}
            >>> cache[v1.exact_key()] = "data for build 123"
            >>> cache[v2.exact_key()] = "data for build 456"
            >>> len(cache)  # Two separate entries
            2

        Returns:
            int: Hash computed from version tuple.
        """
        return hash((self.major, self.minor, self.patch, self.prerelease))

    @classmethod
    def parse(cls, version_str: str) -> "ModelSemVer":
        """
        Parse semantic version string into ModelSemVer (class method alias).

        Supports full SemVer 2.0.0 format:
            MAJOR.MINOR.PATCH[-prerelease][+build]

        Examples:
            >>> ModelSemVer.parse("1.0.0")
            ModelSemVer(major=1, minor=0, patch=0)

            >>> ModelSemVer.parse("1.0.0-alpha")
            ModelSemVer(major=1, minor=0, patch=0, prerelease=("alpha",))

            >>> ModelSemVer.parse("1.0.0-alpha.1")
            ModelSemVer(major=1, minor=0, patch=0, prerelease=("alpha", 1))

            >>> ModelSemVer.parse("1.0.0+build.123")
            ModelSemVer(major=1, minor=0, patch=0, build=("build", "123"))

            >>> ModelSemVer.parse("1.0.0-beta.2+build.456")
            ModelSemVer(major=1, minor=0, patch=0, prerelease=("beta", 2), build=("build", "456"))

        Args:
            version_str: Semantic version string

        Returns:
            ModelSemVer instance

        Raises:
            ModelOnexError: If version string format is invalid
        """
        return parse_semver_from_string(version_str)


# Type alias for use in models - enforce proper ModelSemVer instances only
SemVerField = ModelSemVer


def default_model_version() -> ModelSemVer:
    """
    Create default ModelSemVer instance (1.0.0).

    This factory function is used as default_factory for version fields across
    all ONEX models, providing a centralized way to specify the default version.

    Returns:
        ModelSemVer instance with major=1, minor=0, patch=0

    Example:
        >>> class MyModel(BaseModel):
        ...     version: ModelSemVer = Field(default_factory=default_model_version)
    """
    return ModelSemVer(major=1, minor=0, patch=0)


def parse_semver_from_string(version_str: str) -> ModelSemVer:
    """
    Parse semantic version string into ModelSemVer using full SemVer 2.0.0 spec.

    This function parses the complete SemVer format including prerelease
    and build metadata.

    Args:
        version_str: Semantic version string (e.g., "1.2.3-alpha.1+build.123")

    Returns:
        ModelSemVer instance validated through Pydantic

    Raises:
        ModelOnexError: If version string format is invalid

    Example:
        >>> version = parse_semver_from_string("1.2.3-alpha.1+build")
        >>> assert version.major == 1 and version.minor == 2 and version.patch == 3
        >>> assert version.prerelease == ("alpha", 1)
        >>> assert version.build == ("build",)
    """
    match = _SEMVER_PATTERN.match(version_str)
    if not match:
        msg = f"Invalid semantic version format: {version_str}"
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=msg,
        )

    # Parse major, minor, patch
    major = int(match.group("major"))
    minor = int(match.group("minor"))
    patch = int(match.group("patch"))

    # Parse prerelease identifiers
    prerelease: tuple[str | int, ...] | None = None
    prerelease_str = match.group("prerelease")
    if prerelease_str:
        identifiers = prerelease_str.split(".")
        parsed_identifiers: list[str | int] = []
        for identifier in identifiers:
            parsed_identifiers.append(_parse_prerelease_identifier(identifier))
        prerelease = tuple(parsed_identifiers)

    # Parse build metadata
    build: tuple[str, ...] | None = None
    build_str = match.group("build")
    if build_str:
        build = tuple(build_str.split("."))

    # Use Pydantic's model validation
    return ModelSemVer.model_validate(
        {
            "major": major,
            "minor": minor,
            "patch": patch,
            "prerelease": prerelease,
            "build": build,
        }
    )


def parse_input_state_version(input_state: SerializedDict) -> "ModelSemVer":
    """
    Parse a version from an input state dict[str, Any], requiring structured dictionary format.

    Args:
        input_state: The input state dictionary (must have a 'version' key)

    Returns:
        ModelSemVer instance

    Raises:
        ModelOnexError: If version is missing, is a string, or has invalid format
    """
    v = input_state.get("version")

    if v is None:
        msg = "Version field is required in input state"
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=msg,
        )

    if isinstance(v, str):
        msg = (
            f"String versions are not allowed. Use structured format: "
            f"{{major: X, minor: Y, patch: Z}}. Got string: {v}"
        )
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=msg,
        )

    if isinstance(v, ModelSemVer):
        return v

    if isinstance(v, dict):
        try:
            return ModelSemVer.model_validate(v)
        except (AttributeError, TypeError, ValueError) as e:
            msg = (
                f"Invalid version dictionary format. Expected {{major: int, minor: int, patch: int}}. "
                f"Got: {v}. Error: {e}"
            )
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            ) from e

    msg = (
        f"Version must be a ModelSemVer instance or dictionary with {{major, minor, patch}} keys. "
        f"Got {type(v).__name__}: {v}"
    )
    raise ModelOnexError(
        error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        message=msg,
    )
