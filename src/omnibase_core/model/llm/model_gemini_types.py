"""
Gemini-specific type models for ONEX standards compliance.

Replaces Dict[str, Any] patterns with proper typed models.
"""

from pydantic import BaseModel, Field


class ModelGeminiGenerationConfig(BaseModel):
    """Generation configuration for Gemini API requests."""

    temperature: float | None = Field(
        default=None,
        ge=0.0,
        le=2.0,
        description="Controls randomness in generation",
    )

    top_p: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Nucleus sampling threshold",
    )

    top_k: int | None = Field(
        default=None,
        ge=1,
        description="Top-k sampling parameter",
    )

    candidate_count: int | None = Field(
        default=None,
        ge=1,
        le=8,
        description="Number of response candidates to generate",
    )

    max_output_tokens: int | None = Field(
        default=None,
        ge=1,
        description="Maximum number of tokens in response",
    )

    stop_sequences: list[str] | None = Field(
        default=None,
        description="Sequences that stop generation",
    )


class ModelGeminiPart(BaseModel):
    """A part of a Gemini message (text, image, etc)."""

    text: str | None = Field(default=None, description="Text content of the part")

    # Future: Add support for other part types (images, etc)


class ModelGeminiContent(BaseModel):
    """Content structure for Gemini messages."""

    role: str = Field(description="Role of the message sender (user or model)")

    parts: list[ModelGeminiPart] = Field(description="Parts that make up this content")


class ModelGeminiRequest(BaseModel):
    """Request structure for Gemini API."""

    contents: list[ModelGeminiContent] = Field(description="Conversation contents")

    generation_config: ModelGeminiGenerationConfig | None = Field(
        default=None,
        description="Generation configuration",
    )

    safety_settings: list[dict[str, str]] | None = Field(
        default=None,
        description="Safety settings for content filtering",
    )

    system_instruction: ModelGeminiContent | None = Field(
        default=None,
        description="System instruction content",
    )


class ModelGeminiCandidate(BaseModel):
    """Response candidate from Gemini API."""

    content: ModelGeminiContent = Field(description="Generated content")

    finish_reason: str | None = Field(
        default=None,
        description="Reason for stopping generation",
    )

    index: int | None = Field(default=0, description="Candidate index")

    safety_ratings: list[dict[str, str | float]] | None = Field(
        default=None,
        description="Safety ratings for the content",
    )


class ModelGeminiUsageMetadata(BaseModel):
    """Usage metadata from Gemini response."""

    prompt_token_count: int = Field(description="Number of tokens in the prompt")

    candidates_token_count: int = Field(
        description="Number of tokens in all candidates",
    )

    total_token_count: int = Field(description="Total token count")


class ModelGeminiResponse(BaseModel):
    """Response structure from Gemini API."""

    candidates: list[ModelGeminiCandidate] = Field(description="Response candidates")

    usage_metadata: ModelGeminiUsageMetadata | None = Field(
        default=None,
        description="Token usage information",
    )

    prompt_feedback: dict[str, str | list[dict[str, str]]] | None = Field(
        default=None,
        description="Feedback about the prompt",
    )
