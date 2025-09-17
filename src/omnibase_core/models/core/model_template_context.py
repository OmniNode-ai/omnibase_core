from pathlib import Path

from pydantic import BaseModel

from omnibase_core.models.core.model_metadata import ModelMetadata
from omnibase_core.models.core.model_regeneration_target import ModelRegenerationTarget
from omnibase_core.models.core.model_rendered_template import ModelRenderedTemplate
from omnibase_core.models.core.model_semver import ModelSemVer

# Re-export for current standards
__all__ = ["ModelRegenerationTarget", "ModelRenderedTemplate", "ModelTemplateContext"]


class ModelTemplateContext(BaseModel):
    """
    Canonical context model for template rendering in node_manager.
    Add fields as needed for your node generation and template logic.
    """

    node_name: str
    node_class: str  # Main node class name
    node_id: str  # Node ID string (lowercase, underscores)
    node_id_upper: str  # Node ID in uppercase (for constants)
    author: str
    year: int  # Copyright year
    version: ModelSemVer  # Required version field
    description: str | None = None
    metadata: ModelMetadata | None = None
    # Additional fields for template tokenization
    version_string: str | None = (
        None  # String version for template tokens like {VERSION}
    )
    bundle_hash: str | None = None
    last_modified: str | None = None
    deployment_timestamp: str | None = None

    # Contract-derived fields for template token replacement
    contract_hash: str | None = None
    contract_version: str | None = None
    node_version: str | None = None
    input_fields: str | None = None
    output_fields: str | None = None
    uuid: str | None = None

    # Output directory handling for dynamic path generation
    output_directory: Path | None = None
