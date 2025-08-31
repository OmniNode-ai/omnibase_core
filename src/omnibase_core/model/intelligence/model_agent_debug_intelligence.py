"""Agent Debug Intelligence Models for automatic problem-solving capture.

These models enable agents to automatically capture their problem-solving process
and share intelligence with other agents through the knowledge base.
"""

from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, validator


class EnumProblemType(str, Enum):
    """Classification of problem types agents encounter."""

    CONFIGURATION_ERROR = "configuration_error"
    DEPENDENCY_ISSUE = "dependency_issue"
    VALIDATION_FAILURE = "validation_failure"
    PERFORMANCE_ISSUE = "performance_issue"
    INTEGRATION_FAILURE = "integration_failure"
    DATA_PROCESSING_ERROR = "data_processing_error"
    NETWORK_CONNECTIVITY = "network_connectivity"
    AUTHENTICATION_ERROR = "authentication_error"
    RESOURCE_CONSTRAINT = "resource_constraint"
    LOGIC_ERROR = "logic_error"
    ENVIRONMENT_MISMATCH = "environment_mismatch"
    VERSION_COMPATIBILITY = "version_compatibility"
    UNKNOWN = "unknown"


class EnumSolutionEffectiveness(str, Enum):
    """Measure of how effective a solution was."""

    HIGHLY_EFFECTIVE = "highly_effective"  # Solved completely, no issues
    EFFECTIVE = "effective"  # Solved the main problem
    PARTIALLY_EFFECTIVE = "partially_effective"  # Solved some aspects
    INEFFECTIVE = "ineffective"  # Did not solve the problem
    UNKNOWN = "unknown"  # Effectiveness not yet determined


class EnumAgentType(str, Enum):
    """Types of agents for context categorization."""

    STRUCTURED_LOGGING = "structured_logging"
    DEBUG_INTELLIGENCE = "debug_intelligence"
    CONTRACT_VALIDATOR = "contract_validator"
    CONTRACT_GENERATOR = "contract_generator"
    PR_REVIEW = "pr_review"
    COMMIT_GENERATOR = "commit_generator"
    TESTING = "testing"
    SECURITY_AUDIT = "security_audit"
    PERFORMANCE = "performance"
    RESEARCH = "research"
    GENERAL_PURPOSE = "general_purpose"


