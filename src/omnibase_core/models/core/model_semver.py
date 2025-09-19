"""
Semantic Version Model

Pydantic model for semantic versioning following SemVer specification.
"""

from typing import Type

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ModelSemVer(BaseModel):
    """Semantic version model following SemVer specification."""

    major: int = Field(ge=0, description="Major version number")
    minor: int = Field(ge=0, description="Minor version number")
    patch: int = Field(ge=0, description="Patch version number")

    model_config = ConfigDict(frozen=True, extra="ignore")

    @field_validator("major", "minor", "patch")
    @classmethod
    def validate_non_negative(cls: Type["ModelSemVer"], v: int) -> int:
        """Validate version numbers are non-negative."""
        if v < 0:
            msg = "Version numbers must be non-negative"
            raise ValueError(msg)
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
        if not isinstance(other, ModelSemVer):
            raise TypeError(f"Cannot compare ModelSemVer with {type(other)}")
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
        if not isinstance(other, ModelSemVer):
            raise TypeError(f"Cannot compare ModelSemVer with {type(other)}")
        return (self.major, self.minor, self.patch) > (
            other.major,
            other.minor,
            other.patch,
        )

    def __ge__(self, other: "ModelSemVer") -> bool:
        """Check if this version is greater than or equal to another."""
        return self == other or self > other

    def __hash__(self) -> int:
        """Hash function for use in sets and as dict keys."""
        return hash((self.major, self.minor, self.patch))

    @classmethod
    def parse(cls, version_str: str) -> "ModelSemVer":
        """Parse semantic version string into ModelSemVer instance."""
        if not isinstance(version_str, str):
            msg = f"Version must be a string, got {type(version_str)}"  # type: ignore[unreachable]
            raise ValueError(msg)

        parts = version_str.strip().split(".")
        if len(parts) != 3:
            msg = f"Invalid semantic version format: {version_str}. Expected 'major.minor.patch'"
            raise ValueError(msg)

        try:
            major = int(parts[0])
            minor = int(parts[1])
            patch = int(parts[2])
        except ValueError as e:
            msg = f"Invalid semantic version format: {version_str}. All parts must be integers"
            raise ValueError(msg) from e

        return cls(major=major, minor=minor, patch=patch)


# Utility function for external modules
def parse_semver_from_string(version_str: str) -> ModelSemVer:
    """Parse semantic version string into ModelSemVer instance."""
    return ModelSemVer.parse(version_str)


# Type alias for use in models - enforce proper ModelSemVer instances only
SemVerField = ModelSemVer
