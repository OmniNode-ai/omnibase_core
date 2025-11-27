from pydantic import BaseModel, Field

from omnibase_core.models.core.model_core_metadata import ModelMetadata


class ModelGeneratedModels(BaseModel):
    """
    Canonical output model for contract-to-model generation tools.
    Maps model names to generated code strings.
    Optionally includes canonical metadata.
    """

    models: dict[str, str] = Field(
        default_factory=dict,
        description="Mapping of model names to generated code strings.",
    )
    metadata: ModelMetadata | None = Field(
        default=None,
        description="Optional canonical metadata for the generated models.",
    )
