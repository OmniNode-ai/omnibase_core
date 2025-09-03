"""
AI Routing Preferences Model

Defines routing preferences for AI workflows that integrate with llm_005
metric-aware routing system for intelligent model selection and load balancing.
"""

from enum import Enum

from pydantic import BaseModel, Field, validator


class EnumCostConstraints(Enum):
    """Cost optimization preferences."""

    LOCAL_ONLY = "local_only"  # Use only local models (no cloud costs)
    LOCAL_PREFERRED = "local_preferred"  # Prefer local, fallback to cloud
    BALANCED = "balanced"  # Balance cost vs quality/performance
    CLOUD_PREFERRED = "cloud_preferred"  # Prefer cloud for better quality
    COST_OPTIMIZED = "cost_optimized"  # Always choose lowest cost option


class EnumAccuracyRequirements(Enum):
    """Accuracy level requirements."""

    LOW = "low"  # Basic accuracy acceptable (50-70%)
    MEDIUM = "medium"  # Good accuracy required (70-85%)
    HIGH = "high"  # High accuracy required (85-95%)
    VERY_HIGH = "very_high"  # Maximum accuracy required (95%+)
    CRITICAL = "critical"  # Mission-critical accuracy (near 100%)


class EnumLatencyRequirements(Enum):
    """Response time requirements."""

    REAL_TIME = "under_1s"  # < 1 second (interactive)
    FAST = "under_3s"  # < 3 seconds (responsive)
    MODERATE = "under_5s"  # < 5 seconds (acceptable)
    RELAXED = "under_10s"  # < 10 seconds (batch-like)
    BACKGROUND = "under_30s"  # < 30 seconds (background processing)


class EnumPrivacyLevel(Enum):
    """Data privacy requirements."""

    LOCAL_ONLY = "local_only"  # Never send data to external services
    SECURE_CLOUD = "secure_cloud"  # Allow secure cloud providers only
    STANDARD_CLOUD = "standard_cloud"  # Allow standard cloud providers
    ANY_PROVIDER = "any_provider"  # No privacy restrictions


class EnumLoadBalancing(Enum):
    """Load balancing strategies."""

    INTELLIGENT = "intelligent"  # Use llm_005 intelligent routing
    ROUND_ROBIN = "round_robin"  # Simple round-robin distribution
    LEAST_LOADED = "least_loaded"  # Route to least loaded provider
    CAPACITY_AWARE = "capacity_aware"  # Consider provider capacity
    STICKY_SESSION = "sticky_session"  # Maintain provider affinity


