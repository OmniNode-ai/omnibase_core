from pathlib import Path
from uuid import UUID

from pydantic import BaseModel

from omnibase_core.models.core.model_core_metadata import ModelMetadata
from omnibase_core.models.core.model_regeneration_target import ModelRegenerationTarget
from omnibase_core.models.core.model_rendered_template import ModelRenderedTemplate
from omnibase_core.models.primitives.model_semver import ModelSemVer

__all__ = ["ModelRegenerationTarget", "ModelRenderedTemplate", "ModelTemplateContext"]


class ModelTemplateContext(BaseModel):
    """
    Canonical context model for template rendering in node_manager.
    Add fields as needed for your node generation and template logic.
    """

    node_name: str
    node_class: str
    node_id: UUID
    node_id_upper: UUID
    author: str
    year: int
    version: ModelSemVer
    description: str | None = None
    metadata: ModelMetadata | None = None
    version_string: ModelSemVer | None = None
    bundle_hash: str | None = None
    last_modified: str | None = None
    deployment_timestamp: str | None = None
    contract_hash: str | None = None
    contract_version: ModelSemVer | None = None
    node_version: ModelSemVer | None = None
    input_fields: str | None = None
    output_fields: str | None = None
    uuid: str | None = None
    output_directory: Path | None = None
