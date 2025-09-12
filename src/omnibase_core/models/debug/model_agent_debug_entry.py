"""
Models for agent debug entries and self-improving AI system.

This model represents debug information, success/failure patterns,
and contextual intelligence for Claude Code agents that learn
from every attempt and improve over time.
"""

from datetime import datetime, timedelta
from enum import Enum

from pydantic import BaseModel, Field

# Import the strongly typed models
from omnibase_core.models.debug.model_agent_attempt_details import (
    ModelAgentAttemptDetails,
)
from omnibase_core.models.debug.model_extraction_metadata import ModelExtractionMetadata
from omnibase_core.models.debug.model_similar_task_outcome import (
    ModelSimilarTaskOutcome,
)


class DebugSeverity(str, Enum):
    """Debug entry severity levels."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class DebugCategory(str, Enum):
    """Debug entry categories for classification."""

    LOGIC = "logic"
    INTEGRATION = "integration"
    PERFORMANCE = "performance"
    SECURITY = "security"
    DATA = "data"
    INFRASTRUCTURE = "infrastructure"
    USER_INTERFACE = "user_interface"
    CONFIGURATION = "configuration"


class ModelAgentDebugEntry(BaseModel):
    """Model for agent debug entries tracking every attempt."""

    entry_id: str = Field(description="Unique identifier for this debug entry")
    agent_id: str = Field(description="ID of the agent that made this attempt")
    task_description: str = Field(description="Description of the task attempted")
    attempt_details: ModelAgentAttemptDetails = Field(
        description="Detailed information about the attempt",
    )
    success: bool = Field(description="Whether the attempt was successful")
    error_message: str | None = Field(
        default=None,
        description="Error message if attempt failed",
    )
    execution_trace: list[str] = Field(
        default_factory=list,
        description="Step-by-step execution trace",
    )
    category: DebugCategory = Field(description="Category of the debug entry")
    severity: DebugSeverity = Field(description="Severity level of the entry")
    tags: list[str] = Field(
        default_factory=list,
        description="Tags for categorization and search",
    )
    resolution_status: str = Field(
        default="open",
        description="Status of issue resolution",
    )
    learning_extraction: dict[str, str] = Field(
        default_factory=dict,
        description="Extracted learning points from this attempt",
    )
    context_fingerprint: str | None = Field(
        default=None,
        description="Fingerprint of the context for similarity matching",
    )
    related_entries: list[str] = Field(
        default_factory=list,
        description="IDs of related debug entries",
    )
    knowledge_contribution_score: float = Field(
        default=0.5,
        description="Score indicating value of this entry to knowledge base",
    )
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="When this debug entry was created",
    )
    updated_at: datetime = Field(
        default_factory=datetime.now,
        description="When this entry was last updated",
    )

    @property
    def is_recent(self) -> bool:
        """Check if debug entry is recent (within last 24 hours)."""
        return datetime.now() - self.created_at < timedelta(hours=24)

    @property
    def is_high_value(self) -> bool:
        """Check if this entry provides high value learning."""
        return self.knowledge_contribution_score > 0.7

    @property
    def execution_duration(self) -> float | None:
        """Calculate execution duration if available in trace."""
        if len(self.execution_trace) >= 2:
            # Try to extract timing information from trace
            try:
                self.execution_trace[0]
                self.execution_trace[-1]
                # This would need parsing logic based on trace format
                return None  # Placeholder
            except:
                return None
        return None

    def add_related_entry(self, entry_id: str) -> None:
        """Add a related debug entry."""
        if entry_id not in self.related_entries:
            self.related_entries.append(entry_id)
            self.updated_at = datetime.now()

    def update_resolution_status(
        self,
        status: str,
        resolution_notes: str | None = None,
    ) -> None:
        """Update the resolution status of this entry."""
        self.resolution_status = status
        if resolution_notes:
            self.learning_extraction["resolution_notes"] = resolution_notes
        self.updated_at = datetime.now()


class ModelSuccessPattern(BaseModel):
    """Model for success patterns extracted from successful attempts."""

    pattern_id: str = Field(description="Unique identifier for this success pattern")
    task_context: str = Field(description="Context where this pattern was successful")
    successful_approach: str = Field(
        description="Description of the successful approach",
    )
    key_techniques: list[str] = Field(
        description="Key techniques that contributed to success",
    )
    tools_used: list[str] = Field(
        default_factory=list,
        description="Tools that were used in the successful attempt",
    )
    execution_steps: list[str] = Field(
        default_factory=list,
        description="Step-by-step execution that led to success",
    )
    preconditions: list[str] = Field(
        default_factory=list,
        description="Conditions that need to be met for this pattern to work",
    )
    success_indicators: list[str] = Field(
        default_factory=list,
        description="Indicators that show the pattern is working",
    )
    confidence_score: float = Field(
        description="Confidence in this pattern's effectiveness (0.0-1.0)",
    )
    reusability_score: float = Field(
        description="How reusable this pattern is in other contexts (0.0-1.0)",
    )
    validation_evidence: list[str] = Field(
        default_factory=list,
        description="Evidence that validates this pattern's success",
    )
    applicable_contexts: list[str] = Field(
        default_factory=list,
        description="Contexts where this pattern is applicable",
    )
    performance_metrics: dict[str, float] | None = Field(
        default=None,
        description="Performance metrics associated with this pattern",
    )
    usage_count: int = Field(
        default=1,
        description="Number of times this pattern has been successfully used",
    )
    last_used: datetime | None = Field(
        default=None,
        description="When this pattern was last successfully used",
    )
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="When this pattern was identified",
    )

    @property
    def is_proven(self) -> bool:
        """Check if pattern is proven with multiple successful uses."""
        return self.usage_count >= 3 and self.confidence_score > 0.8

    @property
    def is_recent(self) -> bool:
        """Check if pattern has been used recently."""
        if not self.last_used:
            return False
        return datetime.now() - self.last_used < timedelta(days=30)

    def record_usage(self, success: bool = True) -> None:
        """Record usage of this pattern."""
        if success:
            self.usage_count += 1
            self.last_used = datetime.now()
            # Increase confidence with successful usage
            self.confidence_score = min(1.0, self.confidence_score + 0.05)


class ModelFailurePattern(BaseModel):
    """Model for failure patterns to help avoid common mistakes."""

    pattern_id: str = Field(description="Unique identifier for this failure pattern")
    task_context: str = Field(description="Context where this failure pattern occurs")
    failed_approach: str = Field(description="Description of the approach that failed")
    error_indicators: list[str] = Field(
        description="Indicators that signal this type of failure",
    )
    root_cause_analysis: str = Field(description="Root cause analysis of the failure")
    prevention_strategies: list[str] = Field(
        default_factory=list,
        description="Strategies to prevent this type of failure",
    )
    detection_methods: list[str] = Field(
        default_factory=list,
        description="Methods to detect this failure early",
    )
    recovery_procedures: list[str] = Field(
        default_factory=list,
        description="Procedures to recover from this failure",
    )
    confidence_score: float = Field(
        description="Confidence in this failure pattern identification (0.0-1.0)",
    )
    severity: DebugSeverity = Field(
        description="Severity of failures following this pattern",
    )
    frequency: int = Field(
        default=1,
        description="Number of times this failure pattern has been observed",
    )
    last_occurrence: datetime | None = Field(
        default=None,
        description="When this failure pattern was last observed",
    )
    mitigation_effectiveness: float | None = Field(
        default=None,
        description="Effectiveness of mitigation strategies (0.0-1.0)",
    )
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="When this failure pattern was identified",
    )

    @property
    def is_critical(self) -> bool:
        """Check if this is a critical failure pattern."""
        return self.severity == DebugSeverity.CRITICAL and self.frequency >= 2

    @property
    def is_recurring(self) -> bool:
        """Check if this is a recurring failure pattern."""
        return self.frequency >= 3

    def record_occurrence(self) -> None:
        """Record a new occurrence of this failure pattern."""
        self.frequency += 1
        self.last_occurrence = datetime.now()


class ModelDebugContext(BaseModel):
    """Model for debug context provided to agents before starting work."""

    context_id: str = Field(description="Unique identifier for this debug context")
    task_description: str = Field(
        description="Description of the task for which context is provided",
    )
    agent_capabilities: list[str] = Field(
        description="Capabilities of the agent requesting context",
    )
    relevant_debug_entries: list[ModelAgentDebugEntry] = Field(
        description="Debug entries relevant to the current task",
    )
    success_patterns: list[ModelSuccessPattern] = Field(
        default_factory=list,
        description="Success patterns applicable to this task",
    )
    failure_patterns: list[ModelFailurePattern] = Field(
        default_factory=list,
        description="Failure patterns to avoid for this task",
    )
    contextual_recommendations: list[str] = Field(
        default_factory=list,
        description="Recommendations based on historical context",
    )
    similar_task_outcomes: list[ModelSimilarTaskOutcome] = Field(
        default_factory=list,
        description="Outcomes of similar tasks performed previously",
    )
    risk_assessment: dict[str, float] | None = Field(
        default=None,
        description="Risk assessment based on historical data",
    )
    confidence_score: float = Field(
        description="Confidence in the quality of this context (0.0-1.0)",
    )
    extraction_metadata: ModelExtractionMetadata = Field(
        default_factory=lambda: ModelExtractionMetadata(
            extraction_method="debug_context", confidence_level=0.8
        ),
        description="Metadata about how this context was extracted",
    )
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="When this context was created",
    )

    @property
    def has_high_confidence(self) -> bool:
        """Check if context has high confidence."""
        return self.confidence_score > 0.8

    @property
    def has_relevant_patterns(self) -> bool:
        """Check if context contains relevant patterns."""
        return len(self.success_patterns) > 0 or len(self.failure_patterns) > 0

    @property
    def pattern_count(self) -> int:
        """Get total number of patterns in context."""
        return len(self.success_patterns) + len(self.failure_patterns)

    def get_top_recommendations(self, limit: int = 5) -> list[str]:
        """Get top recommendations from context."""
        return self.contextual_recommendations[:limit]

    def get_critical_warnings(self) -> list[str]:
        """Get critical warnings from failure patterns."""
        warnings = []
        for pattern in self.failure_patterns:
            if pattern.is_critical:
                warnings.append(
                    f"CRITICAL: Avoid {pattern.failed_approach} - {pattern.root_cause_analysis}",
                )
        return warnings


class ModelLearningInsight(BaseModel):
    """Model for learning insights derived from debug data."""

    insight_id: str = Field(description="Unique identifier for this learning insight")
    insight_type: str = Field(
        description="Type of insight (pattern, trend, anomaly, etc.)",
    )
    description: str = Field(description="Description of the learning insight")
    evidence: list[str] = Field(description="Evidence supporting this insight")
    confidence: float = Field(description="Confidence in this insight (0.0-1.0)")
    actionable_recommendations: list[str] = Field(
        default_factory=list,
        description="Actionable recommendations based on this insight",
    )
    affected_agents: list[str] = Field(
        default_factory=list,
        description="Agents that would benefit from this insight",
    )
    impact_assessment: dict[str, str] = Field(
        default_factory=dict,
        description="Assessment of potential impact of this insight",
    )
    validation_status: str = Field(
        default="pending",
        description="Status of insight validation",
    )
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="When this insight was generated",
    )

    @property
    def is_validated(self) -> bool:
        """Check if insight has been validated."""
        return self.validation_status == "validated"

    @property
    def is_high_impact(self) -> bool:
        """Check if insight is high impact."""
        return self.confidence > 0.8 and len(self.affected_agents) > 1
