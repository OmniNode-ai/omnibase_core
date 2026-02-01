"""Pydantic model for mixin semantic versioning.

This module provides the ModelMixinVersion class for validating and working
with semantic version numbers in mixin metadata.
"""

from pydantic import BaseModel, Field, ValidationError

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError


class ModelMixinVersion(BaseModel):
    """Semantic version for mixin metadata.

    Attributes:
        major: Major version number (breaking changes)
        minor: Minor version number (new features)
        patch: Patch version number (bug fixes)
    """

    major: int = Field(..., ge=0, description="Major version number")
    minor: int = Field(..., ge=0, description="Minor version number")
    patch: int = Field(..., ge=0, description="Patch version number")

    def __str__(self) -> str:
        """Return semantic version string."""
        return f"{self.major}.{self.minor}.{self.patch}"

    @classmethod
    def from_string(cls, version_str: str) -> "ModelMixinVersion":
        """Parse version string like '1.0.0' into ModelMixinVersion.

        Args:
            version_str: Version string in format 'major.minor.patch'

        Returns:
            Parsed version model

        Raises:
            ModelOnexError: If version string is invalid
        """
        # Validate format outside try block - split() and len() don't raise ValueError/IndexError
        parts = version_str.split(".")
        if len(parts) != 3:
            raise ModelOnexError(
                message=f"Invalid version format: {version_str}. Expected 'major.minor.patch'",
                error_code=EnumCoreErrorCode.VALIDATION_FAILED,
            )

        # Only int() conversions can raise ValueError/IndexError, so isolate in try block
        try:
            return cls(major=int(parts[0]), minor=int(parts[1]), patch=int(parts[2]))
        except ValidationError as e:
            raise ModelOnexError(
                message=f"Invalid version string '{version_str}': Version numbers must be non-negative",
                error_code=EnumCoreErrorCode.VALIDATION_FAILED,
            ) from e
        except (IndexError, ValueError) as e:
            raise ModelOnexError(
                message=f"Invalid version string '{version_str}': {e}",
                error_code=EnumCoreErrorCode.VALIDATION_FAILED,
            ) from e
