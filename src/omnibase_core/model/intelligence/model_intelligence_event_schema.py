"""
ONEX Intelligence Event Schema - Standardized event schemas for intelligence coordination.

This module provides standardized event schemas for intelligence events, correlation,
and learning workflow patterns across all intelligence components.

Key Features:
- Unified event envelope for all intelligence communications
- Standardized correlation and tracing schema
- Learning workflow event patterns
- Performance metrics and analytics events
- Cross-component learning coordination schemas
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Union
from uuid import uuid4

from pydantic import BaseModel, Field

from omnibase_core.intelligence.models.model_context_learning import (
    EnumLearningEventType, ModelLearnedRule, ModelLearningEvent,
    ModelLearningPattern)
from omnibase_core.model.intelligence.model_event_payload_data import (
    ModelBatchProcessingMetadata, ModelComponentContext, ModelDebugContext,
    ModelErrorContext, ModelEventMetadata, ModelEventPayloadData,
    ModelOperationContext, ModelSuccessCriteria, ModelValidationResult,
    ModelWorkflowContextData)


class EnumIntelligencePriority(str, Enum):
    """Priority levels for intelligence events."""

    CRITICAL = "critical"  # <50ms processing requirement
    HIGH = "high"  # <100ms processing requirement
    MEDIUM = "medium"  # <200ms processing requirement
    LOW = "low"  # <500ms processing requirement


class EnumIntelligenceCategory(str, Enum):
    """Categories of intelligence events for routing and processing."""

    LEARNING = "learning"  # Learning events and pattern detection
    CONTEXT = "context"  # Context rules and injection events
    METADATA = "metadata"  # Metadata pipeline and enrichment events
    WORKFLOW = "workflow"  # Multi-component workflow coordination
    ANALYTICS = "analytics"  # Performance and analytics events
    HEALTH = "health"  # Health monitoring and diagnostics
    SECURITY = "security"  # Security and audit events


class EnumWorkflowStage(str, Enum):
    """Stages of multi-component learning workflows."""

    INITIATED = "initiated"  # Workflow started
    PATTERN_ANALYSIS = "pattern_analysis"  # Analyzing patterns
    RULE_GENERATION = "rule_generation"  # Generating new rules
    VALIDATION = "validation"  # Validating in shadow mode
    PROMOTION = "promotion"  # Promoting to production
    MONITORING = "monitoring"  # Ongoing monitoring
    COMPLETION = "completion"  # Workflow completed
    FAILED = "failed"  # Workflow failed


class ModelCorrelationContext(BaseModel):
    """Standardized correlation context for event tracing."""

    correlation_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Primary correlation identifier",
    )
    parent_correlation_id: Optional[str] = Field(
        default=None, description="Parent correlation for nested operations"
    )
    root_correlation_id: Optional[str] = Field(
        default=None, description="Root correlation for workflow chains"
    )
    traceparent: Optional[str] = Field(
        default=None, description="W3C trace context for distributed tracing"
    )
    session_id: Optional[str] = Field(
        default=None, description="Session identifier for user interactions"
    )
    operation_id: Optional[str] = Field(
        default=None, description="Specific operation identifier"
    )


class ModelEventSource(BaseModel):
    """Standardized event source information."""

    component_id: str = Field(description="Source component identifier")
    service_name: str = Field(
        description="Service name (langextract, context-rules, etc.)"
    )
    version: str = Field(default="1.0.0", description="Component version")
    instance_id: Optional[str] = Field(
        default=None, description="Specific instance identifier for load balancing"
    )
    node_id: Optional[str] = Field(
        default=None, description="Physical or virtual node identifier"
    )


class ModelEventTarget(BaseModel):
    """Standardized event target specification."""

    target_components: List[str] = Field(
        default_factory=list, description="Specific target component IDs"
    )
    target_categories: List[EnumIntelligenceCategory] = Field(
        default_factory=list, description="Target component categories"
    )
    broadcast_to_all: bool = Field(
        default=False, description="Whether to broadcast to all registered components"
    )
    exclude_source: bool = Field(
        default=True, description="Whether to exclude source component from targets"
    )


class ModelPerformanceMetrics(BaseModel):
    """Performance metrics for intelligence events."""

    processing_time_ms: float = Field(
        ge=0.0, description="Total processing time in milliseconds"
    )
    queue_time_ms: Optional[float] = Field(
        default=None, description="Time spent in queue before processing"
    )
    distribution_time_ms: Optional[float] = Field(
        default=None, description="Time spent distributing to components"
    )
    memory_usage_bytes: Optional[int] = Field(
        default=None, description="Memory usage for processing this event"
    )
    cpu_usage_percent: Optional[float] = Field(
        default=None, description="CPU usage percentage during processing"
    )


class ModelLearningWorkflowState(BaseModel):
    """State information for learning workflows."""

    workflow_id: str = Field(description="Unique workflow identifier")
    workflow_type: str = Field(description="Type of learning workflow")
    current_stage: EnumWorkflowStage = Field(description="Current workflow stage")
    participants: List[str] = Field(
        default_factory=list, description="Component IDs participating in workflow"
    )
    learned_patterns: List[str] = Field(
        default_factory=list, description="Pattern IDs discovered in workflow"
    )
    generated_rules: List[str] = Field(
        default_factory=list, description="Rule IDs generated in workflow"
    )
    validation_results: Dict[str, ModelValidationResult] = Field(
        default_factory=dict, description="Validation results for generated rules"
    )
    context_data: ModelWorkflowContextData = Field(
        default_factory=ModelWorkflowContextData,
        description="Workflow-specific context data",
    )
    started_at: datetime = Field(description="Workflow start time")
    updated_at: datetime = Field(description="Last update time")
    expires_at: Optional[datetime] = Field(
        default=None, description="Workflow expiration time"
    )


class ModelIntelligenceEventEnvelope(BaseModel):
    """
    Unified intelligence event envelope for all intelligence communications.

    This envelope provides standardized structure for all intelligence events,
    ensuring consistent correlation, tracing, and processing across components.
    """

    # Event identification
    event_id: str = Field(
        default_factory=lambda: str(uuid4()), description="Unique event identifier"
    )
    event_type: Union[EnumLearningEventType, str] = Field(
        description="Type of intelligence event"
    )
    event_category: EnumIntelligenceCategory = Field(
        description="Event category for routing"
    )

    # Correlation and tracing
    correlation: ModelCorrelationContext = Field(
        default_factory=ModelCorrelationContext,
        description="Correlation and tracing context",
    )

    # Source and target information
    source: ModelEventSource = Field(description="Event source information")
    target: ModelEventTarget = Field(
        default_factory=ModelEventTarget, description="Event target specification"
    )

    # Event properties
    priority: EnumIntelligencePriority = Field(
        default=EnumIntelligencePriority.MEDIUM, description="Processing priority"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Event creation timestamp"
    )
    expires_at: Optional[datetime] = Field(
        default=None, description="Event expiration time"
    )

    # Event payload
    payload: ModelEventPayloadData = Field(
        default_factory=ModelEventPayloadData, description="Event-specific payload data"
    )
    metadata: ModelEventMetadata = Field(
        default_factory=ModelEventMetadata,
        description="Additional metadata and context",
    )

    # Performance tracking
    performance: Optional[ModelPerformanceMetrics] = Field(
        default=None, description="Performance metrics for this event"
    )

    # Learning workflow context
    workflow_state: Optional[ModelLearningWorkflowState] = Field(
        default=None, description="Learning workflow state if applicable"
    )

    # Error and debugging context
    error_context: Optional[ModelErrorContext] = Field(
        default=None, description="Error context for failed operations"
    )
    debug_context: Optional[ModelDebugContext] = Field(
        default=None, description="Debug context for troubleshooting"
    )


class ModelIntelligenceEventBatch(BaseModel):
    """Batch container for multiple intelligence events."""

    batch_id: str = Field(
        default_factory=lambda: str(uuid4()), description="Unique batch identifier"
    )
    events: List[ModelIntelligenceEventEnvelope] = Field(
        description="Events in this batch"
    )
    batch_metadata: ModelBatchProcessingMetadata = Field(
        default_factory=ModelBatchProcessingMetadata, description="Batch-level metadata"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Batch creation timestamp"
    )
    processing_hints: ModelBatchProcessingMetadata = Field(
        default_factory=ModelBatchProcessingMetadata,
        description="Hints for batch processing optimization",
    )


class ModelEventProcessingResult(BaseModel):
    """Result of processing an intelligence event."""

    event_id: str = Field(description="Processed event ID")
    processing_status: str = Field(description="success, partial_success, failed")
    components_reached: List[str] = Field(
        default_factory=list, description="Components that successfully received event"
    )
    components_failed: List[str] = Field(
        default_factory=list, description="Components that failed to receive event"
    )
    error_details: Optional[Dict[str, str]] = Field(
        default=None, description="Error details for failed components"
    )
    performance_metrics: Optional[ModelPerformanceMetrics] = Field(
        default=None, description="Processing performance metrics"
    )
    processed_at: datetime = Field(
        default_factory=datetime.utcnow, description="Processing completion time"
    )


class ModelIntelligenceCoordinationSchema(BaseModel):
    """Schema for intelligence coordination operations."""

    operation_type: str = Field(description="Type of coordination operation")
    coordinator_id: str = Field(description="Coordinator instance identifier")
    operation_context: ModelOperationContext = Field(
        default_factory=ModelOperationContext,
        description="Context for coordination operation",
    )
    expected_participants: List[str] = Field(
        description="Expected participating components"
    )
    coordination_timeout_seconds: float = Field(
        default=30.0, description="Timeout for coordination completion"
    )
    success_criteria: ModelSuccessCriteria = Field(
        default_factory=ModelSuccessCriteria,
        description="Criteria for successful coordination",
    )


class ModelAnalyticsEventSchema(BaseModel):
    """Schema for intelligence analytics and monitoring events."""

    metric_name: str = Field(description="Name of the metric being reported")
    metric_value: Union[int, float, str, bool] = Field(description="Metric value")
    metric_type: str = Field(description="counter, gauge, histogram, summary")
    metric_tags: Dict[str, str] = Field(
        default_factory=dict, description="Tags for metric categorization"
    )
    metric_timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Metric measurement timestamp"
    )
    aggregation_period: Optional[str] = Field(
        default=None, description="Period for metric aggregation (1m, 5m, 1h, etc.)"
    )
    component_context: ModelComponentContext = Field(
        default_factory=ModelComponentContext,
        description="Context about the reporting component",
    )


# Factory functions for common event types


def create_learning_event(
    event_type: EnumLearningEventType,
    source_component: str,
    payload: ModelEventPayloadData,
    priority: EnumIntelligencePriority = EnumIntelligencePriority.MEDIUM,
    correlation_id: Optional[str] = None,
) -> ModelIntelligenceEventEnvelope:
    """Factory function to create learning intelligence events."""

    correlation_context = ModelCorrelationContext()
    if correlation_id:
        correlation_context.correlation_id = correlation_id

    source_info = ModelEventSource(
        component_id=source_component,
        service_name=(
            source_component.split("-")[0]
            if "-" in source_component
            else source_component
        ),
    )

    return ModelIntelligenceEventEnvelope(
        event_type=event_type,
        event_category=EnumIntelligenceCategory.LEARNING,
        correlation=correlation_context,
        source=source_info,
        priority=priority,
        payload=payload,
    )


def create_workflow_event(
    workflow_id: str,
    workflow_type: str,
    stage: EnumWorkflowStage,
    source_component: str,
    workflow_context: ModelWorkflowContextData,
    participants: Optional[List[str]] = None,
) -> ModelIntelligenceEventEnvelope:
    """Factory function to create workflow coordination events."""

    workflow_state = ModelLearningWorkflowState(
        workflow_id=workflow_id,
        workflow_type=workflow_type,
        current_stage=stage,
        participants=participants or [],
        context_data=workflow_context,
        started_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    source_info = ModelEventSource(
        component_id=source_component, service_name="workflow-coordinator"
    )

    return ModelIntelligenceEventEnvelope(
        event_type="workflow_stage_change",
        event_category=EnumIntelligenceCategory.WORKFLOW,
        source=source_info,
        priority=EnumIntelligencePriority.HIGH,
        payload=ModelEventPayloadData(
            description=f"Workflow {workflow_type} stage change to {stage}",
            operation="workflow_stage_change",
            status=str(stage),
            affected_components=participants or [],
        ),
        workflow_state=workflow_state,
    )


def create_analytics_event(
    metric_name: str,
    metric_value: Union[int, float, str, bool],
    source_component: str,
    metric_type: str = "gauge",
    tags: Optional[Dict[str, str]] = None,
) -> ModelIntelligenceEventEnvelope:
    """Factory function to create analytics events."""

    analytics_schema = ModelAnalyticsEventSchema(
        metric_name=metric_name,
        metric_value=metric_value,
        metric_type=metric_type,
        metric_tags=tags or {},
    )

    source_info = ModelEventSource(
        component_id=source_component,
        service_name=(
            source_component.split("-")[0]
            if "-" in source_component
            else source_component
        ),
    )

    # Create typed payload for analytics event
    analytics_payload = ModelEventPayloadData(
        description=f"Analytics metric: {metric_name}",
        category="analytics",
        operation="metric_report",
    )

    return ModelIntelligenceEventEnvelope(
        event_type="analytics_metric",
        event_category=EnumIntelligenceCategory.ANALYTICS,
        source=source_info,
        priority=EnumIntelligencePriority.LOW,
        payload=analytics_payload,
        metadata=ModelEventMetadata(
            source_type="analytics", tags=["metric", "analytics", metric_type]
        ),
    )


def create_error_event(
    error_context: ModelErrorContext,
    source_component: str,
    correlation_id: Optional[str] = None,
    priority: EnumIntelligencePriority = EnumIntelligencePriority.HIGH,
) -> ModelIntelligenceEventEnvelope:
    """Factory function to create error intelligence events."""

    correlation_context = ModelCorrelationContext()
    if correlation_id:
        correlation_context.correlation_id = correlation_id

    source_info = ModelEventSource(
        component_id=source_component,
        service_name=(
            source_component.split("-")[0]
            if "-" in source_component
            else source_component
        ),
    )

    # Create error-specific payload
    error_payload = ModelEventPayloadData(
        description=f"Error in {error_context.operation_name}: {error_context.error_message}",
        category="error",
        operation=error_context.operation_name,
        status="error",
        affected_components=[error_context.component_id],
    )

    return ModelIntelligenceEventEnvelope(
        event_type="error_occurred",
        event_category=EnumIntelligenceCategory.HEALTH,
        correlation=correlation_context,
        source=source_info,
        priority=priority,
        payload=error_payload,
        error_context=error_context,
        metadata=ModelEventMetadata(
            source_type="error_handler",
            tags=["error", error_context.error_type, error_context.business_impact],
        ),
    )


def create_debug_event(
    debug_context: ModelDebugContext,
    source_component: str,
    operation_name: str,
    correlation_id: Optional[str] = None,
    priority: EnumIntelligencePriority = EnumIntelligencePriority.LOW,
) -> ModelIntelligenceEventEnvelope:
    """Factory function to create debug intelligence events."""

    correlation_context = ModelCorrelationContext()
    if correlation_id:
        correlation_context.correlation_id = correlation_id

    source_info = ModelEventSource(
        component_id=source_component,
        service_name=(
            source_component.split("-")[0]
            if "-" in source_component
            else source_component
        ),
    )

    # Create debug-specific payload
    debug_payload = ModelEventPayloadData(
        description=f"Debug trace for {operation_name}",
        category="debug",
        operation=operation_name,
        status="debug",
        affected_components=[source_component],
    )

    return ModelIntelligenceEventEnvelope(
        event_type="debug_trace",
        event_category=EnumIntelligenceCategory.HEALTH,
        correlation=correlation_context,
        source=source_info,
        priority=priority,
        payload=debug_payload,
        debug_context=debug_context,
        metadata=ModelEventMetadata(
            source_type="debug_tracer",
            tags=["debug", debug_context.trace_level, "troubleshooting"],
        ),
    )
