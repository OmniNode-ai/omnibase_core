# Generated from contract: tool_claude_code_response_models v1.0.0
from datetime import datetime

from pydantic import BaseModel, Field


class ModelWebSearchResult(BaseModel):
    """Individual web search result."""

    title: str = Field(..., description="Title of the search result")
    url: str = Field(..., description="URL of the search result")
    snippet: str = Field(..., description="Text snippet from the result")
    rank: int = Field(..., description="Ranking position in results", ge=1)
    display_url: str | None = Field(None, description="Display URL shown in results")
    relevance_score: float | None = Field(
        None,
        description="Relevance score if available",
        ge=0,
        le=1,
    )
    published_date: datetime | None = Field(
        None,
        description="Publication date if available",
    )
    source_domain: str | None = Field(
        None,
        description="Domain of the result source",
    )


class ModelWebSearchToolResponse(BaseModel):
    """Structured response from WebSearch tool execution."""

    query: str = Field(..., description="Search query that was executed")
    results: list[ModelWebSearchResult] = Field(
        ...,
        description="Search results returned",
    )
    total_results: int = Field(..., description="Total number of results found", ge=0)
    search_engine: str = Field(..., description="Search engine used")
    language: str = Field(default="en", description="Language used for search")
    search_region: str | None = Field(
        None,
        description="Geographic region for search",
    )
    safe_search: bool = Field(
        default=True,
        description="Whether safe search was enabled",
    )
    execution_time_ms: int | None = Field(
        None,
        description="Search execution time in milliseconds",
        ge=0,
    )
    cached_result: bool = Field(
        default=False,
        description="Whether result was served from cache",
    )
