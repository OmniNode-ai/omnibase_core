"""
Memory metrics models for the OmniMemory analytics and ledger system.

These models define structures for tracking system effectiveness,
rule performance, token savings, and learning progress analytics.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class EnumMetricType(str, Enum):
    """Types of metrics tracked by the memory system."""

    TOKEN_USAGE = "token_usage"
    RULE_EFFECTIVENESS = "rule_effectiveness"
    CORRECTION_FREQUENCY = "correction_frequency"
    LEARNING_PROGRESS = "learning_progress"
    SYSTEM_PERFORMANCE = "system_performance"
    USER_SATISFACTION = "user_satisfaction"
    ERROR_PREVENTION = "error_prevention"


class EnumAggregationPeriod(str, Enum):
    """Time periods for metric aggregation."""

    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class EnumTrendDirection(str, Enum):
    """Direction of metric trends."""

    IMPROVING = "improving"
    DEGRADING = "degrading"
    STABLE = "stable"
    VOLATILE = "volatile"
    UNKNOWN = "unknown"


class ModelMemoryMetric(BaseModel):
    """Model for a single memory system metric."""

    metric_id: str = Field(description="Unique identifier for this metric")
    metric_name: str = Field(description="Human-readable name for the metric")
    metric_type: EnumMetricType = Field(description="Type of metric")

    # Metric value
    value: float = Field(description="Current value of the metric")
    unit: str = Field(description="Unit of measurement for the metric")

    # Metric metadata
    description: str = Field(description="Description of what this metric measures")
    calculation_method: str = Field(description="How this metric is calculated")

    # Time information
    measured_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this metric was measured",
    )
    period_start: datetime = Field(description="Start of the period this metric covers")
    period_end: datetime = Field(description="End of the period this metric covers")

    # Contextual information
    context: dict[str, str] = Field(
        default_factory=dict,
        description="Additional context for this metric",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Tags for categorizing this metric",
    )

    # Quality indicators
    confidence: float = Field(
        default=1.0,
        description="Confidence in this metric value (0.0-1.0)",
    )
    data_points: int = Field(
        description="Number of data points used to calculate this metric",
    )


class ModelTokenUsageMetrics(BaseModel):
    """Model for token usage and savings metrics."""

    metrics_id: str = Field(description="Unique identifier for these metrics")

    # Basic token metrics
    total_tokens_consumed: int = Field(
        description="Total tokens consumed in the period",
    )
    tokens_saved: int = Field(description="Tokens saved through context optimization")
    savings_percentage: float = Field(description="Percentage of tokens saved")

    # Context injection metrics
    context_tokens_injected: int = Field(
        description="Tokens used for context injection",
    )
    context_injection_efficiency: float = Field(
        description="Efficiency of context injection (value per token)",
    )

    # Optimization breakdown
    savings_by_compression: int = Field(
        default=0,
        description="Tokens saved through compression",
    )
    savings_by_filtering: int = Field(
        default=0,
        description="Tokens saved through irrelevant content filtering",
    )
    savings_by_caching: int = Field(
        default=0,
        description="Tokens saved through caching",
    )
    savings_by_deduplication: int = Field(
        default=0,
        description="Tokens saved through deduplication",
    )

    # Cost calculations
    estimated_cost_saved: float = Field(description="Estimated monetary cost saved")
    cost_per_token: float = Field(description="Cost per token used for calculations")

    # Trend analysis
    trend_direction: EnumTrendDirection = Field(
        description="Direction of token usage trend",
    )
    trend_strength: float = Field(description="Strength of the trend (0.0-1.0)")

    # Period information
    period_start: datetime = Field(description="Start of the measurement period")
    period_end: datetime = Field(description="End of the measurement period")

    # Metadata
    calculated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When these metrics were calculated",
    )


class ModelRuleEffectivenessMetrics(BaseModel):
    """Model for tracking the effectiveness of context rules."""

    metrics_id: str = Field(description="Unique identifier for these metrics")

    # Rule performance
    total_rules_evaluated: int = Field(
        description="Total number of rules evaluated in the period",
    )
    rules_triggered: int = Field(description="Number of rules that were triggered")
    successful_applications: int = Field(
        description="Number of successful rule applications",
    )

    # Success rates
    trigger_rate: float = Field(
        description="Percentage of evaluations that triggered rules",
    )
    success_rate: float = Field(
        description="Percentage of triggered rules that were successful",
    )
    overall_effectiveness: float = Field(
        description="Overall effectiveness score for the rule system",
    )

    # Rule categories
    typing_rules_effectiveness: float = Field(
        description="Effectiveness of typing correction rules",
    )
    context_rules_effectiveness: float = Field(
        description="Effectiveness of context injection rules",
    )
    prevention_rules_effectiveness: float = Field(
        description="Effectiveness of error prevention rules",
    )

    # Performance metrics
    average_execution_time_ms: float = Field(
        description="Average execution time for rule evaluation",
    )
    total_execution_time_ms: float = Field(
        description="Total execution time for all rule evaluations",
    )

    # Quality impact
    errors_prevented: int = Field(description="Number of errors prevented by rules")
    corrections_applied: int = Field(
        description="Number of corrections automatically applied",
    )
    developer_interventions_reduced: int = Field(
        description="Number of developer interventions avoided",
    )

    # Rule evolution
    new_rules_learned: int = Field(
        description="Number of new rules learned in the period",
    )
    rules_modified: int = Field(description="Number of existing rules modified")
    rules_deprecated: int = Field(description="Number of rules deprecated")

    # Period information
    period_start: datetime = Field(description="Start of the measurement period")
    period_end: datetime = Field(description="End of the measurement period")

    # Metadata
    calculated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When these metrics were calculated",
    )


class ModelLearningProgressMetrics(BaseModel):
    """Model for tracking learning system progress and effectiveness."""

    metrics_id: str = Field(description="Unique identifier for these metrics")

    # Learning volume
    observations_captured: int = Field(
        description="Number of observations captured in the period",
    )
    patterns_learned: int = Field(description="Number of new patterns learned")
    patterns_reinforced: int = Field(
        description="Number of existing patterns reinforced",
    )

    # Learning quality
    average_pattern_confidence: float = Field(
        description="Average confidence score of learned patterns",
    )
    high_confidence_patterns: int = Field(
        description="Number of patterns with high confidence",
    )
    patterns_promoted_to_rules: int = Field(
        description="Number of patterns promoted to formal rules",
    )

    # Learning efficiency
    learning_velocity: float = Field(
        description="Rate of learning new valuable patterns",
    )
    pattern_diversity_score: float = Field(description="Diversity of patterns learned")
    learning_efficiency_score: float = Field(
        description="Overall efficiency of the learning process",
    )

    # Knowledge base growth
    knowledge_base_size: int = Field(description="Current size of the knowledge base")
    knowledge_growth_rate: float = Field(description="Rate of knowledge base growth")
    knowledge_quality_score: float = Field(
        description="Quality score of the knowledge base",
    )

    # Validation and verification
    patterns_validated: int = Field(
        description="Number of patterns that underwent validation",
    )
    validation_success_rate: float = Field(
        description="Success rate of pattern validation",
    )
    false_positives: int = Field(
        description="Number of false positive patterns identified",
    )

    # Learning insights
    actionable_insights_generated: int = Field(
        description="Number of actionable insights generated",
    )
    insights_acted_upon: int = Field(
        description="Number of insights that were acted upon",
    )
    insight_value_score: float = Field(description="Value score of generated insights")

    # Period information
    period_start: datetime = Field(description="Start of the measurement period")
    period_end: datetime = Field(description="End of the measurement period")

    # Metadata
    calculated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When these metrics were calculated",
    )


class ModelSystemPerformanceMetrics(BaseModel):
    """Model for tracking overall system performance metrics."""

    metrics_id: str = Field(description="Unique identifier for these metrics")

    # Response times
    average_response_time_ms: float = Field(
        description="Average response time for memory operations",
    )
    median_response_time_ms: float = Field(
        description="Median response time for memory operations",
    )
    p99_response_time_ms: float = Field(description="99th percentile response time")

    # Throughput
    operations_per_second: float = Field(
        description="Number of memory operations per second",
    )
    contexts_injected_per_hour: int = Field(
        description="Number of contexts injected per hour",
    )
    rules_evaluated_per_second: float = Field(
        description="Number of rules evaluated per second",
    )

    # Resource utilization
    cpu_usage_percentage: float = Field(description="Average CPU usage percentage")
    memory_usage_mb: float = Field(description="Average memory usage in megabytes")
    storage_usage_gb: float = Field(description="Storage usage in gigabytes")

    # Error rates
    error_rate: float = Field(
        description="Percentage of operations that resulted in errors",
    )
    timeout_rate: float = Field(description="Percentage of operations that timed out")
    retry_rate: float = Field(
        description="Percentage of operations that required retries",
    )

    # Availability and reliability
    uptime_percentage: float = Field(description="System uptime percentage")
    availability_score: float = Field(description="Overall availability score")

    # Scalability metrics
    concurrent_operations: int = Field(
        description="Number of concurrent operations supported",
    )
    queue_depth: int = Field(description="Average depth of operation queues")

    # Period information
    period_start: datetime = Field(description="Start of the measurement period")
    period_end: datetime = Field(description="End of the measurement period")

    # Metadata
    calculated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When these metrics were calculated",
    )


class ModelMemoryLedgerEntry(BaseModel):
    """Model for a single entry in the memory system ledger."""

    entry_id: str = Field(description="Unique identifier for this ledger entry")

    # Operation details
    operation_type: str = Field(description="Type of operation performed")
    operation_description: str = Field(description="Description of the operation")

    # Context information
    session_id: str | None = Field(
        default=None,
        description="Session ID associated with this operation",
    )
    user_id: str | None = Field(
        default=None,
        description="User ID associated with this operation",
    )

    # Metrics captured
    tokens_used: int = Field(
        default=0,
        description="Number of tokens used in this operation",
    )
    tokens_saved: int = Field(
        default=0,
        description="Number of tokens saved by this operation",
    )
    execution_time_ms: float = Field(description="Execution time for this operation")

    # Outcome information
    success: bool = Field(description="Whether the operation was successful")
    error_message: str | None = Field(
        default=None,
        description="Error message if operation failed",
    )

    # Impact assessment
    quality_improvement: float | None = Field(
        default=None,
        description="Quality improvement score for this operation",
    )
    errors_prevented: int = Field(
        default=0,
        description="Number of errors prevented by this operation",
    )

    # Metadata
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this operation occurred",
    )
    component: str = Field(description="System component that performed this operation")

    # Additional context
    additional_data: dict[str, str] = Field(
        default_factory=dict,
        description="Additional contextual data for this entry",
    )


class ModelMemoryAnalyticsReport(BaseModel):
    """Model for comprehensive analytics reports on memory system performance."""

    report_id: str = Field(description="Unique identifier for this report")
    report_name: str = Field(description="Human-readable name for the report")

    # Report scope
    period_start: datetime = Field(description="Start of the reporting period")
    period_end: datetime = Field(description="End of the reporting period")
    aggregation_period: EnumAggregationPeriod = Field(
        description="Aggregation period for the report",
    )

    # Key metrics
    token_metrics: ModelTokenUsageMetrics = Field(
        description="Token usage and savings metrics",
    )
    rule_metrics: ModelRuleEffectivenessMetrics = Field(
        description="Rule effectiveness metrics",
    )
    learning_metrics: ModelLearningProgressMetrics = Field(
        description="Learning progress metrics",
    )
    performance_metrics: ModelSystemPerformanceMetrics = Field(
        description="System performance metrics",
    )

    # Summary statistics
    total_operations: int = Field(
        description="Total number of operations in the reporting period",
    )
    successful_operations: int = Field(description="Number of successful operations")
    overall_success_rate: float = Field(description="Overall success rate percentage")

    # Trends and insights
    key_trends: list[str] = Field(
        description="Key trends identified in the reporting period",
    )
    insights: list[str] = Field(description="Insights derived from the data")
    recommendations: list[str] = Field(
        description="Recommendations based on the analysis",
    )

    # Comparative analysis
    period_over_period_change: float = Field(
        description="Percentage change compared to previous period",
    )
    performance_vs_baseline: float = Field(
        description="Performance compared to baseline metrics",
    )

    # Report metadata
    generated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this report was generated",
    )
    generated_by: str = Field(description="System or user that generated this report")
    report_version: str = Field(
        default="1.0",
        description="Version of the report format",
    )
