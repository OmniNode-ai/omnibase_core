"""
Tool Dependency Model.

Tool-specific dependency definition with version requirements.
"""

from pydantic import BaseModel, Field

from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.types.type_serializable_value import SerializedDict


class ModelToolDependency(BaseModel):
    """Tool-specific dependency definition."""

    name: str = Field(description="Dependency name")
    type: str = Field(description="Dependency type (service, protocol, library)")
    target: str = Field(description="Dependency target (URL, protocol name, etc.)")
    binding: str = Field(
        description="How dependency is bound (injection, lookup, etc.)",
    )
    optional: bool = Field(default=False, description="Whether dependency is optional")
    description: str = Field(description="Dependency purpose and usage")
    version_requirement: ModelSemVer | None = Field(
        default=None,
        description="Version requirement specification",
    )

    def is_service_dependency(self) -> bool:
        """Check if this is a service dependency."""
        return self.type.lower() == "service"

    def is_protocol_dependency(self) -> bool:
        """Check if this is a protocol dependency."""
        return self.type.lower() == "protocol"

    def is_library_dependency(self) -> bool:
        """Check if this is a library dependency."""
        return self.type.lower() == "library"

    def is_optional(self) -> bool:
        """Check if dependency is optional."""
        return self.optional

    def has_version_constraint(self) -> bool:
        """Check if dependency has version constraint."""
        return self.version_requirement is not None

    def get_binding_method(self) -> str:
        """Get binding method in lowercase."""
        return self.binding.lower()

    def get_summary(self) -> SerializedDict:
        """Get dependency summary."""
        return {
            "name": self.name,
            "type": self.type,
            "target": self.target,
            "binding": self.binding,
            "optional": self.optional,
            "has_version_constraint": self.has_version_constraint(),
            "version_requirement": (
                self.version_requirement.model_dump()
                if self.version_requirement
                else None
            ),
            "is_service": self.is_service_dependency(),
            "is_protocol": self.is_protocol_dependency(),
            "is_library": self.is_library_dependency(),
        }
