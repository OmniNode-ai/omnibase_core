from typing import Dict, Optional

from pydantic import BaseModel, Field

from omnibase.model.core.model_metadata import ModelMetadata


class ModelGeneratedModels(BaseModel):
    """
    Canonical output model for contract-to-model generation tools.
    Maps model names to generated code strings.
    Optionally includes canonical metadata.
    """

    models: Dict[str, str] = Field(
        default_factory=dict,
        description="Mapping of model names to generated code strings.",
    )
    metadata: Optional[ModelMetadata] = Field(
        default=None,
        description="Optional canonical metadata for the generated models.",
    )