class ModelProblemContext(BaseModel):
    """Context information about the problem encountered."""

    subsystem: str | None = Field(
        None,
        description="ONEX subsystem where problem occurred",
    )
    component: str | None = Field(None, description="Specific component affected")
    operation: str | None = Field(None, description="Operation being performed")
    input_data: dict[str, str | int | float | bool | list[str]] | None = Field(
        None,
        description="Sanitized input data",
    )
    error_messages: list[str] | None = Field(
        None,
        description="Error messages encountered",
    )
    stack_trace: str | None = Field(None, description="Stack trace if applicable")
    environment: dict[str, str] | None = Field(
        None,
        description="Environment variables",
    )
    dependencies: dict[str, str] | None = Field(
        None,
        description="Relevant dependency versions",
    )
    user_context: str | None = Field(None, description="User or request context")

    @validator("input_data", "environment")
    def sanitize_sensitive_data(self, v):
        """Sanitize sensitive data from input_data and environment fields."""
        if v is None:
            return v

        sensitive_keywords = [
            "password",
            "token",
            "key",
            "secret",
            "auth",
            "credential",
            "api_key",
            "access_token",
            "refresh_token",
            "private_key",
            "cert",
            "certificate",
            "signature",
            "hash",
            "salt",
        ]

        if isinstance(v, dict):
            sanitized = {}
            for key, value in v.items():
                if any(sensitive in key.lower() for sensitive in sensitive_keywords):
                    sanitized[key] = "[REDACTED]"
                else:
                    sanitized[key] = value
            return sanitized

        return v

    @validator("stack_trace", "error_messages")
    def sanitize_stack_traces_and_errors(self, v):
        """Remove sensitive data from stack traces and error messages."""
        if v is None:
            return v

        sensitive_patterns = [
            "password=",
            "token=",
            "key=",
            "secret=",
            "auth=",
            "api_key=",
            "access_token=",
            "private_key=",
        ]

        if isinstance(v, list):
            sanitized = []
            for item in v:
                sanitized_item = str(item)
                for pattern in sensitive_patterns:
                    if pattern in sanitized_item.lower():
                        # Replace the value after = with [REDACTED]
                        parts = sanitized_item.lower().split(pattern)
                        if len(parts) > 1:
                            # Find the end of the sensitive value (usually space, comma, or end of string)
                            value_part = parts[1]
                            end_chars = [" ", ",", ")", "}", "]", "\n", "\t"]
                            end_pos = len(value_part)
                            for char in end_chars:
                                pos = value_part.find(char)
                                if pos != -1 and pos < end_pos:
                                    end_pos = pos
                            sanitized_item = (
                                sanitized_item[
                                    : sanitized_item.lower().find(pattern)
                                    + len(pattern)
                                ]
                                + "[REDACTED]"
                                + value_part[end_pos:]
                            )
                sanitized.append(sanitized_item)
            return sanitized
        if isinstance(v, str):
            sanitized = v
            for pattern in sensitive_patterns:
                if pattern in sanitized.lower():
                    parts = sanitized.lower().split(pattern)
                    if len(parts) > 1:
                        value_part = parts[1]
                        end_chars = [" ", ",", ")", "}", "]", "\n", "\t"]
                        end_pos = len(value_part)
                        for char in end_chars:
                            pos = value_part.find(char)
                            if pos != -1 and pos < end_pos:
                                end_pos = pos
                        sanitized = (
                            sanitized[: sanitized.lower().find(pattern) + len(pattern)]
                            + "[REDACTED]"
                            + value_part[end_pos:]
                        )
            return sanitized

        return v


class ModelSolutionApproach(BaseModel):
    """Details of the solution approach taken."""

    strategy: str = Field(
        ...,
        description="High-level strategy used to solve the problem",
    )
    steps: list[str] = Field(
        ...,
        description="Specific steps taken to implement solution",
    )
    tools_used: list[str] | None = Field(None, description="Tools or utilities used")
    code_changes: list[str] | None = Field(None, description="Code changes made")
    configuration_changes: list[str] | None = Field(
        None,
        description="Configuration changes",
    )
    external_resources: list[str] | None = Field(
        None,
        description="External docs or resources consulted",
    )
    time_to_solution: int | None = Field(
        None,
        description="Time to solve in minutes",
    )


class ModelSolutionOutcome(BaseModel):
    """Results and effectiveness of the solution."""

    effectiveness: EnumSolutionEffectiveness
    success_indicators: list[str] = Field(..., description="How success was measured")
    remaining_issues: list[str] | None = Field(
        None,
        description="Any unresolved aspects",
    )
    side_effects: list[str] | None = Field(
        None,
        description="Unintended consequences",
    )
    follow_up_actions: list[str] | None = Field(
        None,
        description="Additional actions needed",
    )
    lessons_learned: list[str] | None = Field(
        None,
        description="Key insights gained",
    )


