"""
FileFilter model.
"""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ModelFileFilter(BaseModel):
    """
    Configuration model for filtering files during directory traversal.

    This model defines all parameters needed for file filtering operations,
    including patterns, traversal mode, and ignore sources.
    """

    traversal_mode: Literal["RECURSIVE", "FLAT", "SINGLE"] = Field(
        default="RECURSIVE",
        description="Mode for traversing directories",
    )
    include_patterns: list[str] = Field(
        default_factory=list,
        description="Glob patterns to include (e.g., ['**/*.yaml', '**/*.json'])",
    )
    exclude_patterns: list[str] = Field(
        default_factory=list,
        description="Glob patterns to exclude (e.g., ['**/.git/**'])",
    )
    ignore_file: Path | None = Field(
        None,
        description="Path to ignore file (e.g., .onexignore)",
    )
    ignore_pattern_sources: list[Literal["FILE", "DEFAULT", "ENVIRONMENT"]] = Field(
        default_factory=lambda: [
            "FILE",
            "DEFAULT",
        ],
        description="Sources to look for ignore patterns",
    )
    max_file_size: int = Field(
        5 * 1024 * 1024,
        description="Maximum file size in bytes to process",
    )
    max_files: int | None = Field(
        None,
        description="Maximum number of files to process",
    )
    follow_symlinks: bool = Field(False, description="Whether to follow symbolic links")
    case_sensitive: bool = Field(
        True,
        description="Whether pattern matching is case sensitive",
    )
    model_config = ConfigDict(arbitrary_types_allowed=True)


# Compatibility alias
FileFilterModel = ModelFileFilter