class ModelAIRoutingPreferences(BaseModel):
    """
    AI routing preferences for workflow orchestration.

    Integrates with llm_005 metric-aware routing system to provide
    intelligent model selection based on cost, accuracy, latency,
    and privacy requirements.
    """

    # Cost optimization preferences
    cost_constraints: EnumCostConstraints = Field(
        default=EnumCostConstraints.LOCAL_PREFERRED,
        description="Cost optimization strategy for model selection",
    )

    max_cost_per_request: float | None = Field(
        default=None,
        description="Maximum cost per request in USD (None = no limit)",
        ge=0.0,
    )

    # Accuracy requirements
    accuracy_requirements: EnumAccuracyRequirements = Field(
        default=EnumAccuracyRequirements.HIGH,
        description="Required accuracy level for task completion",
    )

    min_accuracy_threshold: float | None = Field(
        default=None,
        description="Minimum accuracy threshold (0.0-1.0)",
        ge=0.0,
        le=1.0,
    )

    # Performance requirements
    latency_requirements: EnumLatencyRequirements = Field(
        default=EnumLatencyRequirements.MODERATE,
        description="Maximum acceptable response latency",
    )

    max_latency_seconds: float | None = Field(
        default=None,
        description="Maximum latency in seconds (None = use enum default)",
        gt=0.0,
    )

    # Privacy and security
    privacy_level: EnumPrivacyLevel = Field(
        default=EnumPrivacyLevel.SECURE_CLOUD,
        description="Data privacy requirements for model routing",
    )

    allowed_regions: list[str] | None = Field(
        default=None,
        description="Allowed geographic regions for cloud providers",
    )

    # Model preferences
    model_preferences: list[str] | None = Field(
        default=None,
        description="Ordered list of preferred models (e.g., ['deepseek-coder', 'mistral'])",
    )

    provider_preferences: list[str] | None = Field(
        default=None,
        description="Ordered list of preferred providers (e.g., ['ollama', 'openai'])",
    )

    excluded_models: list[str] | None = Field(
        default=None,
        description="Models to exclude from routing decisions",
    )

    # Load balancing and distribution
    load_balancing: EnumLoadBalancing = Field(
        default=EnumLoadBalancing.INTELLIGENT,
        description="Load balancing strategy for distributed requests",
    )

    max_concurrent_requests: int | None = Field(
        default=None,
        description="Maximum concurrent requests per provider",
        gt=0,
    )

    # Advanced routing options
    task_type_hint: str | None = Field(
        default=None,
        description="Task type hint for accuracy-based routing (e.g., 'code_generation', 'text_analysis')",
    )

    context_size_hint: int | None = Field(
        default=None,
        description="Expected context size in tokens for capacity planning",
        gt=0,
    )

    # Fallback and retry behavior
    fallback_on_failure: bool = Field(
        default=True,
        description="Whether to fallback to alternative providers on failure",
    )

    max_retries: int = Field(
        default=2,
        description="Maximum retry attempts per provider",
        ge=0,
        le=5,
    )

    # Quality and validation preferences
    enable_quality_validation: bool = Field(
        default=False,
        description="Whether to enable output quality validation",
    )

    quality_validation_threshold: float | None = Field(
        default=None,
        description="Quality threshold for validation (0.0-1.0)",
        ge=0.0,
        le=1.0,
    )

    # Monitoring and observability
    enable_metrics_collection: bool = Field(
        default=True,
        description="Whether to collect routing and performance metrics",
    )

    custom_tags: dict[str, str] | None = Field(
        default=None,
        description="Custom tags for metrics and monitoring",
    )

    @validator("max_latency_seconds")
    def validate_latency_consistency(self, v, values):
        """Ensure max_latency_seconds is consistent with latency_requirements enum."""
        if v is None:
            return v

        latency_req = values.get("latency_requirements")
        if latency_req == EnumLatencyRequirements.REAL_TIME and v > 1.0:
            msg = "max_latency_seconds must be ≤ 1.0 for REAL_TIME requirements"
            raise ValueError(
                msg,
            )
        if latency_req == EnumLatencyRequirements.FAST and v > 3.0:
            msg = "max_latency_seconds must be ≤ 3.0 for FAST requirements"
            raise ValueError(msg)
        if latency_req == EnumLatencyRequirements.MODERATE and v > 5.0:
            msg = "max_latency_seconds must be ≤ 5.0 for MODERATE requirements"
            raise ValueError(
                msg,
            )
        if latency_req == EnumLatencyRequirements.RELAXED and v > 10.0:
            msg = "max_latency_seconds must be ≤ 10.0 for RELAXED requirements"
            raise ValueError(
                msg,
            )
        if latency_req == EnumLatencyRequirements.BACKGROUND and v > 30.0:
            msg = "max_latency_seconds must be ≤ 30.0 for BACKGROUND requirements"
            raise ValueError(
                msg,
            )

        return v

    @validator("min_accuracy_threshold")
    def validate_accuracy_consistency(self, v, values):
        """Ensure min_accuracy_threshold is consistent with accuracy_requirements enum."""
        if v is None:
            return v

        accuracy_req = values.get("accuracy_requirements")
        if accuracy_req == EnumAccuracyRequirements.LOW and v > 0.7:
            msg = "min_accuracy_threshold should be ≤ 0.7 for LOW requirements"
            raise ValueError(
                msg,
            )
        if accuracy_req == EnumAccuracyRequirements.VERY_HIGH and v < 0.95:
            msg = "min_accuracy_threshold should be ≥ 0.95 for VERY_HIGH requirements"
            raise ValueError(
                msg,
            )
        if accuracy_req == EnumAccuracyRequirements.CRITICAL and v < 0.99:
            msg = "min_accuracy_threshold should be ≥ 0.99 for CRITICAL requirements"
            raise ValueError(
                msg,
            )

        return v


