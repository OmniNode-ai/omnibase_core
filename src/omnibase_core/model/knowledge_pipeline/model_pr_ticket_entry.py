"""PR ticket entry model for direct-to-database knowledge pipeline."""

from datetime import datetime
from typing import Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field


class ModelPrTicketEntry(BaseModel):
    """Direct-to-database PR ticket entry bypassing repository.

    This model captures comprehensive pull request data with enhanced UUIDs
    and tree tracking that gets written directly to PostgreSQL without creating
    repository files, enabling instant knowledge availability and real-time learning.
    """

    # Core identification
    pr_ticket_id: Optional[UUID] = Field(
        None, description="Auto-generated UUID for the PR ticket entry"
    )
    session_id: str = Field(..., description="Claude Code session identifier")
    conversation_id: Optional[str] = Field(
        None, description="Conversation context identifier"
    )

    # PR identification
    pr_number: Optional[int] = Field(None, description="Pull request number")
    pr_title: str = Field(..., description="Pull request title")
    pr_description: Optional[str] = Field(None, description="Pull request description")
    pr_url: Optional[str] = Field(None, description="URL to the pull request")

    # Git metadata
    source_branch: str = Field(..., description="Source branch for the pull request")
    target_branch: str = Field(..., description="Target branch for the pull request")
    git_commit_hash: Optional[str] = Field(None, description="Git commit hash")
    merge_commit_hash: Optional[str] = Field(
        None, description="Merge commit hash if merged"
    )

    # File tracking with UUIDs
    modified_files: Dict[str, Union[str, int, List[Dict[str, Union[str, int]]]]] = (
        Field(..., description="Array of file modifications with metadata")
    )
    tree_structure_before: Optional[
        Dict[str, Union[str, List[str], Dict[str, str]]]
    ] = Field(None, description="Directory tree structure before changes")
    tree_structure_after: Optional[Dict[str, Union[str, List[str], Dict[str, str]]]] = (
        Field(None, description="Directory tree structure after changes")
    )
    file_relationships: Optional[Dict[str, Union[List[str], Dict[str, List[str]]]]] = (
        Field(None, description="Dependencies and imports between files")
    )

    # Tool call tracking
    tool_calls: Dict[str, Union[str, List[Dict[str, Union[str, datetime]]]]] = Field(
        ..., description="Array of tool calls made during PR creation"
    )
    operation_sequence: List[str] = Field(
        default_factory=list, description="Sequence of operations performed"
    )

    # Quality metrics
    code_quality_delta: Optional[float] = Field(
        None, description="Change in code quality score"
    )
    test_coverage_change: Optional[float] = Field(
        None, description="Change in test coverage"
    )
    documentation_completeness: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Documentation completeness score"
    )
    security_impact_score: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Security impact assessment score"
    )

    # Review tracking
    review_status: str = Field(
        default="pending",
        description="Current review status",
        regex="^(pending|in_review|approved|changes_requested|merged|closed)$",
    )
    reviewer_feedback: Optional[Dict[str, Union[str, List[str], Dict[str, str]]]] = (
        Field(None, description="Feedback from reviewers")
    )
    merge_conflicts_resolved: int = Field(
        default=0, ge=0, description="Number of merge conflicts resolved"
    )

    # Business impact
    feature_impact: Optional[str] = Field(
        None, description="Impact of the feature on business objectives"
    )
    business_value_score: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Business value assessment score"
    )
    user_impact_assessment: Optional[str] = Field(
        None, description="Assessment of impact on users"
    )

    # Metadata
    created_at: datetime = Field(
        default_factory=datetime.now, description="When the PR ticket was created"
    )
    merged_at: Optional[datetime] = Field(None, description="When the PR was merged")
    closed_at: Optional[datetime] = Field(None, description="When the PR was closed")

    # Intelligence integration
    pattern_id: Optional[UUID] = Field(
        None, description="Reference to learning pattern if applicable"
    )
    success_prediction_score: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="AI prediction score for PR success"
    )
    risk_assessment: Optional[Dict[str, Union[str, float, List[str]]]] = Field(
        None, description="Risk assessment data"
    )

    class Config:
        """Pydantic configuration."""

        json_encoders = {datetime: lambda v: v.isoformat(), UUID: lambda v: str(v)}
        schema_extra = {
            "example": {
                "session_id": "claude_session_pr_001",
                "conversation_id": "conv_pr_789",
                "pr_number": 123,
                "pr_title": "Add user authentication system",
                "pr_description": "Implements JWT-based authentication with role-based access control",
                "pr_url": "https://github.com/org/repo/pull/123",
                "source_branch": "feature/auth-system",
                "target_branch": "main",
                "git_commit_hash": "a1b2c3d4e5f6",
                "modified_files": {
                    "files": [
                        {
                            "file_path": "/src/auth/models.py",
                            "file_uuid": "uuid-auth-models",
                            "change_type": "created",
                            "lines_changed": 120,
                        },
                        {
                            "file_path": "/src/auth/views.py",
                            "file_uuid": "uuid-auth-views",
                            "change_type": "created",
                            "lines_changed": 85,
                        },
                    ]
                },
                "tree_structure_before": {
                    "directories": ["/src", "/tests"],
                    "file_count": 45,
                },
                "tree_structure_after": {
                    "directories": ["/src", "/src/auth", "/tests", "/tests/auth"],
                    "file_count": 53,
                },
                "file_relationships": {
                    "imports": {
                        "/src/auth/views.py": [
                            "/src/auth/models.py",
                            "/src/core/decorators.py",
                        ],
                        "/src/auth/models.py": ["/src/core/base.py"],
                    }
                },
                "tool_calls": {
                    "calls": [
                        {
                            "tool_name": "Write",
                            "timestamp": "2025-08-16T10:15:00Z",
                            "file_affected": "/src/auth/models.py",
                            "operation": "create_file",
                        },
                        {
                            "tool_name": "Edit",
                            "timestamp": "2025-08-16T10:45:00Z",
                            "file_affected": "/src/auth/views.py",
                            "operation": "modify_file",
                        },
                    ]
                },
                "operation_sequence": [
                    "analyze_requirements",
                    "create_auth_models",
                    "implement_views",
                    "add_tests",
                    "update_documentation",
                ],
                "code_quality_delta": 0.05,
                "test_coverage_change": 0.12,
                "documentation_completeness": 0.85,
                "security_impact_score": 0.9,
                "review_status": "pending",
                "reviewer_feedback": {
                    "comments": ["Good implementation", "Add more edge case tests"],
                    "approval_count": 0,
                    "change_requests": 1,
                },
                "merge_conflicts_resolved": 0,
                "feature_impact": "Enables secure user management and access control",
                "business_value_score": 0.8,
                "user_impact_assessment": "High - affects all user interactions",
                "success_prediction_score": 0.75,
                "risk_assessment": {
                    "security_risk": "medium",
                    "complexity_risk": 0.6,
                    "potential_issues": ["authentication_bypass", "session_management"],
                },
            }
        }
