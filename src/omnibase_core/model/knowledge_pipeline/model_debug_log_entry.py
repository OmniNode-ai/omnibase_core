"""Debug log entry model for direct-to-database knowledge pipeline."""

from datetime import datetime
from typing import Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field


class ModelDebugLogEntry(BaseModel):
    """Direct-to-database debug log entry bypassing repository.

    This model represents debug information that gets written directly
    to PostgreSQL without creating repository files, enabling instant
    knowledge availability and real-time learning.
    """

    # Core identification
    log_id: Optional[UUID] = Field(
        None, description="Auto-generated UUID for the debug log entry"
    )
    session_id: str = Field(..., description="Claude Code session identifier")
    conversation_id: Optional[str] = Field(
        None, description="Conversation context identifier"
    )

    # Error classification
    error_type: str = Field(..., description="Type of error encountered")
    severity: str = Field(
        ..., description="Error severity level", regex="^(low|medium|high|critical)$"
    )
    error_category: str = Field(
        ..., description="Categorical classification of the error"
    )

    # Context and causality
    tool_name: Optional[str] = Field(
        None, description="Name of the tool that encountered the error"
    )
    operation_description: str = Field(
        ..., description="Description of the operation being performed"
    )
    full_context: Dict[str, Union[str, int, float, bool, List[str], Dict[str, str]]] = (
        Field(..., description="Complete context data")
    )
    causality_chain: List[str] = Field(
        default_factory=list, description="Chain of events leading to the error"
    )

    # Error details
    error_message: str = Field(..., description="Detailed error message")
    stack_trace: Optional[str] = Field(None, description="Stack trace if available")
    user_action: Optional[str] = Field(
        None, description="User action that triggered the error"
    )
    system_state: Optional[Dict[str, Union[str, int, float, bool]]] = Field(
        None, description="System state at time of error"
    )

    # Resolution tracking
    resolution_status: str = Field(
        default="unresolved",
        description="Current resolution status",
        regex="^(unresolved|investigating|resolved|ignored)$",
    )
    resolution_notes: Optional[str] = Field(
        None, description="Notes about error resolution"
    )
    resolved_by: Optional[str] = Field(
        None, description="Who or what resolved the error"
    )
    resolved_at: Optional[datetime] = Field(
        None, description="When the error was resolved"
    )

    # Metadata
    created_at: datetime = Field(
        default_factory=datetime.now, description="When the debug log was created"
    )
    source_file: Optional[str] = Field(
        None, description="Source file where error occurred"
    )
    line_number: Optional[int] = Field(
        None, description="Line number where error occurred"
    )
    git_commit_hash: Optional[str] = Field(
        None, description="Git commit hash at time of error"
    )
    working_directory: Optional[str] = Field(
        None, description="Working directory when error occurred"
    )

    # Intelligence integration
    quality_score: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Quality score for intelligence processing",
    )
    pattern_id: Optional[UUID] = Field(
        None, description="Reference to learning pattern if applicable"
    )
    intelligence_processed: bool = Field(
        default=False,
        description="Whether this entry has been processed by intelligence system",
    )

    class Config:
        """Pydantic configuration."""

        json_encoders = {datetime: lambda v: v.isoformat(), UUID: lambda v: str(v)}
        schema_extra = {
            "example": {
                "session_id": "claude_session_12345",
                "conversation_id": "conv_67890",
                "error_type": "ValidationError",
                "severity": "medium",
                "error_category": "input_validation",
                "tool_name": "Edit",
                "operation_description": "Attempting to edit file with invalid syntax",
                "full_context": {
                    "file_path": "/src/example.py",
                    "edit_operation": "replace",
                    "target_line": 42,
                },
                "causality_chain": [
                    "user_requested_edit",
                    "syntax_validation_failed",
                    "edit_rejected",
                ],
                "error_message": "Invalid Python syntax in replacement text",
                "user_action": "Edit file with malformed code",
                "system_state": {"memory_usage": 512, "active_tools": 3},
                "quality_score": 0.8,
            }
        }