class ModelAIRoutingResult(BaseModel):
    """
    Result of AI routing decision made by llm_005 system.

    Contains the routing decision, performance predictions,
    cost estimates, and confidence scoring.
    """

    # Routing decision
    selected_provider: str = Field(
        description="Selected provider name (e.g., 'ollama', 'openai')",
    )

    selected_model: str = Field(
        description="Selected model name (e.g., 'mistral', 'gpt-4')",
    )

    routing_reason: str = Field(
        description="Human-readable explanation for routing decision",
    )

    # Performance predictions
    predicted_latency: float | None = Field(
        default=None,
        description="Predicted response latency in seconds",
    )

    predicted_accuracy: float | None = Field(
        default=None,
        description="Predicted accuracy score (0.0-1.0)",
    )

    predicted_quality: float | None = Field(
        default=None,
        description="Predicted output quality score (0.0-1.0)",
    )

    # Cost estimation
    estimated_cost: float | None = Field(
        default=None,
        description="Estimated cost in USD for this request",
    )

    cost_breakdown: dict[str, float] | None = Field(
        default=None,
        description="Detailed cost breakdown by component",
    )

    # Routing confidence and alternatives
    confidence_score: float = Field(
        description="Confidence in routing decision (0.0-1.0)",
        ge=0.0,
        le=1.0,
    )

    alternative_options: list[dict[str, str | int | float | bool]] | None = Field(
        default=None,
        description="Alternative routing options considered",
    )

    # Capacity and load information
    provider_load: float | None = Field(
        default=None,
        description="Current load on selected provider (0.0-1.0)",
    )

    queue_position: int | None = Field(
        default=None,
        description="Position in provider queue (if applicable)",
    )

    # Routing metadata
    routing_timestamp: float = Field(
        description="Unix timestamp when routing decision was made",
    )

    routing_version: str = Field(
        default="1.0.0",
        description="Version of routing algorithm used",
    )

    routing_session_id: str | None = Field(
        default=None,
        description="Session ID for routing correlation",
    )


class ModelAIWorkflowContext(BaseModel):
    """
    Workflow execution context for AI routing decisions.

    Provides additional context to routing system for better
    decision making and optimization.
    """

    workflow_id: str = Field(description="Unique workflow execution identifier")

    workflow_type: str = Field(
        description="Type of workflow (e.g., 'document_regeneration', 'code_analysis')",
    )

    step_id: str = Field(description="Current workflow step identifier")

    step_type: str = Field(
        description="Type of workflow step (e.g., 'llm_inference', 'validation')",
    )

    # Execution context
    execution_environment: str = Field(
        default="production",
        description="Execution environment (production, staging, development)",
    )

    user_id: str | None = Field(
        default=None,
        description="User ID for personalized routing (if applicable)",
    )

    organization_id: str | None = Field(
        default=None,
        description="Organization ID for billing and quotas",
    )

    # Dependencies and relationships
    dependent_steps: list[str] | None = Field(
        default=None,
        description="Steps that depend on this routing decision",
    )

    input_dependencies: list[str] | None = Field(
        default=None,
        description="Previous steps this decision depends on",
    )

    # Resource context
    available_budget: float | None = Field(
        default=None,
        description="Available budget for this workflow execution",
    )

    deadline: float | None = Field(
        default=None,
        description="Unix timestamp deadline for workflow completion",
    )

    # Historical context
    similar_workflows: list[str] | None = Field(
        default=None,
        description="IDs of similar workflows for learning-based routing",
    )

    previous_routing_decisions: list[ModelAIRoutingResult] | None = Field(
        default=None,
        description="Previous routing decisions in this workflow",
    )

    # Quality and feedback context
    quality_feedback: dict[str, float] | None = Field(
        default=None,
        description="Quality feedback from previous similar workflows",
    )

    user_preferences: ModelAIRoutingPreferences | None = Field(
        default=None,
        description="User-specific routing preferences",
    )
