"""
FileFilter model.
"""

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums import EnumIgnorePatternSource, EnumTraversalMode


class ModelFileFilter(BaseModel):
    """
    Configuration model for filtering files during directory traversal.

    This model defines all parameters needed for file filtering operations,
    including patterns, traversal mode, and ignore sources.
    """

    traversal_mode: EnumTraversalMode = Field(
        default=EnumTraversalMode.RECURSIVE,
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
        default=None,
        description="Path to ignore file (e.g., .onexignore)",
    )
    ignore_pattern_sources: list[EnumIgnorePatternSource] = Field(
        default_factory=lambda: [
            EnumIgnorePatternSource.FILE,
            EnumIgnorePatternSource.DEFAULT,
        ],
        description="Sources to look for ignore patterns",
    )
    max_file_size: int = Field(
        default=5 * 1024 * 1024,
        description="Maximum file size in bytes to process",
    )
    max_files: int | None = Field(
        default=None,
        description="Maximum number of files to process",
    )
    follow_symlinks: bool = Field(
        default=False, description="Whether to follow symbolic links"
    )
    case_sensitive: bool = Field(
        default=True,
        description="Whether pattern matching is case sensitive",
    )
    model_config = ConfigDict(arbitrary_types_allowed=True)


# Compatibility alias
FileFilterModel = ModelFileFilter
