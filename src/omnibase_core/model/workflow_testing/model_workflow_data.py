"""Model for workflow test data structures."""

from pydantic import BaseModel, Field


class ModelWorkflowTestData(BaseModel):
    """Strongly-typed model for workflow test data."""

    workflow_id: str = Field(description="Unique workflow identifier")
    workflow_type: str = Field(description="Type of workflow being tested")
    input_data: dict[str, str | int | float | bool] = Field(
        default_factory=dict,
        description="Input data for the workflow",
    )
    expected_outputs: list[str] | None = Field(
        default=None,
        description="Expected output patterns or values",
    )
    test_parameters: dict[str, str | int | float | bool] = Field(
        default_factory=dict,
        description="Test-specific parameters",
    )


class ModelDocumentWorkflowData(BaseModel):
    """Strongly-typed model for document workflow test data."""

    document_id: str = Field(description="Document identifier")
    document_type: str = Field(description="Type of document")
    content: str = Field(description="Document content")
    regeneration_params: dict[str, str | int | float | bool] = Field(
        default_factory=dict,
        description="Parameters for document regeneration",
    )
    quality_requirements: dict[str, float] | None = Field(
        default=None,
        description="Quality thresholds for the regenerated document",
    )


class ModelLLMInferenceData(BaseModel):
    """Strongly-typed model for LLM inference test data."""

    prompt: str = Field(description="Input prompt for the LLM")
    model_id: str = Field(description="LLM model identifier")
    temperature: float | None = Field(default=0.7, description="Model temperature")
    max_tokens: int | None = Field(
        default=1000,
        description="Maximum tokens to generate",
    )
    system_prompt: str | None = Field(default=None, description="System prompt")
    expected_patterns: list[str] | None = Field(
        default=None,
        description="Expected patterns in the response",
    )
    metadata: dict[str, str | int | float | bool] = Field(
        default_factory=dict,
        description="Additional metadata for the inference",
    )
