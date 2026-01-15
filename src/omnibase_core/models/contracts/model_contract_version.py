"""
Contract Version Model

Provides typed semantic versioning for ONEX contracts with downgrade protection.
This model is optimized for contract versioning where version progression
rules are strictly enforced by CI.

See: CONTRACT_STABILITY_SPEC.md for detailed specification.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError


class ModelContractVersion(BaseModel):
    """
    Typed semver fields for contract versioning.

    Provides semantic versioning with downgrade protection for ONEX contracts.
    Implements full comparison operators and progression validation.

    Attributes:
        major: Major version component (breaking changes)
        minor: Minor version component (new features, backward compatible)
        patch: Patch version component (bug fixes)

    Example:
        >>> version = ModelContractVersion(major=1, minor=2, patch=3)
        >>> str(version)
        '1.2.3'
        >>> version.bump_minor()
        ModelContractVersion(major=1, minor=3, patch=0)
    """

    major: int = Field(..., ge=0, description="Major version (breaking changes)")
    minor: int = Field(..., ge=0, description="Minor version (backward compatible)")
    patch: int = Field(..., ge=0, description="Patch version (bug fixes)")

    model_config = ConfigDict(
        extra="forbid",  # Strict - no extra fields
        from_attributes=True,  # Required for pytest-xdist compatibility
        frozen=True,  # Immutable
        strict=True,  # Strict type checking - no coercion
        validate_assignment=True,
    )

    def __str__(self) -> str:
        """Return string representation in 'X.Y.Z' format."""
        return f"{self.major}.{self.minor}.{self.patch}"

    def __repr__(self) -> str:
        """Return detailed representation with class name and fields."""
        return f"ModelContractVersion(major={self.major}, minor={self.minor}, patch={self.patch})"

    def to_string(self) -> str:
        """Convert to semantic version string (alias for __str__)."""
        return str(self)

    def to_tuple(self) -> tuple[int, int, int]:
        """Convert to tuple (major, minor, patch)."""
        return (self.major, self.minor, self.patch)

    @classmethod
    def from_string(cls, version_str: str) -> ModelContractVersion:
        """
        Parse a version string in 'X.Y.Z' format.

        Supports optional prerelease (-alpha) and build metadata (+build) suffixes,
        which are ignored for the version comparison.

        Args:
            version_str: Version string in 'X.Y.Z' format

        Returns:
            ModelContractVersion instance

        Raises:
            ModelOnexError: If version string format is invalid

        Example:
            >>> ModelContractVersion.from_string("1.2.3")
            ModelContractVersion(major=1, minor=2, patch=3)
        """
        # SemVer pattern allowing prerelease/metadata suffix
        pattern = r"^(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)(?:[-+].*)?$"

        match = re.match(pattern, version_str)
        if not match:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Invalid contract version format: '{version_str}'. Expected 'X.Y.Z' format.",
            )

        return cls(
            major=int(match.group("major")),
            minor=int(match.group("minor")),
            patch=int(match.group("patch")),
        )

    @classmethod
    def from_tuple(cls, version_tuple: tuple[int, int, int]) -> ModelContractVersion:
        """
        Create a ModelContractVersion from a tuple.

        Args:
            version_tuple: Tuple of (major, minor, patch)

        Returns:
            ModelContractVersion instance

        Raises:
            ModelOnexError: If tuple does not have exactly 3 elements

        Example:
            >>> ModelContractVersion.from_tuple((1, 2, 3))
            ModelContractVersion(major=1, minor=2, patch=3)
        """
        if len(version_tuple) != 3:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Version tuple must have exactly 3 elements, got {len(version_tuple)}",
            )
        return cls(
            major=version_tuple[0], minor=version_tuple[1], patch=version_tuple[2]
        )

    def __eq__(self, other: object) -> bool:
        """Check equality with another ModelContractVersion."""
        if not isinstance(other, ModelContractVersion):
            return NotImplemented
        return self.to_tuple() == other.to_tuple()

    def __lt__(self, other: object) -> bool:
        """Check if this version is less than another."""
        if not isinstance(other, ModelContractVersion):
            return NotImplemented
        return self.to_tuple() < other.to_tuple()

    def __le__(self, other: object) -> bool:
        """Check if this version is less than or equal to another."""
        if not isinstance(other, ModelContractVersion):
            return NotImplemented
        return self.to_tuple() <= other.to_tuple()

    def __gt__(self, other: object) -> bool:
        """Check if this version is greater than another."""
        if not isinstance(other, ModelContractVersion):
            return NotImplemented
        return self.to_tuple() > other.to_tuple()

    def __ge__(self, other: object) -> bool:
        """Check if this version is greater than or equal to another."""
        if not isinstance(other, ModelContractVersion):
            return NotImplemented
        return self.to_tuple() >= other.to_tuple()

    def __hash__(self) -> int:
        """Return hash value for use in sets and as dict keys.

        Returns:
            int: Hash computed from (major, minor, patch) version tuple.
        """
        return hash(self.to_tuple())

    def bump_major(self) -> ModelContractVersion:
        """
        Bump major version, reset minor and patch to 0.

        Returns:
            New ModelContractVersion with incremented major

        Example:
            >>> ModelContractVersion(major=1, minor=2, patch=3).bump_major()
            ModelContractVersion(major=2, minor=0, patch=0)
        """
        return ModelContractVersion(major=self.major + 1, minor=0, patch=0)

    def bump_minor(self) -> ModelContractVersion:
        """
        Bump minor version, reset patch to 0.

        Returns:
            New ModelContractVersion with incremented minor

        Example:
            >>> ModelContractVersion(major=1, minor=2, patch=3).bump_minor()
            ModelContractVersion(major=1, minor=3, patch=0)
        """
        return ModelContractVersion(major=self.major, minor=self.minor + 1, patch=0)

    def bump_patch(self) -> ModelContractVersion:
        """
        Bump patch version.

        Returns:
            New ModelContractVersion with incremented patch

        Example:
            >>> ModelContractVersion(major=1, minor=2, patch=3).bump_patch()
            ModelContractVersion(major=1, minor=2, patch=4)
        """
        return ModelContractVersion(
            major=self.major, minor=self.minor, patch=self.patch + 1
        )

    def is_upgrade_from(self, other: ModelContractVersion) -> bool:
        """
        Check if this version is an upgrade from another version.

        An upgrade means this version is strictly greater than the other version.

        Args:
            other: Version to compare against

        Returns:
            True if this version is greater than other, False otherwise

        Example:
            >>> v2 = ModelContractVersion(major=2, minor=0, patch=0)
            >>> v1 = ModelContractVersion(major=1, minor=0, patch=0)
            >>> v2.is_upgrade_from(v1)
            True
        """
        return self > other

    def is_downgrade_from(self, other: ModelContractVersion) -> bool:
        """
        Check if this version is a downgrade from another version.

        A downgrade means this version is strictly less than the other version.

        Args:
            other: Version to compare against

        Returns:
            True if this version is less than other, False otherwise

        Example:
            >>> v1 = ModelContractVersion(major=1, minor=0, patch=0)
            >>> v2 = ModelContractVersion(major=2, minor=0, patch=0)
            >>> v1.is_downgrade_from(v2)
            True
        """
        return self < other

    def validate_progression(
        self, from_version: ModelContractVersion, allow_downgrade: bool = False
    ) -> None:
        """
        Validate version progression from another version.

        By default, downgrades are not allowed. This method raises an error
        if a downgrade is detected and allow_downgrade is False.

        Args:
            from_version: The version being upgraded from
            allow_downgrade: If True, allow downgrades without error

        Raises:
            ModelOnexError: If downgrade detected and allow_downgrade is False

        Example:
            >>> v2 = ModelContractVersion(major=2, minor=0, patch=0)
            >>> v1 = ModelContractVersion(major=1, minor=0, patch=0)
            >>> v2.validate_progression(from_version=v1)  # OK
            >>> v1.validate_progression(from_version=v2)  # Raises ModelOnexError
        """
        if self.is_downgrade_from(from_version) and not allow_downgrade:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=(
                    f"Version downgrade detected: {from_version} -> {self}. "
                    f"Downgrades are not allowed without explicit allow_downgrade=True. "
                    f"See CONTRACT_STABILITY_SPEC.md for versioning rules."
                ),
            )
