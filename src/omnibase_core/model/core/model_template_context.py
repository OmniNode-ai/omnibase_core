from pathlib import Path
from typing import Optional

from pydantic import BaseModel

from omnibase_core.model.core.model_metadata import ModelMetadata
from omnibase_core.model.core.model_regeneration_target import \
    ModelRegenerationTarget
from omnibase_core.model.core.model_rendered_template import \
    ModelRenderedTemplate
from omnibase_core.model.core.model_semver import ModelSemVer

# Re-export for backward compatibility
__all__ = ["ModelTemplateContext", "ModelRenderedTemplate", "ModelRegenerationTarget"]


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
    description: Optional[str] = None
    metadata: Optional[ModelMetadata] = None
    # Additional fields for template tokenization
    version_string: Optional[str] = (
        None  # String version for template tokens like {VERSION}
    )
    bundle_hash: Optional[str] = None
    last_modified: Optional[str] = None
    deployment_timestamp: Optional[str] = None

    # Contract-derived fields for template token replacement
    contract_hash: Optional[str] = None
    contract_version: Optional[str] = None
    node_version: Optional[str] = None
    input_fields: Optional[str] = None
    output_fields: Optional[str] = None
    uuid: Optional[str] = None

    # Output directory handling for dynamic path generation
    output_directory: Optional[Path] = None
