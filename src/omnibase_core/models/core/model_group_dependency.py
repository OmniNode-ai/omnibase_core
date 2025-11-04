from pydantic import BaseModel, Field

from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelGroupDependency(BaseModel):
    """External dependency required by the tool group."""

    name: str = Field(description="Dependency name")
    type: str = Field(description="Dependency type (service, library, protocol)")
    version_requirement: ModelSemVer | None = Field(
        default=None, description="Version requirement specification"
    )
    optional: bool = Field(default=False, description="Whether dependency is optional")
    description: str = Field(description="Dependency purpose and usage")
