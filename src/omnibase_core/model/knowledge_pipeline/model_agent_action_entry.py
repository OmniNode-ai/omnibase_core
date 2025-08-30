"""Agent action entry model for direct-to-database knowledge pipeline."""

from datetime import datetime
from typing import Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field


class ModelAgentActionEntry(BaseModel):
    """Direct-to-database agent action entry bypassing repository.

    This model provides a comprehensive audit trail of agent actions that gets
    written directly to PostgreSQL without creating repository files, enabling
    instant knowledge availability and real-time learning for agent behavior analysis.
    """

    # Core identification
    action_id: Optional[UUID] = Field(
        None, description="Auto-generated UUID for the agent action entry"
    )
    session_id: str = Field(..., description="Claude Code session identifier")
    conversation_id: Optional[str] = Field(
        None, description="Conversation context identifier"
    )

    # Agent identification
    agent_name: str = Field(..., description="Name of the agent performing the action")
    agent_version: Optional[str] = Field(None, description="Version of the agent")
    action_type: str = Field(..., description="Type of action being performed")

    # Action details
    action_description: str = Field(
        ..., description="Detailed description of the action"
    )
    input_parameters: Optional[
        Dict[str, Union[str, int, float, bool, List[str], Dict[str, str]]]
    ] = Field(None, description="Input parameters for the action")
    output_result: Optional[
        Dict[str, Union[str, int, float, bool, List[str], Dict[str, str]]]
    ] = Field(None, description="Output result of the action")

    # Execution context
    tool_name: Optional[str] = Field(
        None, description="Name of the tool used in the action"
    )
    file_path: Optional[str] = Field(
        None, description="File path affected by the action"
    )
    working_directory: Optional[str] = Field(
        None, description="Working directory when action was performed"
    )
    git_context: Optional[Dict[str, Union[str, bool, List[str]]]] = Field(
        None, description="Git context information"
    )

    # Performance metrics
    execution_time_ms: Optional[int] = Field(
        None, ge=0, description="Execution time in milliseconds"
    )
    memory_usage_mb: Optional[float] = Field(
        None, ge=0.0, description="Memory usage in megabytes"
    )
    success_status: bool = Field(
        ..., description="Whether the action completed successfully"
    )
    error_details: Optional[str] = Field(
        None, description="Error details if action failed"
    )

    # Causality and relationships
    parent_action_id: Optional[UUID] = Field(
        None, description="UUID of parent action if this is a sub-action"
    )
    related_actions: List[UUID] = Field(
        default_factory=list, description="UUIDs of related actions"
    )
    causality_chain: List[str] = Field(
        default_factory=list, description="Chain of events leading to this action"
    )

    # Learning integration
    learning_value: Optional[str] = Field(
        None,
        description="Learning value of this action",
        regex="^(none|low|medium|high|critical)$",
    )
    pattern_significance: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Significance for pattern recognition"
    )

    # Metadata
    created_at: datetime = Field(
        default_factory=datetime.now, description="When the action was recorded"
    )
    user_interaction: bool = Field(
        default=False, description="Whether this action involved user interaction"
    )
    automation_level: Optional[str] = Field(
        None,
        description="Level of automation",
        regex="^(manual|assisted|automated|autonomous)$",
    )

    # Intelligence processing
    intelligence_processed: bool = Field(
        default=False,
        description="Whether this entry has been processed by intelligence system",
    )
    quality_score: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Quality score for intelligence processing",
    )

    class Config:
        """Pydantic configuration."""

        json_encoders = {datetime: lambda v: v.isoformat(), UUID: lambda v: str(v)}
        schema_extra = {
            "example": {
                "session_id": "claude_session_action_001",
                "conversation_id": "conv_action_456",
                "agent_name": "claude-code-agent",
                "agent_version": "v1.2.0",
                "action_type": "file_modification",
                "action_description": "Modified Python file to fix import statements",
                "input_parameters": {
                    "file_path": "/src/main.py",
                    "operation": "edit",
                    "target_lines": [1, 2, 3],
                    "replacement_text": "from typing import Dict, List",
                },
                "output_result": {
                    "success": True,
                    "lines_modified": 3,
                    "backup_created": True,
                    "validation_passed": True,
                },
                "tool_name": "Edit",
                "file_path": "/src/main.py",
                "working_directory": "/Volumes/PRO-G40/Code/project",
                "git_context": {
                    "branch": "feature/imports-fix",
                    "commit_hash": "abc123def456",
                    "has_uncommitted_changes": True,
                    "modified_files": ["/src/main.py"],
                },
                "execution_time_ms": 150,
                "memory_usage_mb": 2.5,
                "success_status": True,
                "causality_chain": [
                    "user_requested_import_fix",
                    "analyzed_import_statements",
                    "identified_missing_imports",
                    "applied_edit_operation",
                ],
                "learning_value": "medium",
                "pattern_significance": 0.7,
                "user_interaction": True,
                "automation_level": "assisted",
                "intelligence_processed": False,
                "quality_score": 0.8,
            }
        }
