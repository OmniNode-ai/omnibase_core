from pydantic import BaseModel, Field

from omnibase_core.enums import EnumUriType
from omnibase_core.models.core.model_semver import ModelSemVer


class ModelOnexUri(BaseModel):
    """
    Canonical Pydantic model for ONEX URIs.
    See docs/nodes/node_contracts.md and docs/nodes/structural_conventions.md for spec.
    """

    type: EnumUriType = Field(
        default=...,
        description="ONEX URI type (tool, validator, agent, model, plugin, schema, node)",
    )
    namespace: str = Field(default=..., description="Namespace component of the URI")
    version_spec: ModelSemVer = Field(
        default=..., description="Version specifier (semver or constraint)"
    )
    original: str = Field(default=..., description="Original URI string as provided")


OnexUriModel = ModelOnexUri
