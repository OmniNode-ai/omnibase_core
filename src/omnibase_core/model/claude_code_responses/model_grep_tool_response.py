# Generated from contract: tool_claude_code_response_models v1.0.0
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class ModelGrepMatch(BaseModel):
    """Individual grep search match."""

    file_path: str = Field(..., description="Path to file containing match")
    line_number: int = Field(..., description="Line number of match", ge=1)
    matched_text: str = Field(..., description="The actual matched text")
    line_content: str = Field(..., description="Full line content containing match")
    column_number: Optional[int] = Field(
        None, description="Column number of match start", ge=1
    )
    context_before: Optional[List[str]] = Field(
        None, description="Lines before match for context"
    )
    context_after: Optional[List[str]] = Field(
        None, description="Lines after match for context"
    )


class ModelGrepToolResponse(BaseModel):
    """Structured response from Grep tool execution."""

    pattern: str = Field(..., description="Search pattern that was used")
    matches_found: int = Field(..., description="Total number of matches found", ge=0)
    files_searched: int = Field(..., description="Number of files searched", ge=0)
    files_with_matches: List[str] = Field(
        ..., description="Paths to files containing matches"
    )
    search_results: List[ModelGrepMatch] = Field(
        ..., description="Detailed search results"
    )
    case_sensitive: bool = Field(
        default=True, description="Whether search was case sensitive"
    )
    regex_used: bool = Field(
        default=True, description="Whether pattern was treated as regex"
    )
    output_mode: Literal["content", "files_with_matches", "count"] = Field(
        default="files_with_matches", description="Output mode used for search"
    )
    search_path: Optional[str] = Field(
        None, description="Root path where search was performed"
    )
    glob_pattern: Optional[str] = Field(
        None, description="File glob pattern used to filter files"
    )
    execution_time_ms: Optional[int] = Field(
        None, description="Search execution time in milliseconds", ge=0
    )
