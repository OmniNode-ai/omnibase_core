from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelMetadata(BaseModel):
    """Basic metadata model for file information."""

    meta_type: str = Field(default=..., description="Type of metadata block")
    metadata_version: ModelSemVer = Field(
        default=..., description="Version of the metadata schema"
    )
    schema_version: ModelSemVer = Field(
        default=..., description="Version of the content schema"
    )
    uuid: str = Field(default=..., description="Unique identifier for this file")
    name: str = Field(default=..., description="File name")
    version: ModelSemVer = Field(default=..., description="File version")
    author: str = Field(default=..., description="Author of the file")
    created_at: datetime = Field(default=..., description="Creation timestamp")
    last_modified_at: datetime = Field(
        default=..., description="Last modification timestamp"
    )
    description: str | None = Field(default=None, description="Description of the file")
    state_contract: str | None = Field(
        default=None, description="State contract reference"
    )
    lifecycle: str | None = Field(default=None, description="EnumLifecycle state")
    hash: str = Field(default=..., description="Canonical content hash")
    entrypoint: str | None = Field(default=None, description="Entrypoint information")
    namespace: str | None = Field(default=None, description="Namespace for the file")
