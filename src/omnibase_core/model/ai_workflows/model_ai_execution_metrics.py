"""
AI Execution Metrics Models

Comprehensive metrics collection for AI model executions, integrating with
llm_005 metric-aware routing and providing real-time performance monitoring.
"""

import time
from enum import Enum

from pydantic import BaseModel, Field, validator


class EnumMetricType(Enum):
    """Types of metrics collected during AI execution."""

    PERFORMANCE = "performance"  # Speed, latency, throughput
    QUALITY = "quality"  # Accuracy, coherence, relevance
    COST = "cost"  # Infrastructure and API costs
    RESOURCE = "resource"  # CPU, GPU, memory usage
    BUSINESS = "business"  # User satisfaction, task completion
    SECURITY = "security"  # Privacy, compliance, safety


class EnumMetricUnit(Enum):
    """Units for metric measurements."""

    SECONDS = "seconds"
    MILLISECONDS = "milliseconds"
    PERCENTAGE = "percentage"
    SCORE_0_TO_1 = "score_0_to_1"
    SCORE_0_TO_100 = "score_0_to_100"
    USD = "usd"
    TOKENS_PER_SECOND = "tokens_per_second"
    BYTES = "bytes"
    MEGABYTES = "megabytes"
    COUNT = "count"


class ModelMetricValue(BaseModel):
    """Individual metric value with metadata."""

    name: str = Field(
        description="Metric name (e.g., 'response_latency', 'accuracy_score')",
    )

    value: float | int | str | bool = Field(description="Metric value")

    unit: EnumMetricUnit = Field(description="Unit of measurement")

    type: EnumMetricType = Field(description="Category of metric")

    timestamp: float = Field(
        default_factory=time.time,
        description="Unix timestamp when metric was recorded",
    )

    confidence: float | None = Field(
        default=None,
        description="Confidence in metric accuracy (0.0-1.0)",
        ge=0.0,
        le=1.0,
    )

    metadata: dict[str, str | int | float | bool] | None = Field(
        default=None,
        description="Additional metadata about the metric",
    )


class ModelAIExecutionMetrics(BaseModel):
    """
    Comprehensive metrics for a single AI model execution.

    Collects performance, quality, cost, and resource metrics
    for every LLM call in AI workflows.
    """

    # Execution identification
    execution_id: str = Field(description="Unique identifier for this execution")

    workflow_id: str | None = Field(
        default=None,
        description="Parent workflow ID if part of a larger workflow",
    )

    model_name: str = Field(
        description="Name of the AI model used (e.g., 'mistral', 'gpt-4')",
    )

    provider: str = Field(
        description="Provider used (e.g., 'ollama', 'openai', 'anthropic')",
    )

    machine_id: str = Field(description="Machine that executed the model")

    # Timing metrics
    start_time: float = Field(description="Unix timestamp when execution started")

    end_time: float | None = Field(
        default=None,
        description="Unix timestamp when execution completed",
    )

    total_duration: float | None = Field(
        default=None,
        description="Total execution duration in seconds",
    )

    # Performance metrics
    response_latency: float | None = Field(
        default=None,
        description="Time to first token in seconds",
    )

    tokens_per_second: float | None = Field(
        default=None,
        description="Token generation rate",
    )

    input_tokens: int | None = Field(
        default=None,
        description="Number of input tokens processed",
    )

    output_tokens: int | None = Field(
        default=None,
        description="Number of output tokens generated",
    )

    # Quality metrics
    accuracy_score: float | None = Field(
        default=None,
        description="Accuracy score (0.0-1.0) if measurable",
        ge=0.0,
        le=1.0,
    )

    coherence_score: float | None = Field(
        default=None,
        description="Output coherence score (0.0-1.0)",
        ge=0.0,
        le=1.0,
    )

    relevance_score: float | None = Field(
        default=None,
        description="Response relevance score (0.0-1.0)",
        ge=0.0,
        le=1.0,
    )

    completeness_score: float | None = Field(
        default=None,
        description="Response completeness score (0.0-1.0)",
        ge=0.0,
        le=1.0,
    )

    confidence_score: float | None = Field(
        default=None,
        description="Model's confidence in its response (0.0-1.0)",
        ge=0.0,
        le=1.0,
    )

    # Cost metrics
    estimated_cost: float | None = Field(
        default=None,
        description="Estimated execution cost in USD",
    )

    api_cost: float | None = Field(
        default=None,
        description="Direct API cost (for cloud providers)",
    )

    infrastructure_cost: float | None = Field(
        default=None,
        description="Infrastructure cost (for local models)",
    )

    cost_per_token: float | None = Field(
        default=None,
        description="Cost per token in USD",
    )

    # Resource usage metrics
    cpu_usage_percent: float | None = Field(
        default=None,
        description="Average CPU usage during execution",
        ge=0.0,
        le=100.0,
    )

    memory_usage_mb: float | None = Field(
        default=None,
        description="Peak memory usage in MB",
    )

    gpu_usage_percent: float | None = Field(
        default=None,
        description="Average GPU usage during execution",
        ge=0.0,
        le=100.0,
    )

    gpu_memory_usage_mb: float | None = Field(
        default=None,
        description="Peak GPU memory usage in MB",
    )

    network_bytes_sent: int | None = Field(
        default=None,
        description="Network bytes sent for remote calls",
    )

    network_bytes_received: int | None = Field(
        default=None,
        description="Network bytes received for remote calls",
    )

    # Error and retry information
    success: bool = Field(
        default=True,
        description="Whether execution completed successfully",
    )

    error_message: str | None = Field(
        default=None,
        description="Error message if execution failed",
    )

    retry_count: int = Field(default=0, description="Number of retries attempted")

    # Additional metrics
    custom_metrics: list[ModelMetricValue] | None = Field(
        default=None,
        description="Custom metrics specific to the task or model",
    )

    routing_decision_reason: str | None = Field(
        default=None,
        description="Reason for model/provider routing decision",
    )

    # Context information
    task_type: str | None = Field(
        default=None,
        description="Type of task (e.g., 'code_generation', 'text_analysis')",
    )

    prompt_template: str | None = Field(
        default=None,
        description="Template used for prompt generation",
    )

    temperature: float | None = Field(
        default=None,
        description="Model temperature setting",
    )

    max_tokens: int | None = Field(
        default=None,
        description="Maximum tokens requested",
    )

    # Validation and derived metrics
    @validator("total_duration", always=True)
    def calculate_total_duration(self, v, values):
        """Calculate total duration if not provided."""
        if v is not None:
            return v

        start_time = values.get("start_time")
        end_time = values.get("end_time")

        if start_time and end_time:
            return end_time - start_time

        return None

    @validator("cost_per_token", always=True)
    def calculate_cost_per_token(self, v, values):
        """Calculate cost per token if not provided."""
        if v is not None:
            return v

        estimated_cost = values.get("estimated_cost")
        input_tokens = values.get("input_tokens")
        output_tokens = values.get("output_tokens")
        total_tokens = (input_tokens or 0) + (output_tokens or 0)

        if estimated_cost and total_tokens > 0:
            return estimated_cost / total_tokens

        return None