class ModelAgentDebugIntelligence(BaseModel):
    """Complete model for agent debug intelligence capture."""

    # Identity
    entry_id: UUID = Field(default_factory=uuid4, description="Unique identifier")
    agent_name: str = Field(
        ...,
        description="Name of the agent that created this entry",
    )
    agent_type: EnumAgentType = Field(..., description="Type/category of the agent")
    agent_version: str = Field(..., description="Version of the agent")

    # Problem Description
    problem_type: EnumProblemType = Field(
        ...,
        description="Classification of the problem",
    )
    problem_description: str = Field(
        ...,
        description="Clear description of the problem",
    )
    problem_context: ModelProblemContext = Field(
        ...,
        description="Detailed context about the problem",
    )

    # Solution Details
    solution_approach: ModelSolutionApproach = Field(
        ...,
        description="How the problem was solved",
    )
    solution_outcome: ModelSolutionOutcome = Field(
        ...,
        description="Results of the solution",
    )

    # Intelligence Metadata
    similar_problems_consulted: list[UUID] | None = Field(
        None,
        description="Similar problems this agent referenced",
    )
    confidence_level: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Agent's confidence in this solution",
    )
    reusability_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="How reusable this solution is",
    )

    # Temporal Information
    problem_occurred_at: datetime = Field(
        ...,
        description="When the problem was first encountered",
    )
    solution_completed_at: datetime = Field(
        ...,
        description="When the solution was implemented",
    )
    entry_created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this entry was created",
    )

    # Correlation and Learning
    correlation_id: UUID | None = Field(
        None,
        description="Links related problem-solving sessions",
    )
    parent_task_id: str | None = Field(
        None,
        description="Parent task or operation ID",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Searchable tags for categorization",
    )

    @validator("problem_description")
    def validate_problem_description(self, v):
        """Ensure problem description is meaningful."""
        if len(v.strip()) < 10:
            msg = "Problem description must be at least 10 characters"
            raise ValueError(msg)
        return v.strip()

    @validator("tags")
    def validate_tags(self, v):
        """Ensure tags are lowercase and valid."""
        return [tag.lower().strip() for tag in v if tag.strip()]

    def calculate_solution_time_minutes(self) -> int:
        """Calculate time taken to solve the problem in minutes."""
        delta = self.solution_completed_at - self.problem_occurred_at
        return int(delta.total_seconds() / 60)

    def get_searchable_text(self) -> str:
        """Generate searchable text content for RAG indexing."""
        searchable_parts = [
            self.problem_description,
            self.solution_approach.strategy,
            " ".join(self.solution_approach.steps),
            " ".join(self.solution_outcome.success_indicators),
        ]

        if self.problem_context.error_messages:
            searchable_parts.extend(self.problem_context.error_messages)

        if self.solution_outcome.lessons_learned:
            searchable_parts.extend(self.solution_outcome.lessons_learned)

        return " ".join(filter(None, searchable_parts))

    def is_highly_reusable(self) -> bool:
        """Check if this solution is highly reusable for similar problems."""
        return (
            self.reusability_score >= 0.8
            and self.solution_outcome.effectiveness
            in [
                EnumSolutionEffectiveness.HIGHLY_EFFECTIVE,
                EnumSolutionEffectiveness.EFFECTIVE,
            ]
            and self.confidence_level >= 0.7
        )


class ModelDebugIntelligenceQuery(BaseModel):
    """Model for querying debug intelligence."""

    problem_description: str = Field(..., description="Description of current problem")
    problem_type: EnumProblemType | None = Field(
        None,
        description="Problem type filter",
    )
    agent_type: EnumAgentType | None = Field(None, description="Agent type filter")
    subsystem: str | None = Field(None, description="Subsystem filter")
    component: str | None = Field(None, description="Component filter")
    tags: list[str] | None = Field(None, description="Tag filters")
    min_effectiveness: EnumSolutionEffectiveness | None = Field(
        None,
        description="Minimum solution effectiveness",
    )
    min_reusability_score: float | None = Field(
        0.5,
        ge=0.0,
        le=1.0,
        description="Minimum reusability score",
    )
    limit: int = Field(10, ge=1, le=100, description="Maximum number of results")


class ModelDebugIntelligenceResult(BaseModel):
    """Result from debug intelligence query."""

    entry: ModelAgentDebugIntelligence
    similarity_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Similarity to query",
    )
    relevance_explanation: str = Field(..., description="Why this result is relevant")


class ModelDebugIntelligenceStats(BaseModel):
    """Statistics about debug intelligence in the system."""

    total_entries: int
    entries_by_agent_type: dict[str, int]
    entries_by_problem_type: dict[str, int]
    average_solution_time_minutes: float
    most_effective_solutions: int
    highly_reusable_solutions: int
    most_common_tags: list[str]
    recent_activity_count: int  # Entries in last 24 hours
