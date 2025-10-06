from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ModelMetadata(BaseModel):
    """Basic metadata model for file information."""

    meta_type: str = Field(..., description="Type of metadata block")
    metadata_version: str = Field(..., description="Version of the metadata schema")
    schema_version: str = Field(..., description="Version of the content schema")
    uuid: str = Field(..., description="Unique identifier for this file")
    name: str = Field(..., description="File name")
    version: str = Field(..., description="File version")
    author: str = Field(..., description="Author of the file")
    created_at: datetime = Field(..., description="Creation timestamp")
    last_modified_at: datetime = Field(..., description="Last modification timestamp")
    description: str | None = Field(default=None, description="Description of the file")
    state_contract: str | None = Field(
        default=None, description="State contract reference"
    )
    lifecycle: str | None = Field(default=None, description="EnumLifecycle state")
    hash: str = Field(..., description="Canonical content hash")
    entrypoint: str | None = Field(default=None, description="Entrypoint information")
    namespace: str | None = Field(default=None, description="Namespace for the file")
