"""
Model quirk pattern models for the OmniMemory model quirk database.

These models define structures for tracking model-specific behaviors,
quirks, and adaptation patterns to optimize context injection for
different AI models.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class EnumModelType(str, Enum):
    """Supported AI model types."""

    CLAUDE_CODE = "claude_code"
    CLAUDE_SONNET = "claude_sonnet"
    CLAUDE_HAIKU = "claude_haiku"
    GPT_4 = "gpt_4"
    GPT_3_5 = "gpt_3_5"
    GEMINI_PRO = "gemini_pro"
    LLAMA = "llama"
    UNKNOWN = "unknown"


class EnumQuirkCategory(str, Enum):
    """Categories of model quirks and behaviors."""

    TYPING_PREFERENCE = "typing_preference"
    CODE_STYLE = "code_style"
    PATTERN_RECOGNITION = "pattern_recognition"
    CONTEXT_SENSITIVITY = "context_sensitivity"
    ERROR_HANDLING = "error_handling"
    IMPORT_BEHAVIOR = "import_behavior"
    NAMING_CONVENTION = "naming_convention"
    DOCUMENTATION_STYLE = "documentation_style"
    PERFORMANCE_BIAS = "performance_bias"
    SECURITY_AWARENESS = "security_awareness"


class EnumQuirkSeverity(str, Enum):
    """Severity levels for model quirks."""

    CRITICAL = "critical"  # Must be addressed to prevent broken code
    HIGH = "high"  # Should be addressed for best results
    MEDIUM = "medium"  # Recommended to address
    LOW = "low"  # Optional optimization
    COSMETIC = "cosmetic"  # Style preference only


class EnumAdaptationStrategy(str, Enum):
    """Strategies for adapting to model quirks."""

    PREEMPTIVE_INJECTION = (
        "preemptive_injection"  # Inject corrections before generation
    )
    PATTERN_REPLACEMENT = "pattern_replacement"  # Replace patterns during generation
    POST_CORRECTION = "post_correction"  # Correct after generation
    CONTEXT_PRIMING = "context_priming"  # Prime with specific context
    NEGATIVE_PROMPTING = "negative_prompting"  # Explicitly avoid patterns
    REINFORCEMENT = "reinforcement"  # Reinforce preferred patterns


class ModelQuirkPattern(BaseModel):
    """Model for a specific quirk pattern exhibited by an AI model."""

    quirk_id: str = Field(description="Unique identifier for this quirk")
    name: str = Field(description="Human-readable name for the quirk")
    description: str = Field(description="Detailed description of the quirk behavior")

    # Model information
    model_type: EnumModelType = Field(
        description="Type of model that exhibits this quirk",
    )
    model_version: str | None = Field(
        default=None,
        description="Specific version of the model (if applicable)",
    )

    # Quirk classification
    category: EnumQuirkCategory = Field(description="Category this quirk belongs to")
    severity: EnumQuirkSeverity = Field(description="Severity level of this quirk")

    # Pattern details
    trigger_pattern: str = Field(
        description="Pattern or condition that triggers this quirk",
    )
    quirk_behavior: str = Field(description="Description of the problematic behavior")
    example_input: str | None = Field(
        default=None,
        description="Example input that triggers the quirk",
    )
    example_output: str | None = Field(
        default=None,
        description="Example of the quirky output",
    )

    # Context conditions
    context_requirements: list[str] = Field(
        default_factory=list,
        description="Context conditions under which this quirk manifests",
    )
    domain_specific: list[str] = Field(
        default_factory=list,
        description="Specific domains where this quirk is more likely",
    )

    # Observation data
    observation_count: int = Field(
        default=1,
        description="Number of times this quirk has been observed",
    )
    first_observed: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this quirk was first observed",
    )
    last_observed: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this quirk was last observed",
    )

    # Frequency and conditions
    occurrence_frequency: float = Field(
        description="Frequency of quirk occurrence (0.0-1.0)",
    )
    confidence_score: float = Field(
        description="Confidence in quirk pattern identification",
    )

    # Impact assessment
    impact_description: str = Field(
        description="Description of the impact this quirk has",
    )
    business_impact: str = Field(
        default="low",
        description="Business impact level (critical, high, medium, low)",
    )

    # Related quirks
    related_quirks: list[str] = Field(
        default_factory=list,
        description="IDs of related quirk patterns",
    )

    # Status
    active: bool = Field(
        default=True,
        description="Whether this quirk is currently active/relevant",
    )
    verified: bool = Field(
        default=False,
        description="Whether this quirk has been verified",
    )


class ModelQuirkAdaptation(BaseModel):
    """Model for an adaptation strategy to handle a specific quirk."""

    adaptation_id: str = Field(description="Unique identifier for this adaptation")
    quirk_id: str = Field(description="ID of the quirk this adaptation addresses")

    # Adaptation details
    strategy: EnumAdaptationStrategy = Field(
        description="Strategy used for this adaptation",
    )
    name: str = Field(description="Human-readable name for the adaptation")
    description: str = Field(description="Description of how the adaptation works")

    # Implementation
    adaptation_content: str = Field(
        description="Content or pattern used for adaptation",
    )
    injection_point: str = Field(description="When/where to apply this adaptation")
    priority: int = Field(
        default=100,
        description="Priority of this adaptation (higher = more important)",
    )

    # Effectiveness tracking
    times_applied: int = Field(
        default=0,
        description="Number of times this adaptation has been applied",
    )
    successful_applications: int = Field(
        default=0,
        description="Number of times the adaptation was successful",
    )
    success_rate: float = Field(
        default=0.0,
        description="Success rate of this adaptation",
    )

    # Performance metrics
    avg_improvement_score: float = Field(
        default=0.0,
        description="Average improvement score when adaptation is applied",
    )
    prevented_errors: int = Field(
        default=0,
        description="Number of errors prevented by this adaptation",
    )

    # Configuration
    enabled: bool = Field(
        default=True,
        description="Whether this adaptation is currently enabled",
    )
    auto_apply: bool = Field(
        default=False,
        description="Whether to automatically apply this adaptation",
    )
    requires_approval: bool = Field(
        default=True,
        description="Whether adaptation requires human approval",
    )

    # Context constraints
    applicable_contexts: list[str] = Field(
        default_factory=list,
        description="Contexts where this adaptation should be applied",
    )
    excluded_contexts: list[str] = Field(
        default_factory=list,
        description="Contexts where this adaptation should not be applied",
    )

    # Lifecycle
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this adaptation was created",
    )
    last_applied: datetime | None = Field(
        default=None,
        description="When this adaptation was last applied",
    )

    # Validation
    validated: bool = Field(
        default=False,
        description="Whether this adaptation has been validated",
    )
    validation_results: str | None = Field(
        default=None,
        description="Results of adaptation validation",
    )


class ModelModelBehaviorProfile(BaseModel):
    """Model for the overall behavior profile of a specific AI model."""

    profile_id: str = Field(description="Unique identifier for this behavior profile")
    model_type: EnumModelType = Field(
        description="Type of model this profile describes",
    )
    model_version: str | None = Field(
        default=None,
        description="Specific version of the model",
    )

    # Profile metadata
    profile_name: str = Field(description="Human-readable name for this profile")
    description: str = Field(description="Description of the model's general behavior")

    # Quirk summary
    total_quirks: int = Field(
        description="Total number of quirks identified for this model",
    )
    critical_quirks: int = Field(description="Number of critical quirks")
    quirk_ids: list[str] = Field(
        description="List of quirk IDs associated with this model",
    )

    # Adaptation summary
    total_adaptations: int = Field(description="Total number of adaptations available")
    active_adaptations: int = Field(
        description="Number of currently active adaptations",
    )
    auto_adaptations: int = Field(description="Number of adaptations that auto-apply")

    # Performance characteristics
    typing_accuracy: float = Field(
        description="Model's accuracy in generating proper types",
    )
    pattern_consistency: float = Field(
        description="Consistency in following established patterns",
    )
    context_retention: float = Field(
        description="Ability to retain and use context effectively",
    )
    error_susceptibility: float = Field(
        description="Likelihood of making common errors",
    )

    # Preferences and biases
    preferred_patterns: list[str] = Field(
        default_factory=list,
        description="Patterns this model tends to favor",
    )
    avoided_patterns: list[str] = Field(
        default_factory=list,
        description="Patterns this model tends to avoid",
    )
    common_mistakes: list[str] = Field(
        default_factory=list,
        description="Common mistakes this model makes",
    )

    # Context sensitivity
    context_window_effectiveness: float = Field(
        description="How effectively the model uses its context window",
    )
    instruction_following: float = Field(
        description="How well the model follows specific instructions",
    )
    constraint_adherence: float = Field(
        description="How well the model adheres to constraints",
    )

    # Profile lifecycle
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this profile was created",
    )
    last_updated: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this profile was last updated",
    )
    data_points: int = Field(
        description="Number of data points used to build this profile",
    )

    # Validation and confidence
    profile_confidence: float = Field(description="Confidence in this behavior profile")
    validation_status: str = Field(
        default="pending",
        description="Validation status of this profile",
    )


class ModelQuirkDetectionResult(BaseModel):
    """Model for the result of quirk detection analysis."""

    detection_id: str = Field(description="Unique identifier for this detection")
    model_type: EnumModelType = Field(description="Model that was analyzed")

    # Input analyzed
    input_content: str = Field(description="Content that was analyzed for quirks")
    output_content: str = Field(description="Model output that was analyzed")
    context_used: str | None = Field(
        default=None,
        description="Context that was provided to the model",
    )

    # Detection results
    quirks_detected: list[str] = Field(
        description="List of quirk IDs that were detected",
    )
    new_quirks_identified: int = Field(
        description="Number of previously unknown quirks identified",
    )

    # Analysis details
    detection_confidence: float = Field(
        description="Overall confidence in quirk detection",
    )
    analysis_method: str = Field(description="Method used for quirk detection")

    # Impact assessment
    severity_breakdown: dict[str, int] = Field(
        description="Count of quirks by severity level",
    )
    immediate_action_required: bool = Field(
        description="Whether immediate action is required",
    )

    # Recommended adaptations
    recommended_adaptations: list[str] = Field(
        default_factory=list,
        description="IDs of adaptations recommended based on detected quirks",
    )

    # Detection metadata
    detected_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this detection was performed",
    )
    detection_duration_ms: float = Field(description="Time taken for quirk detection")


class ModelQuirkDatabaseStatus(BaseModel):
    """Model for the overall status of the model quirk database."""

    # Database statistics
    total_models_tracked: int = Field(
        description="Total number of models being tracked",
    )
    total_quirks: int = Field(description="Total number of quirks in the database")
    total_adaptations: int = Field(description="Total number of adaptations available")

    # Quirk breakdown
    quirks_by_severity: dict[str, int] = Field(
        description="Number of quirks by severity level",
    )
    quirks_by_category: dict[str, int] = Field(
        description="Number of quirks by category",
    )

    # Recent activity
    quirks_added_24h: int = Field(description="New quirks added in last 24 hours")
    adaptations_created_24h: int = Field(
        description="New adaptations created in last 24 hours",
    )
    detections_performed_24h: int = Field(
        description="Quirk detections performed in last 24 hours",
    )

    # Effectiveness metrics
    average_adaptation_success_rate: float = Field(
        description="Average success rate across all adaptations",
    )
    errors_prevented_24h: int = Field(
        description="Errors prevented by adaptations in last 24 hours",
    )

    # System health
    database_health: str = Field(
        description="Overall health status of the quirk database",
    )
    last_maintenance: datetime | None = Field(
        default=None,
        description="When database maintenance was last performed",
    )

    # Status metadata
    status_generated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this status was generated",
    )
