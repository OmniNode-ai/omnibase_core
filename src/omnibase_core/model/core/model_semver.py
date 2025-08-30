"""
Semantic Version Model

Pydantic model for semantic versioning following SemVer specification.
"""

from pydantic import BaseModel, ConfigDict, Field, field_validator


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
            raise ValueError("Version numbers must be non-negative")
        return v

    def __str__(self) -> str:
        """String representation in SemVer format."""
        return f"{self.major}.{self.minor}.{self.patch}"

    def to_string(self) -> str:
        """Convert to semantic version string."""
        return str(self)

    @classmethod
    def from_string(cls, version_str: str) -> "ModelSemVer":
        """Create ModelSemVer from version string."""
        import re

        # Basic SemVer regex pattern for major.minor.patch
        pattern = (
            r"^(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)"
        )

        match = re.match(pattern, version_str)
        if not match:
            raise ValueError(f"Invalid semantic version format: {version_str}")

        return cls(
            major=int(match.group("major")),
            minor=int(match.group("minor")),
            patch=int(match.group("patch")),
        )

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


# Type alias for use in models - enforce proper ModelSemVer instances only
SemVerField = ModelSemVer


def parse_input_state_version(input_state: dict) -> "ModelSemVer":
    """
    Parse a version from an input state dict, requiring structured dictionary format.

    Args:
        input_state: The input state dictionary (must have a 'version' key)

    Returns:
        ModelSemVer instance

    Raises:
        ValueError: If version is missing, is a string, or has invalid format
    """
    v = input_state.get("version")

    if v is None:
        raise ValueError("Version field is required in input state")

    if isinstance(v, str):
        raise ValueError(
            f"String versions are not allowed. Use structured format: "
            f"{{major: X, minor: Y, patch: Z}}. Got string: {v}"
        )

    if isinstance(v, ModelSemVer):
        return v

    if isinstance(v, dict):
        try:
            return ModelSemVer(**v)
        except Exception as e:
            raise ValueError(
                f"Invalid version dictionary format. Expected {{major: int, minor: int, patch: int}}. "
                f"Got: {v}. Error: {e}"
            ) from e

    raise ValueError(
        f"Version must be a ModelSemVer instance or dictionary with {{major, minor, patch}} keys. "
        f"Got {type(v).__name__}: {v}"
    )
