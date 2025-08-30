"""Structure markers model with strong typing."""

from pydantic import BaseModel, ConfigDict, Field


class ModelCodeBlock(BaseModel):
    """Strongly typed code block model."""

    start_pos: int = Field(ge=0, description="Start position in text")
    end_pos: int = Field(ge=0, description="End position in text")
    language: str | None = Field(default=None, description="Programming language")
    content: str = Field(description="Code block content")

    model_config = ConfigDict(frozen=True, extra="forbid")


class ModelStructureMarkers(BaseModel):
    """Strongly typed structure markers model."""

    has_headers: bool = Field(description="Whether text contains headers")
    has_lists: bool = Field(description="Whether text contains lists")
    has_code_blocks: bool = Field(description="Whether text contains code blocks")
    has_tables: bool = Field(description="Whether text contains tables")

    header_count: int = Field(ge=0, description="Number of headers found")
    list_count: int = Field(ge=0, description="Number of lists found")
    code_block_count: int = Field(ge=0, description="Number of code blocks found")
    table_count: int = Field(ge=0, description="Number of tables found")

    avg_paragraph_length: float | None = Field(
        default=None,
        ge=0.0,
        description="Average paragraph length",
    )
    complexity_score: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Text complexity score",
    )

    model_config = ConfigDict(frozen=True, extra="forbid")
