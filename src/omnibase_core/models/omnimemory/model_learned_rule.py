"""
Learned rule models for the OmniMemory auto rule learning system.

These models define structures for automatically learning context injection
rules from developer corrections, diff analysis, and pattern recognition.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class EnumLearningMethod(str, Enum):
    """Methods used to learn rules from interactions."""

    DIFF_ANALYSIS = "diff_analysis"
    PATTERN_MINING = "pattern_mining"
    CORRECTION_TRACKING = "correction_tracking"
    FREQUENCY_ANALYSIS = "frequency_analysis"
    TEMPORAL_PATTERN = "temporal_pattern"
    CONTEXT_CORRELATION = "context_correlation"


class EnumPatternType(str, Enum):
    """Types of patterns that can be learned."""

    TYPING_CORRECTION = "typing_correction"
    CODE_CONVENTION = "code_convention"
    IMPORT_PATTERN = "import_pattern"
    NAMING_CONVENTION = "naming_convention"
    STRUCTURE_PATTERN = "structure_pattern"
    CONTEXT_INJECTION = "context_injection"
    ERROR_PREVENTION = "error_prevention"


class EnumLearningConfidence(str, Enum):
    """Confidence levels for learned rules."""

    HIGH = "high"  # 80%+ confidence, can be auto-applied
    MEDIUM = "medium"  # 60-80% confidence, suggest for review
    LOW = "low"  # 40-60% confidence, requires validation
    UNCERTAIN = "uncertain"  # <40% confidence, needs investigation


class ModelPatternObservation(BaseModel):
    """Model for a single pattern observation from developer behavior."""

    observation_id: str = Field(description="Unique identifier for this observation")

    # Observation context
    session_id: str = Field(description="Session where this observation was made")
    interaction_id: str = Field(
        description="Specific interaction that generated this observation",
    )

    # Pattern details
    pattern_type: EnumPatternType = Field(description="Type of pattern observed")
    before_code: str = Field(description="Code before the developer correction")
    after_code: str = Field(description="Code after the developer correction")

    # Context information
    file_context: str | None = Field(
        default=None,
        description="File path or context where pattern was observed",
    )
    surrounding_context: str | None = Field(
        default=None,
        description="Code surrounding the correction",
    )
    conversation_context: str | None = Field(
        default=None,
        description="Conversation context when correction was made",
    )

    # Developer feedback
    correction_method: str = Field(
        description="How the correction was made (manual edit, tool usage, etc.)",
    )
    correction_frequency: int = Field(
        default=1,
        description="How many times this correction has been observed",
    )

    # Observation metadata
    observed_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this observation was made",
    )
    learning_method: EnumLearningMethod = Field(
        description="Method used to capture this observation",
    )


class ModelLearnedPattern(BaseModel):
    """Model for a pattern learned from multiple observations."""

    pattern_id: str = Field(description="Unique identifier for this learned pattern")
    name: str = Field(description="Human-readable name for the pattern")
    description: str = Field(description="Description of what this pattern represents")

    # Pattern definition
    pattern_type: EnumPatternType = Field(description="Type of pattern this represents")
    trigger_pattern: str = Field(description="Pattern that triggers this correction")
    replacement_pattern: str = Field(description="Pattern to replace the trigger with")

    # Learning details
    learning_method: EnumLearningMethod = Field(
        description="Primary method used to learn this pattern",
    )
    source_observations: list[str] = Field(
        description="IDs of observations that contributed to learning this pattern",
    )
    observation_count: int = Field(
        description="Number of observations used to learn this pattern",
    )

    # Confidence and validation
    confidence: EnumLearningConfidence = Field(
        description="Confidence level in this learned pattern",
    )
    confidence_score: float = Field(description="Numeric confidence score (0.0-1.0)")
    validation_attempts: int = Field(
        default=0,
        description="Number of times this pattern has been validated",
    )
    validation_successes: int = Field(
        default=0,
        description="Number of successful validations",
    )

    # Pattern effectiveness
    times_applied: int = Field(
        default=0,
        description="Number of times this pattern has been applied",
    )
    successful_applications: int = Field(
        default=0,
        description="Number of times application was successful",
    )
    developer_corrections: int = Field(
        default=0,
        description="Number of times developers corrected this pattern's output",
    )

    # Context constraints
    applicable_contexts: list[str] = Field(
        default_factory=list,
        description="Contexts where this pattern is applicable",
    )
    excluded_contexts: list[str] = Field(
        default_factory=list,
        description="Contexts where this pattern should not be applied",
    )

    # Rule generation
    generated_rule_id: str | None = Field(
        default=None,
        description="ID of context rule generated from this pattern",
    )
    rule_generated_at: datetime | None = Field(
        default=None,
        description="When a rule was generated from this pattern",
    )

    # Lifecycle
    learned_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this pattern was first learned",
    )
    last_reinforced: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this pattern was last reinforced by an observation",
    )

    # Status
    active: bool = Field(
        default=True,
        description="Whether this pattern is actively being used for learning",
    )
    promoted_to_rule: bool = Field(
        default=False,
        description="Whether this pattern has been promoted to a formal rule",
    )


class ModelDiffAnalysis(BaseModel):
    """Model for analysis of code differences to extract patterns."""

    analysis_id: str = Field(description="Unique identifier for this diff analysis")

    # Diff source
    before_code: str = Field(description="Code before changes")
    after_code: str = Field(description="Code after changes")
    diff_context: str = Field(description="Context information about the diff")

    # Analysis results
    changes_detected: list[str] = Field(description="List of specific changes detected")
    patterns_extracted: list[str] = Field(
        description="Patterns extracted from the diff",
    )

    # Classification
    change_type: str = Field(
        description="Type of change (typing, structure, style, etc.)",
    )
    complexity_score: float = Field(description="Complexity score of the changes")
    impact_scope: str = Field(description="Scope of impact (local, module, project)")

    # Pattern analysis
    repeated_pattern: bool = Field(
        description="Whether this represents a repeated pattern",
    )
    similar_changes_count: int = Field(
        default=0,
        description="Number of similar changes seen before",
    )

    # Analysis metadata
    analyzed_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this analysis was performed",
    )
    analysis_method: str = Field(description="Method used for diff analysis")
    analysis_duration_ms: float = Field(description="Time taken for analysis")


class ModelRuleLearningSession(BaseModel):
    """Model for a session of rule learning from interactions."""

    session_id: str = Field(description="Unique identifier for this learning session")

    # Session scope
    conversation_session_id: str = Field(
        description="ID of the conversation session being analyzed",
    )
    interactions_analyzed: int = Field(
        description="Number of interactions analyzed in this session",
    )

    # Learning results
    observations_captured: int = Field(
        description="Number of new observations captured",
    )
    patterns_learned: int = Field(description="Number of new patterns learned")
    patterns_reinforced: int = Field(
        description="Number of existing patterns reinforced",
    )
    rules_generated: int = Field(description="Number of new rules generated")

    # Quality metrics
    confidence_improvements: int = Field(
        description="Number of patterns with improved confidence",
    )
    validation_failures: int = Field(
        description="Number of patterns that failed validation",
    )

    # Learning effectiveness
    learning_efficiency: float = Field(
        description="Efficiency score for this learning session",
    )
    pattern_diversity: float = Field(description="Diversity score of patterns learned")

    # Session metadata
    started_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this learning session started",
    )
    completed_at: datetime | None = Field(
        default=None,
        description="When this learning session completed",
    )
    duration_ms: float = Field(
        default=0.0,
        description="Duration of the learning session",
    )

    # Processing details
    learning_methods_used: list[EnumLearningMethod] = Field(
        description="Learning methods used in this session",
    )
    processing_errors: list[str] = Field(
        default_factory=list,
        description="Errors encountered during learning",
    )


class ModelLearningInsight(BaseModel):
    """Model for insights gained from the learning process."""

    insight_id: str = Field(description="Unique identifier for this insight")
    insight_type: str = Field(
        description="Type of insight (trend, anomaly, opportunity)",
    )

    # Insight content
    title: str = Field(description="Brief title for the insight")
    description: str = Field(description="Detailed description of the insight")
    evidence: list[str] = Field(description="Evidence supporting this insight")

    # Insight metrics
    confidence: float = Field(description="Confidence in this insight (0.0-1.0)")
    impact_potential: str = Field(
        description="Potential impact of acting on this insight",
    )

    # Related data
    related_patterns: list[str] = Field(
        default_factory=list,
        description="Pattern IDs related to this insight",
    )
    related_observations: list[str] = Field(
        default_factory=list,
        description="Observation IDs related to this insight",
    )

    # Actionability
    actionable: bool = Field(description="Whether this insight can be acted upon")
    recommended_actions: list[str] = Field(
        default_factory=list,
        description="Recommended actions based on this insight",
    )

    # Lifecycle
    discovered_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this insight was discovered",
    )
    acted_upon: bool = Field(
        default=False,
        description="Whether action has been taken on this insight",
    )


class ModelLearningSystemStatus(BaseModel):
    """Model for the overall status of the auto rule learning system."""

    # System status
    learning_active: bool = Field(description="Whether learning is currently active")
    last_learning_session: datetime | None = Field(
        default=None,
        description="When the last learning session completed",
    )

    # Learning statistics
    total_observations: int = Field(description="Total number of observations captured")
    total_patterns: int = Field(description="Total number of patterns learned")
    active_patterns: int = Field(description="Number of currently active patterns")
    rules_generated: int = Field(
        description="Total number of rules generated from patterns",
    )

    # Quality metrics
    average_pattern_confidence: float = Field(
        description="Average confidence score across all patterns",
    )
    pattern_success_rate: float = Field(
        description="Success rate of pattern applications",
    )
    learning_velocity: float = Field(description="Rate of learning new patterns")

    # Recent activity
    observations_24h: int = Field(description="Observations captured in last 24 hours")
    patterns_learned_24h: int = Field(description="Patterns learned in last 24 hours")
    rules_generated_24h: int = Field(description="Rules generated in last 24 hours")

    # System health
    learning_system_load: float = Field(
        description="Current load on the learning system",
    )
    processing_errors_24h: int = Field(description="Processing errors in last 24 hours")

    # Insights
    available_insights: int = Field(
        description="Number of actionable insights available",
    )
    insights_acted_upon: int = Field(
        description="Number of insights that have been acted upon",
    )

    # Status metadata
    status_generated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this status was generated",
    )
