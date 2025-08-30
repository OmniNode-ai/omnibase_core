"""Velocity log entry model for direct-to-database knowledge pipeline."""

from datetime import datetime
from typing import Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field


class ModelVelocityLogEntry(BaseModel):
    """Direct-to-database velocity log entry bypassing repository.

    This model captures development velocity metrics and patterns that get
    written directly to PostgreSQL without creating repository files, enabling
    instant knowledge availability and real-time learning for productivity analysis.
    """

    # Core identification
    velocity_id: Optional[UUID] = Field(
        None, description="Auto-generated UUID for the velocity log entry"
    )
    session_id: str = Field(..., description="Claude Code session identifier")
    conversation_id: Optional[str] = Field(
        None, description="Conversation context identifier"
    )

    # Task identification
    task_type: str = Field(..., description="Type of development task being performed")
    task_description: str = Field(..., description="Detailed description of the task")
    task_complexity: Optional[str] = Field(
        None,
        description="Task complexity level",
        regex="^(simple|moderate|complex|expert)$",
    )

    # Timing metrics
    start_time: datetime = Field(..., description="When the task started")
    end_time: datetime = Field(..., description="When the task completed")
    # Note: duration_minutes is computed in database as GENERATED column

    # Progress tracking
    completion_percentage: int = Field(
        default=100, ge=0, le=100, description="Percentage of task completion"
    )
    success_status: str = Field(
        ...,
        description="Task completion status",
        regex="^(success|partial|failed|abandoned)$",
    )

    # Development metrics
    tools_used: List[str] = Field(
        default_factory=list, description="List of tools used during the task"
    )
    files_modified: int = Field(default=0, ge=0, description="Number of files modified")
    lines_added: int = Field(default=0, ge=0, description="Number of lines added")
    lines_removed: int = Field(default=0, ge=0, description="Number of lines removed")
    errors_encountered: int = Field(
        default=0, ge=0, description="Number of errors encountered"
    )

    # Quality metrics
    code_quality_score: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Code quality assessment score"
    )
    test_coverage_delta: Optional[float] = Field(
        None, description="Change in test coverage"
    )
    documentation_updated: bool = Field(
        default=False, description="Whether documentation was updated"
    )

    # Context and patterns
    work_ticket_id: Optional[str] = Field(
        None, description="Associated work ticket identifier"
    )
    epic_id: Optional[str] = Field(None, description="Associated epic identifier")
    developer_focus_area: Optional[str] = Field(
        None, description="Primary focus area for the developer"
    )
    interruption_count: int = Field(
        default=0, ge=0, description="Number of interruptions during the task"
    )
    context_switches: int = Field(
        default=0, ge=0, description="Number of context switches"
    )

    # Learning data
    productivity_patterns: Optional[
        Dict[str, Union[str, int, float, bool, List[str]]]
    ] = Field(None, description="Patterns that affected productivity")
    blockers_encountered: List[str] = Field(
        default_factory=list, description="List of blockers encountered"
    )
    efficiency_notes: Optional[str] = Field(
        None, description="Notes about efficiency and productivity"
    )

    # Metadata
    created_at: datetime = Field(
        default_factory=datetime.now, description="When the velocity log was created"
    )
    git_branch: Optional[str] = Field(None, description="Git branch being worked on")
    pr_number: Optional[int] = Field(None, description="Associated pull request number")

    # Intelligence integration
    pattern_id: Optional[UUID] = Field(
        None, description="Reference to learning pattern if applicable"
    )
    velocity_trend: Optional[str] = Field(
        None,
        description="Velocity trend analysis",
        regex="^(improving|stable|declining)$",
    )
    benchmark_comparison: Optional[Dict[str, Union[str, int, float]]] = Field(
        None, description="Comparison against benchmarks"
    )

    class Config:
        """Pydantic configuration."""

        json_encoders = {datetime: lambda v: v.isoformat(), UUID: lambda v: str(v)}
        schema_extra = {
            "example": {
                "session_id": "claude_session_67890",
                "conversation_id": "conv_54321",
                "task_type": "feature_implementation",
                "task_description": "Implement user authentication system",
                "task_complexity": "complex",
                "start_time": "2025-08-16T10:00:00Z",
                "end_time": "2025-08-16T14:30:00Z",
                "completion_percentage": 100,
                "success_status": "success",
                "tools_used": ["Edit", "Bash", "Read", "Write"],
                "files_modified": 8,
                "lines_added": 245,
                "lines_removed": 12,
                "errors_encountered": 2,
                "code_quality_score": 0.85,
                "test_coverage_delta": 0.15,
                "documentation_updated": True,
                "work_ticket_id": "AUTH-123",
                "epic_id": "SECURITY-EPIC-1",
                "developer_focus_area": "backend_security",
                "interruption_count": 1,
                "context_switches": 3,
                "productivity_patterns": {
                    "peak_hours": "morning",
                    "flow_state_duration": 180,
                    "tool_efficiency": "high",
                },
                "blockers_encountered": [
                    "dependency_installation",
                    "environment_setup",
                ],
                "efficiency_notes": "Good flow state, minimal context switching",
                "git_branch": "feature/auth-system",
                "pr_number": 456,
                "velocity_trend": "improving",
                "benchmark_comparison": {
                    "lines_per_hour": 67.5,
                    "quality_vs_team_avg": 1.15,
                },
            }
        }
