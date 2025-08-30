"""
Agent Action Model for tracking individual agent actions.

This model represents a single agent action for audit trail,
learning, and performance analysis with strong typing.
"""

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.model.ai_workflows.model_ai_execution_metrics import \
    ModelMetricValue
from omnibase_core.model.core.model_tool_type import ModelToolType


class EnumActionType(str, Enum):
    """Types of agent actions."""

    FILE_READ = "file_read"
    FILE_WRITE = "file_write"
    FILE_EDIT = "file_edit"
    TOOL_CALL = "tool_call"
    DECISION = "decision"
    ANALYSIS = "analysis"
    VALIDATION = "validation"
    COMMIT = "commit"
    SEARCH = "search"
    PLANNING = "planning"


class EnumActionOutcome(str, Enum):
    """Outcomes of agent actions."""

    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL_SUCCESS = "partial_success"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class ModelActionInput(BaseModel):
    """Strongly typed input data for an agent action."""

    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True)

    parameters: Dict[str, Any] = Field(description="Input parameters for the action")
    context: Dict[str, Any] = Field(description="Contextual information")
    target_files: List[Path] = Field(
        default_factory=list, description="Files targeted by this action"
    )
    tool_involved: Optional[ModelToolType] = Field(
        default=None, description="Tool involved in this action"
    )


class ModelActionOutput(BaseModel):
    """Strongly typed output data from an agent action."""

    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True)

    result: Dict[str, Any] = Field(description="Action result data")
    modified_files: List[Path] = Field(
        default_factory=list, description="Files that were modified"
    )
    created_files: List[Path] = Field(
        default_factory=list, description="Files that were created"
    )
    metrics: List[ModelMetricValue] = Field(
        default_factory=list, description="Performance metrics"
    )


class ModelActionReasoning(BaseModel):
    """Agent reasoning process for an action."""

    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True)

    thought_process: str = Field(description="Agent's reasoning steps", min_length=1)
    alternatives_considered: List[str] = Field(
        default_factory=list, description="Other options considered"
    )
    decision_factors: Dict[str, Any] = Field(
        description="Factors that influenced the decision"
    )
    confidence_level: ModelMetricValue = Field(description="Confidence in the decision")
    learned_patterns: List[str] = Field(
        default_factory=list, description="Patterns identified during reasoning"
    )


class ModelAgentAction(BaseModel):
    """
    Complete agent action model for audit trail and learning.

    This model captures all aspects of an individual agent action
    including input, output, reasoning, performance, and context.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        json_encoders={datetime: lambda v: v.isoformat()},
    )

    # Primary identification
    action_id: str = Field(
        default_factory=lambda: str(uuid4()), description="Unique action identifier"
    )
    agent_id: str = Field(
        description="ID of the agent performing the action", min_length=1
    )

    # Action classification
    action_type: EnumActionType = Field(description="Type of action performed")
    action_description: str = Field(
        description="Human-readable description of the action", min_length=1
    )

    # Context and correlation
    work_session_id: Optional[str] = Field(
        default=None, description="Work session identifier"
    )
    correlation_id: Optional[UUID] = Field(
        default=None, description="Correlation ID for related actions"
    )
    parent_action_id: Optional[str] = Field(
        default=None, description="Parent action if this is a sub-action"
    )

    # Input and output with strong typing
    input_data: ModelActionInput = Field(description="Strongly typed input data")
    output_data: ModelActionOutput = Field(description="Strongly typed output data")

    # Outcome tracking
    outcome: EnumActionOutcome = Field(description="Outcome of the action")
    error_message: Optional[str] = Field(
        default=None, description="Error message if action failed"
    )

    # Performance metrics
    duration_ms: int = Field(
        default=0, ge=0, description="Action duration in milliseconds"
    )
    tokens_used: int = Field(default=0, ge=0, description="Number of tokens consumed")
    cost_estimate: ModelMetricValue = Field(
        default_factory=lambda: ModelMetricValue(
            name="action_cost", value=0.0, unit="usd"
        ),
        description="Estimated cost of the action",
    )

    # Learning and reasoning
    reasoning: ModelActionReasoning = Field(description="Agent reasoning process")

    # File and tool context
    affected_files: List[Path] = Field(
        default_factory=list, description="Files affected by this action"
    )
    tools_involved: List[ModelToolType] = Field(
        default_factory=list, description="Tools used in this action"
    )

    # Extensible metadata
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata for extensibility"
    )

    # Timestamps
    timestamp: datetime = Field(description="When the action was performed")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Record creation timestamp"
    )
