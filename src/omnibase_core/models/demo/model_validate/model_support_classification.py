"""Support classification output model for model-validate demo scenario."""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums import EnumSentiment, EnumSupportCategory


class ModelSupportClassificationResult(BaseModel):
    """Output model representing the classification result from an LLM.

    This frozen model captures the LLM's analysis of a support ticket,
    including category classification, sentiment, and suggested response.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    ticket_id: str = Field(  # string-id-ok: external ticketing system identifier
        description="ID of the classified ticket (must match input)"
    )
    category: EnumSupportCategory = Field(
        description="Classified support category for routing"
    )
    confidence: float = Field(
        ge=0.0, le=1.0, description="Classification confidence score (0.0 to 1.0)"
    )
    sentiment: EnumSentiment = Field(
        description="Detected customer sentiment (positive, neutral, negative)"
    )
    summary: str = Field(description="Brief summary of the ticket issue")
    suggested_reply: str = Field(description="LLM-generated suggested response")
    latency_ms: int = Field(ge=0, description="LLM response latency in milliseconds")
    model_id: str = Field(  # string-id-ok: LLM model identifier string
        description="Identifier of the model that generated this"
    )

    # Optional fields for detailed analysis
    reason_codes: list[str] | None = Field(
        default=None, description="Codes explaining the classification decision"
    )
    invariant_tags: list[str] | None = Field(
        default=None, description="Tags indicating which invariants apply"
    )


__all__ = ["ModelSupportClassificationResult"]