class ModelAIWorkflowMetrics(BaseModel):
    """
    Aggregate metrics for an entire AI workflow execution.

    Combines metrics from multiple model executions and provides
    workflow-level performance, cost, and quality insights.
    """

    workflow_id: str = Field(description="Unique identifier for the workflow execution")

    workflow_type: str = Field(
        description="Type of workflow (e.g., 'document_regeneration')",
    )

    start_time: float = Field(description="Unix timestamp when workflow started")

    end_time: float | None = Field(
        default=None,
        description="Unix timestamp when workflow completed",
    )

    total_duration: float | None = Field(
        default=None,
        description="Total workflow duration in seconds",
    )

    # Execution metrics
    executions: list[ModelAIExecutionMetrics] = Field(
        default_factory=list,
        description="Metrics for individual AI model executions",
    )

    total_executions: int = Field(
        default=0,
        description="Total number of AI model executions in workflow",
    )

    successful_executions: int = Field(
        default=0,
        description="Number of successful AI model executions",
    )

    failed_executions: int = Field(
        default=0,
        description="Number of failed AI model executions",
    )

    # Aggregate performance metrics
    average_latency: float | None = Field(
        default=None,
        description="Average response latency across all executions",
    )

    total_tokens_processed: int | None = Field(
        default=None,
        description="Total tokens processed across all executions",
    )

    average_tokens_per_second: float | None = Field(
        default=None,
        description="Average token processing rate",
    )

    # Aggregate quality metrics
    average_accuracy: float | None = Field(
        default=None,
        description="Average accuracy score across executions",
    )

    average_quality_score: float | None = Field(
        default=None,
        description="Average combined quality score",
    )

    quality_variance: float | None = Field(
        default=None,
        description="Variance in quality scores across executions",
    )

    # Aggregate cost metrics
    total_cost: float | None = Field(
        default=None,
        description="Total workflow execution cost in USD",
    )

    cost_breakdown: dict[str, float] | None = Field(
        default=None,
        description="Cost breakdown by provider/model",
    )

    cost_efficiency: float | None = Field(
        default=None,
        description="Cost efficiency metric (quality/cost ratio)",
    )

    # Resource utilization
    peak_cpu_usage: float | None = Field(
        default=None,
        description="Peak CPU usage during workflow",
    )

    peak_memory_usage: float | None = Field(
        default=None,
        description="Peak memory usage during workflow",
    )

    total_network_bytes: int | None = Field(
        default=None,
        description="Total network bytes transferred",
    )

    # Workflow outcome
    success: bool = Field(
        default=True,
        description="Whether workflow completed successfully",
    )

    quality_threshold_met: bool | None = Field(
        default=None,
        description="Whether workflow met quality thresholds",
    )

    final_output_quality: float | None = Field(
        default=None,
        description="Quality score of final workflow output",
    )

    # Optimization insights
    optimization_opportunities: list[str] | None = Field(
        default=None,
        description="Identified opportunities for optimization",
    )

    model_selection_effectiveness: float | None = Field(
        default=None,
        description="Effectiveness of routing decisions (0.0-1.0)",
    )

    # Context and metadata
    user_id: str | None = Field(
        default=None,
        description="User who initiated the workflow",
    )

    workflow_config: dict[str, str | int | float | bool] | None = Field(
        default=None,
        description="Configuration used for workflow execution",
    )

    environment: str = Field(default="production", description="Execution environment")


