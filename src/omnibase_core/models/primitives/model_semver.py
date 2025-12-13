import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.types.type_serializable_value import SerializedDict

# Pre-compiled SemVer pattern for performance
# Basic SemVer regex pattern for major.minor.patch
# Allows prerelease/metadata suffix (e.g., "1.2.3-alpha" or "1.2.3+build")
# But ensures version ends after patch or has valid separator (-, +)
_SEMVER_PATTERN = re.compile(
    r"^(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)(?:[-+].*)?$"
)

"""
Semantic Version Model

Pydantic model for semantic versioning following SemVer specification.
"""


class ModelSemVer(BaseModel):
    """
    Semantic version model following SemVer specification.

    Preferred usage (structured format):
        >>> version = ModelSemVer(major=0, minor=4, patch=0)
        >>> assert str(version) == "0.4.0"
        >>> assert version.major == 0 and version.minor == 4

    For parsing external input, use the parse() class method:
        >>> version = ModelSemVer.parse("0.4.0")
        >>> assert version == ModelSemVer(major=0, minor=4, patch=0)

    Note: String version literals like "1.0.0" are deprecated.
    Always use structured format: ModelSemVer(major=X, minor=Y, patch=Z)
    """

    major: int = Field(ge=0, description="Major version number")
    minor: int = Field(ge=0, description="Minor version number")
    patch: int = Field(ge=0, description="Patch version number")

    model_config = ConfigDict(frozen=True, extra="ignore")

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

    def __str__(self) -> str:
        """String representation in SemVer format."""
        return f"{self.major}.{self.minor}.{self.patch}"

    def to_string(self) -> str:
        """Convert to semantic version string."""
        return str(self)

    def is_prerelease(self) -> bool:
        """Check if this is a pre-release version."""
        return False  # No prerelease support in simplified version

    def bump_major(self) -> "ModelSemVer":
        """Bump major version, reset minor and patch to 0."""
        return ModelSemVer(major=self.major + 1, minor=0, patch=0)

    def bump_minor(self) -> "ModelSemVer":
        """Bump minor version, reset patch to 0."""
        return ModelSemVer(major=self.major, minor=self.minor + 1, patch=0)

    def bump_patch(self) -> "ModelSemVer":
        """Bump patch version."""
        return ModelSemVer(major=self.major, minor=self.minor, patch=self.patch + 1)

    def __eq__(self, other: object) -> bool:
        """Check equality with another ModelSemVer."""
        if not isinstance(other, ModelSemVer):
            return NotImplemented
        return (
            self.major == other.major
            and self.minor == other.minor
            and self.patch == other.patch
        )

    def __lt__(self, other: "ModelSemVer") -> bool:
        """Check if this version is less than another."""
        return (self.major, self.minor, self.patch) < (
            other.major,
            other.minor,
            other.patch,
        )

    def __le__(self, other: "ModelSemVer") -> bool:
        """Check if this version is less than or equal to another."""
        return self == other or self < other

    def __gt__(self, other: "ModelSemVer") -> bool:
        """Check if this version is greater than another."""
        return (self.major, self.minor, self.patch) > (
            other.major,
            other.minor,
            other.patch,
        )

    def __ge__(self, other: "ModelSemVer") -> bool:
        """Check if this version is greater than or equal to another."""
        return self == other or self > other

    def __hash__(self) -> int:
        """Return hash value for use in sets and as dict keys.

        Returns:
            int: Hash computed from (major, minor, patch) version tuple.
        """
        return hash((self.major, self.minor, self.patch))

    @classmethod
    def parse(cls, version_str: str) -> "ModelSemVer":
        """
        Parse semantic version string into ModelSemVer (class method alias).

        Note: For new code, prefer direct construction:
            >>> version = ModelSemVer(major=1, minor=2, patch=3)

        This method is primarily for parsing external input:
            >>> version = ModelSemVer.parse("1.2.3")
            >>> assert version.major == 1

        Args:
            version_str: Semantic version string (e.g., "1.2.3")

        Returns:
            ModelSemVer instance
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
    Parse semantic version string into ModelSemVer using ONEX-compatible patterns.

    This function replaces the old ModelSemVer.from_string() factory method
    with proper validation through Pydantic's model creation.

    Args:
        version_str: Semantic version string (e.g., "1.2.3")

    Returns:
        ModelSemVer instance validated through Pydantic

    Raises:
        ValueError: If version string format is invalid

    Example:
        >>> version = parse_semver_from_string("1.2.3")
        >>> assert version.major == 1 and version.minor == 2 and version.patch == 3
    """
    match = _SEMVER_PATTERN.match(version_str)
    if not match:
        msg = f"Invalid semantic version format: {version_str}"
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=msg,
        )

    # Use Pydantic's model validation instead of direct construction
    return ModelSemVer.model_validate(
        {
            "major": int(match.group("major")),
            "minor": int(match.group("minor")),
            "patch": int(match.group("patch")),
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
        ModelOnexError: If version is missing, is an invalid type, or has invalid format

    Type Handling:
        - None: Rejected - version is required
        - str: Rejected - use structured format instead
        - bool: Rejected - bool is not a valid version type (even though bool is int subclass)
        - int/float: Rejected - scalar numbers are not valid versions
        - ModelSemVer: Returned as-is
        - dict: Parsed as {major, minor, patch} structure
        - Other types: Rejected with descriptive error
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

    # Check bool BEFORE int (bool is subclass of int in Python)
    if isinstance(v, bool):
        msg = (
            f"Boolean is not a valid version type. Use structured format: "
            f"{{major: X, minor: Y, patch: Z}}. Got bool: {v}"
        )
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=msg,
        )

    # Reject scalar numbers (int, float) - they're not valid version formats
    if isinstance(v, (int, float)):
        msg = (
            f"Scalar numbers are not valid version types. Use structured format: "
            f"{{major: X, minor: Y, patch: Z}}. Got {type(v).__name__}: {v}"
        )
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=msg,
        )

    if isinstance(v, ModelSemVer):
        return v

    if isinstance(v, dict):
        try:
            return ModelSemVer(**v)
        except Exception as e:
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
