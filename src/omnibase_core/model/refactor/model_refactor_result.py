"""
Refactor Result Model

Structured model for refactoring operation results.
"""

from enum import Enum
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field


class EnumRefactorStatus(str, Enum):
    """Status of refactoring operations."""

    success = "success"
    warning = "warning"
    error = "error"
    partial = "partial"
    cancelled = "cancelled"


class ModelRefactorChange(BaseModel):
    """Individual refactoring change."""

    file_path: Path = Field(..., description="Path to modified file")
    change_type: str = Field(..., description="Type of change made")
    old_content: Optional[str] = Field(None, description="Original content")
    new_content: Optional[str] = Field(None, description="Modified content")
    line_range: Optional[List[int]] = Field(
        None, description="Line range affected [start, end]"
    )


class ModelRefactorResult(BaseModel):
    """
    Structured refactor result model.

    Replaces Dict[str, Any] usage with proper typing for
    refactoring operation results.
    """

    # Core result information
    status: EnumRefactorStatus = Field(..., description="Overall refactoring status")
    success: bool = Field(..., description="Whether refactoring was successful")

    # Change details
    files_modified: int = Field(default=0, description="Number of files modified")
    changes_made: List[ModelRefactorChange] = Field(
        default_factory=list, description="List of changes made"
    )
    backup_files: List[Path] = Field(
        default_factory=list, description="Backup files created"
    )

    # Issues and validation
    syntax_errors: List[str] = Field(
        default_factory=list, description="Syntax errors found"
    )
    warnings: List[str] = Field(default_factory=list, description="Warnings generated")

    # Metadata
    duration_ms: Optional[int] = Field(
        None, description="Refactoring duration in milliseconds"
    )
    summary: str = Field(..., description="Human-readable refactoring summary")

    @classmethod
    def create_success(
        cls, summary: str = "Refactoring completed successfully"
    ) -> "ModelRefactorResult":
        """Factory method for successful refactor results."""
        return cls(status=EnumRefactorStatus.success, success=True, summary=summary)

    @classmethod
    def create_failure(
        cls, errors: List[str], summary: Optional[str] = None
    ) -> "ModelRefactorResult":
        """Factory method for failed refactor results."""
        if summary is None:
            summary = f"Refactoring failed with {len(errors)} errors"

        return cls(
            status=EnumRefactorStatus.error,
            success=False,
            syntax_errors=errors,
            summary=summary,
        )
