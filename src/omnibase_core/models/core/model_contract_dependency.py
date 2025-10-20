"""
Model for contract dependency representation in ONEX Phase 0 pattern.

This model supports dependency injection configuration in contracts.

Author: ONEX Framework Team
"""

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.primitives.model_semver import ModelSemVer, parse_semver_from_string


class ModelContractDependency(BaseModel):
    """Model representing a single dependency in a contract."""

    model_config = ConfigDict(extra="ignore")

    name: str = Field(default=..., description="Dependency service name")
    type: str = Field(
        default=..., description="Dependency type (utility, protocol, service)"
    )
    version: ModelSemVer | None = Field(
        default=None, description="Dependency version (semver format)"
    )
    class_name: str | None = Field(
        default=None,
        alias="class",
        description="Class name for the dependency",
    )
    module: str | None = Field(
        default=None, description="Module path for the dependency"
    )
    description: str | None = Field(default=None, description="Dependency description")

    @field_validator("version", mode="before")
    @classmethod
    def parse_version_string(cls, v: object) -> ModelSemVer | None:
        """Convert string versions to ModelSemVer objects automatically.

        Args:
            v: Version value (string, dict, or ModelSemVer)

        Returns:
            ModelSemVer object or None

        Raises:
            ModelOnexError: If version string format is invalid
        """
        if v is None:
            return None
        if isinstance(v, str):
            return parse_semver_from_string(v)
        if isinstance(v, dict):
            # Handle dict format like {"major": 1, "minor": 0, "patch": 0}
            return ModelSemVer.model_validate(v)
        # Already a ModelSemVer instance
        return v  # type: ignore[return-value]
