# Generated from contract: tool_claude_code_response_models v1.0.0
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class ModelGlobToolResponse(BaseModel):
    """Structured response from Glob tool execution."""

    pattern: str = Field(..., description="Glob pattern that was used")
    matches_found: List[str] = Field(..., description="File paths matching the pattern")
    total_matches: int = Field(..., description="Total number of matches found", ge=0)
    pattern_type: Literal["glob", "regex", "literal"] = Field(
        default="glob", description="Type of pattern matching used"
    )
    recursive: bool = Field(default=True, description="Whether search was recursive")
    search_path: Optional[str] = Field(
        None, description="Root path where search was performed"
    )
    hidden_files_included: bool = Field(
        default=False, description="Whether hidden files were included"
    )
    sorted_results: bool = Field(
        default=True, description="Whether results were sorted"
    )
    execution_time_ms: Optional[int] = Field(
        None, description="Pattern matching execution time", ge=0
    )
