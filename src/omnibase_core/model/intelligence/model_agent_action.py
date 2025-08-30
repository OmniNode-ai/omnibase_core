"""
Pydantic model for agent actions in the direct knowledge pipeline.

This model represents audit trail of all agent actions for learning and analysis
that are written directly to the PostgreSQL database bypassing repository.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class ModelAgentActionRecord(BaseModel):
    """
    Agent action record for audit trail and learning.

    Maps to debug_intelligence.agent_actions table in PostgreSQL.
    Used for direct-to-database writes bypassing repository.
    """

    action_id: str = Field(..., description="Unique identifier for this action")

    agent_id: str = Field(..., description="Agent that performed this action")

    # Action details
    action_type: str = Field(
        ...,
        description="Type of action: file_read, file_write, tool_call, decision, analysis",
    )

    action_description: str = Field(
        ...,
        description="Detailed description of the action performed",
    )

    # Context
    work_session_id: str | None = Field(
        default=None,
        description="ID of the work session this action belongs to",
    )

    correlation_id: str | None = Field(
        default=None,
        description="Links related actions together",
    )

    parent_action_id: str | None = Field(
        default=None,
        description="Parent action ID for action hierarchies",
    )

    # Input and output
    input_data: dict = Field(
        default_factory=dict,
        description="Input data for this action as JSON",
    )

    output_data: dict = Field(
        default_factory=dict,
        description="Output data from this action as JSON",
    )

    # Outcome tracking
    success: bool = Field(..., description="Whether the action completed successfully")

    error_message: str | None = Field(
        default=None,
        description="Error message if action failed",
    )

    confidence_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Agent confidence in this action from 0.0-1.0",
    )

    # Performance metrics
    duration_ms: int = Field(default=0, description="Action duration in milliseconds")

    tokens_used: int = Field(
        default=0,
        description="Number of tokens consumed by this action",
    )

    cost_estimate: float = Field(
        default=0.0,
        description="Estimated cost of this action",
    )

    # Learning data
    reasoning: dict = Field(
        default_factory=dict,
        description="Agent's reasoning process as JSON",
    )

    alternatives_considered: list[dict] = Field(
        default_factory=list,
        description="Other options considered as JSON array",
    )

    learned_patterns: list[dict] = Field(
        default_factory=list,
        description="Patterns identified during action as JSON array",
    )

    # File and tool context
    affected_files: list[str] = Field(
        default_factory=list,
        description="List of files affected by this action",
    )

    tools_involved: list[str] = Field(
        default_factory=list,
        description="List of tools used in this action",
    )

    # Metadata and extensibility
    metadata: dict = Field(
        default_factory=dict,
        description="Additional metadata as JSON",
    )

    # Timestamps
    timestamp: datetime = Field(..., description="When this action was performed")

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this record was created",
    )

    class Config:
        """Pydantic configuration for the agent action model."""

        # Enable JSON encoding for datetime objects
        json_encoders = {datetime: lambda v: v.isoformat()}

        # Allow extra fields for future extensibility
        extra = "forbid"

        # Validate assignment to catch errors early
        validate_assignment = True

        # Use enum values for string enums
        use_enum_values = True


class ModelActionContext(BaseModel):
    """
    Context information for agent actions.

    Used to provide rich context when creating agent action records.
    """

    session_id: str = Field(..., description="Current work session ID")

    task_description: str = Field(..., description="Description of the current task")

    current_branch: str | None = Field(
        default=None,
        description="Current git branch",
    )

    working_directory: str = Field(..., description="Current working directory")

    environment: str = Field(
        default="development",
        description="Environment where action is performed",
    )

    user_intent: str | None = Field(
        default=None,
        description="User's original intent or request",
    )

    previous_actions: list[str] = Field(
        default_factory=list,
        description="List of previous action IDs in this context",
    )

    class Config:
        """Pydantic configuration for the action context model."""

        extra = "forbid"
        validate_assignment = True
