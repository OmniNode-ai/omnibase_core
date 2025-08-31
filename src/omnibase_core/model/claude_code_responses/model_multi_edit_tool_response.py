# Generated from contract: tool_claude_code_response_models v1.0.0

from pydantic import BaseModel, Field


class ModelEditOperation(BaseModel):
    """Single edit operation in MultiEdit."""

    operation_id: int = Field(
        ...,
        description="Sequence number of edit operation",
        ge=1,
    )
    old_string: str = Field(..., description="Text that was replaced")
    new_string: str = Field(..., description="Replacement text")
    replace_all: bool = Field(
        default=False,
        description="Whether all occurrences were replaced",
    )
    replacements_made: int = Field(
        ...,
        description="Number of replacements for this operation",
        ge=0,
    )
    lines_affected: list[int] = Field(
        ...,
        description="Line numbers affected by this operation",
    )
    success: bool = Field(..., description="Whether this operation succeeded")
    execution_order: int = Field(
        ...,
        description="Order in which operation was executed",
        ge=1,
    )
    error_message: str | None = Field(
        None,
        description="Error message if operation failed",
    )


class ModelMultiEditToolResponse(BaseModel):
    """Structured response from MultiEdit tool execution."""

    file_path: str = Field(..., description="Path to the file that was edited")
    edits_applied: list[ModelEditOperation] = Field(
        ...,
        description="Details of each edit operation",
    )
    total_edits: int = Field(
        ...,
        description="Total number of edit operations performed",
        ge=0,
    )
    successful_edits: int = Field(
        ...,
        description="Number of successful edit operations",
        ge=0,
    )
    failed_edits: int = Field(..., description="Number of failed edit operations", ge=0)
    atomic_operation: bool = Field(
        default=True,
        description="Whether all edits were applied atomically",
    )
    file_size_before: int = Field(
        ...,
        description="File size before edits in bytes",
        ge=0,
    )
    file_size_after: int = Field(
        ...,
        description="File size after edits in bytes",
        ge=0,
    )
    backup_created: bool = Field(
        default=False,
        description="Whether backup was created before edits",
    )
    backup_path: str | None = Field(
        None,
        description="Path to backup file if created",
    )
    lines_affected: list[int] | None = Field(
        None,
        description="All line numbers that were modified",
    )
    rollback_available: bool = Field(
        default=False,
        description="Whether rollback is available",
    )
