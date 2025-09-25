# Generated from contract: tool_claude_code_response_models v1.0.0
from pydantic import BaseModel, Field

from omnibase_core.enums.enum_output_mode import EnumOutputMode


class ModelGrepMatch(BaseModel):
    """Individual grep search match."""

    file_path: str = Field(..., description="Path to file containing match")
    line_number: int = Field(..., description="Line number of match", ge=1)
    matched_text: str = Field(..., description="The actual matched text")
    line_content: str = Field(..., description="Full line content containing match")
    column_number: int | None = Field(
        None,
        description="Column number of match start",
        ge=1,
    )
    context_before: list[str] | None = Field(
        None,
        description="Lines before match for context",
    )
    context_after: list[str] | None = Field(
        None,
        description="Lines after match for context",
    )


class ModelGrepToolResponse(BaseModel):
    """Structured response from Grep tool execution."""

    pattern: str = Field(..., description="Search pattern that was used")
    matches_found: int = Field(..., description="Total number of matches found", ge=0)
    files_searched: int = Field(..., description="Number of files searched", ge=0)
    files_with_matches: list[str] = Field(
        ...,
        description="Paths to files containing matches",
    )
    search_results: list[ModelGrepMatch] = Field(
        ...,
        description="Detailed search results",
    )
    case_sensitive: bool = Field(
        default=True,
        description="Whether search was case sensitive",
    )
    regex_used: bool = Field(
        default=True,
        description="Whether pattern was treated as regex",
    )
    output_mode: EnumOutputMode = Field(
        default=EnumOutputMode.FILES_WITH_MATCHES,
        description="Output mode used for search",
    )
    search_path: str | None = Field(
        None,
        description="Root path where search was performed",
    )
    glob_pattern: str | None = Field(
        None,
        description="File glob pattern used to filter files",
    )
    execution_time_ms: int | None = Field(
        None,
        description="Search execution time in milliseconds",
        ge=0,
    )
