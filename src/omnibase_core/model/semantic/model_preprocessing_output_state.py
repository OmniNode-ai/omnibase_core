"""
Output state model for advanced text preprocessing.

Defines the output results and metadata from advanced text preprocessing
operations in the semantic discovery engine.
"""

from pydantic import ConfigDict, Field

from omnibase_core.model.core.model_onex_output_state import ModelOnexOutputState
from omnibase_core.model.semantic.model_document_metadata import ModelDocumentMetadata
from omnibase_core.model.semantic.model_preprocessing_statistics import (
    ModelPreprocessingStatistics,
)


class ModelPreprocessingOutputState(ModelOnexOutputState):
    """
    Output state for advanced text preprocessing operations.

    Contains processed documents, operation statistics,
    and metadata from preprocessing operations.
    """

    processed_documents: list[ModelDocumentMetadata] = Field(
        description="List of processed documents with chunks",
        default_factory=list,
    )

    processing_statistics: ModelPreprocessingStatistics = Field(
        description="Statistics about the preprocessing operation",
        default_factory=ModelPreprocessingStatistics,
    )

    quality_metrics: dict[str, float] = Field(
        description="Quality metrics for processed documents",
        default_factory=dict,
    )

    warnings: list[str] = Field(
        description="Non-fatal warnings from processing",
        default_factory=list,
    )

    processing_time_ms: int | None = Field(
        default=None,
        description="Total processing time in milliseconds",
    )

    documents_processed: int = Field(
        default=0,
        description="Number of documents successfully processed",
    )

    chunks_created: int = Field(default=0, description="Total number of chunks created")

    model_config = ConfigDict(
        use_enum_values=True,
        validate_assignment=True,
        extra="forbid",
    )
