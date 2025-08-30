from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from omnibase_core.model.core.model_semver import ModelSemVer


class ModelMetadata(BaseModel):
    """
    Canonical metadata model for ONEX nodes, targets, and artifacts.
    Reuse this model for all metadata fields across the codebase.
    """

    name: str = Field(..., description="Canonical name of the node or artifact.")
    description: str | None = Field(
        default=None,
        description="Description of the entity.",
    )
    version: ModelSemVer | None = Field(
        default=None,
        description="Semantic version, if applicable.",
    )
    author: str | None = Field(
        default=None,
        description="Author or owner of the entity.",
    )
    created_at: datetime | None = Field(
        default=None,
        description="Creation timestamp, if available.",
    )

    @model_validator(mode="before")
    def coerce_version(self, values):
        version = values.get("version")
        if version is not None and not isinstance(version, ModelSemVer):
            values["version"] = ModelSemVer.parse(version)
        return values
