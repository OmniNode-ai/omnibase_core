"""
Input state model for advanced text preprocessing.

Defines the input parameters and configuration for advanced text preprocessing
operations in the semantic discovery engine.
"""

from pydantic import ConfigDict, Field

from omnibase_core.models.core.model_onex_base_state import ModelOnexInputState
from omnibase_core.models.semantic.model_input_document import ModelInputDocument
from omnibase_core.models.semantic.model_preprocessing_config import (
    ModelPreprocessingConfig,
)


class ModelPreprocessingInputState(ModelOnexInputState):
    """
    Input state for advanced text preprocessing operations.

    Contains documents to process, preprocessing configuration,
    and operation metadata required for advanced text preprocessing.
    """

    documents: list[ModelInputDocument] = Field(
        ...,
        description="List of documents to process",
        min_length=1,
    )

    config: ModelPreprocessingConfig = Field(
        description="Preprocessing configuration parameters",
        default_factory=ModelPreprocessingConfig,
    )

    preserve_metadata: bool | None = Field(
        default=None,
        description="Override config setting for metadata preservation",
    )

    operation_mode: str = Field(
        default="standard",
        description="Processing mode: standard, fast, thorough",
    )

    model_config = ConfigDict(
        use_enum_values=True,
        validate_assignment=True,
        extra="forbid",
    )