class ModelMetricsCollectionConfig(BaseModel):
    """Configuration for metrics collection in AI workflows."""

    # Collection settings
    enable_performance_metrics: bool = Field(
        default=True,
        description="Whether to collect performance metrics",
    )

    enable_quality_metrics: bool = Field(
        default=True,
        description="Whether to collect quality metrics",
    )

    enable_cost_metrics: bool = Field(
        default=True,
        description="Whether to collect cost metrics",
    )

    enable_resource_metrics: bool = Field(
        default=True,
        description="Whether to collect resource usage metrics",
    )

    # Quality assessment settings
    quality_validation_enabled: bool = Field(
        default=False,
        description="Whether to run quality validation on outputs",
    )

    quality_validation_sample_rate: float = Field(
        default=0.1,
        description="Fraction of outputs to validate (0.0-1.0)",
        ge=0.0,
        le=1.0,
    )

    # Storage and retention
    store_detailed_metrics: bool = Field(
        default=True,
        description="Whether to store detailed execution metrics",
    )

    metrics_retention_days: int = Field(
        default=30,
        description="Number of days to retain detailed metrics",
        gt=0,
    )

    aggregate_metrics_retention_days: int = Field(
        default=365,
        description="Number of days to retain aggregate metrics",
        gt=0,
    )

    # Export and integration
    export_to_prometheus: bool = Field(
        default=True,
        description="Whether to export metrics to Prometheus",
    )

    export_to_event_bus: bool = Field(
        default=True,
        description="Whether to publish metrics to event bus",
    )

    real_time_monitoring: bool = Field(
        default=True,
        description="Whether to enable real-time metrics monitoring",
    )

    # Alert thresholds
    latency_alert_threshold: float | None = Field(
        default=None,
        description="Latency threshold for alerts (seconds)",
    )

    quality_alert_threshold: float | None = Field(
        default=None,
        description="Quality threshold for alerts (0.0-1.0)",
    )

    cost_alert_threshold: float | None = Field(
        default=None,
        description="Cost threshold for alerts (USD)",
    )

    error_rate_alert_threshold: float | None = Field(
        default=0.05,
        description="Error rate threshold for alerts (0.0-1.0)",
    )


class ModelMetricsAggregator(BaseModel):
    """Aggregates and analyzes metrics from AI executions."""

    @staticmethod
    def aggregate_workflow_metrics(
        executions: list[ModelAIExecutionMetrics],
    ) -> ModelAIWorkflowMetrics:
        """Aggregate individual execution metrics into workflow metrics."""
        if not executions:
            msg = "Cannot aggregate empty executions list"
            raise ValueError(msg)

        # Basic counts
        total_executions = len(executions)
        successful_executions = sum(1 for e in executions if e.success)
        failed_executions = total_executions - successful_executions

        # Performance aggregations
        latencies = [
            e.response_latency for e in executions if e.response_latency is not None
        ]
        average_latency = sum(latencies) / len(latencies) if latencies else None

        total_tokens = sum(
            (e.input_tokens or 0) + (e.output_tokens or 0) for e in executions
        )

        durations = [
            e.total_duration for e in executions if e.total_duration is not None
        ]
        total_duration = sum(durations) if durations else None
        average_tokens_per_second = (
            total_tokens / total_duration
            if total_duration and total_duration > 0
            else None
        )

        # Quality aggregations
        accuracy_scores = [
            e.accuracy_score for e in executions if e.accuracy_score is not None
        ]
        average_accuracy = (
            sum(accuracy_scores) / len(accuracy_scores) if accuracy_scores else None
        )

        # Cost aggregations
        costs = [e.estimated_cost for e in executions if e.estimated_cost is not None]
        total_cost = sum(costs) if costs else None

        # Create workflow metrics
        return ModelAIWorkflowMetrics(
            workflow_id=executions[0].workflow_id or "unknown",
            workflow_type="aggregated",
            start_time=min(e.start_time for e in executions),
            end_time=max(e.end_time for e in executions if e.end_time is not None)
            or None,
            total_duration=total_duration,
            executions=executions,
            total_executions=total_executions,
            successful_executions=successful_executions,
            failed_executions=failed_executions,
            average_latency=average_latency,
            total_tokens_processed=total_tokens,
            average_tokens_per_second=average_tokens_per_second,
            average_accuracy=average_accuracy,
            total_cost=total_cost,
            success=failed_executions == 0,
        )
