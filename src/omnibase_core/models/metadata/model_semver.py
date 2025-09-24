"""
Semantic Version Model

Pydantic model for semantic versioning following SemVer specification.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.exceptions.onex_error import OnexError

# Import only when needed to break circular dependencies
if TYPE_CHECKING:
    from .model_input_state import ModelInputState


class ModelSemVer(BaseModel):
    """Semantic version model following SemVer specification."""

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
            raise OnexError(code=EnumCoreErrorCode.VALIDATION_ERROR, message=msg)
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

    def bump_major(self) -> ModelSemVer:
        """Bump major version, reset minor and patch to 0."""
        return ModelSemVer(major=self.major + 1, minor=0, patch=0)

    def bump_minor(self) -> ModelSemVer:
        """Bump minor version, reset patch to 0."""
        return ModelSemVer(major=self.major, minor=self.minor + 1, patch=0)

    def bump_patch(self) -> ModelSemVer:
        """Bump patch version."""
        return ModelSemVer(major=self.major, minor=self.minor, patch=self.patch + 1)

    def __eq__(self, other: object) -> bool:
        """Check equality with another ModelSemVer."""
        if not isinstance(other, ModelSemVer):
            return False
        return (
            self.major == other.major
            and self.minor == other.minor
            and self.patch == other.patch
        )

    def __lt__(self, other: object) -> bool:
        """Check if this version is less than another."""
        if not isinstance(other, ModelSemVer):
            msg = f"Cannot compare ModelSemVer with {type(other).__name__}"
            raise OnexError(code=EnumCoreErrorCode.VALIDATION_ERROR, message=msg)
        return (self.major, self.minor, self.patch) < (
            other.major,
            other.minor,
            other.patch,
        )

    def __le__(self, other: object) -> bool:
        """Check if this version is less than or equal to another."""
        return self == other or self < other

    def __gt__(self, other: object) -> bool:
        """Check if this version is greater than another."""
        if not isinstance(other, ModelSemVer):
            msg = f"Cannot compare ModelSemVer with {type(other).__name__}"
            raise OnexError(code=EnumCoreErrorCode.VALIDATION_ERROR, message=msg)
        return (self.major, self.minor, self.patch) > (
            other.major,
            other.minor,
            other.patch,
        )

    def __ge__(self, other: object) -> bool:
        """Check if this version is greater than or equal to another."""
        return self == other or self > other

    def __hash__(self) -> int:
        """Hash function for use in sets and as dict keys."""
        return hash((self.major, self.minor, self.patch))


def parse_semver_from_string(version_str: str) -> ModelSemVer:
    """
    Parse semantic version string into ModelSemVer using ONEX-compliant patterns.

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
    import re

    # Basic SemVer regex pattern for major.minor.patch
    pattern = r"^(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)"

    match = re.match(pattern, version_str)
    if not match:
        msg = f"Invalid semantic version format: {version_str}"
        raise OnexError(code=EnumCoreErrorCode.VALIDATION_ERROR, message=msg)

    # Use Pydantic's model validation instead of direct construction
    return ModelSemVer.model_validate(
        {
            "major": int(match.group("major")),
            "minor": int(match.group("minor")),
            "patch": int(match.group("patch")),
        },
    )


def parse_input_state_version(
    input_state: Any,
) -> ModelSemVer:
    """
    Parse a version from an input state dict, requiring structured dictionary format.

    Args:
        input_state: The input state (ModelInputState or dict with 'version' key) - validated at runtime

    Returns:
        ModelSemVer instance

    Raises:
        ValueError: If version is missing, is a string, or has invalid format
    """
    # Convert to structured input state for better type safety
    # Use delayed import to break circular dependencies
    from .model_input_state import ModelInputState

    if isinstance(input_state, ModelInputState):
        structured_state = input_state
    else:
        structured_state = ModelInputState.model_validate(input_state)
    v = structured_state.get_version_data()

    if v is None:
        msg = "Version field is required in input state"
        raise OnexError(code=EnumCoreErrorCode.VALIDATION_ERROR, message=msg)

    if isinstance(v, str):
        msg = (
            f"String versions are not allowed. Use structured format: "
            f"{{major: X, minor: Y, patch: Z}}. Got string: {v}"
        )
        raise OnexError(code=EnumCoreErrorCode.VALIDATION_ERROR, message=msg)

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
            raise OnexError(code=EnumCoreErrorCode.VALIDATION_ERROR, message=msg) from e

    msg = (
        f"Version must be a ModelSemVer instance or dictionary with {{major, minor, patch}} keys. "
        f"Got {type(v).__name__}: {v}"
    )
    raise OnexError(code=EnumCoreErrorCode.VALIDATION_ERROR, message=msg)
