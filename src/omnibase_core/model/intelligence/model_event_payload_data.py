"""
ONEX Event Payload Data - Strongly typed payload structures for intelligence events.

This module defines strongly typed payload data structures that replace generic
Dict[str, Any] usage in intelligence event schemas, ensuring ONEX compliance.
"""

from datetime import datetime
from typing import Dict, List, Optional, Union

from pydantic import BaseModel, Field


class ModelEventPayloadData(BaseModel):
    """Strongly typed payload data for intelligence events."""

    # Core event data
    pattern_id: Optional[str] = Field(
        default=None, description="Pattern identifier if applicable"
    )
    rule_id: Optional[str] = Field(
        default=None, description="Rule identifier if applicable"
    )
    context_id: Optional[str] = Field(
        default=None, description="Context identifier if applicable"
    )

    # Numeric values
    confidence_score: Optional[float] = Field(
        default=None, description="Confidence score for event"
    )
    quality_score: Optional[float] = Field(
        default=None, description="Quality assessment score"
    )
    processing_duration_ms: Optional[float] = Field(
        default=None, description="Processing duration"
    )

    # Text and string data
    description: Optional[str] = Field(default=None, description="Event description")
    category: Optional[str] = Field(default=None, description="Event category")
    operation: Optional[str] = Field(
        default=None, description="Operation being performed"
    )
    status: Optional[str] = Field(default=None, description="Operation status")

    # Lists of identifiers
    affected_components: List[str] = Field(
        default_factory=list, description="Components affected"
    )
    related_patterns: List[str] = Field(
        default_factory=list, description="Related pattern IDs"
    )
    related_rules: List[str] = Field(
        default_factory=list, description="Related rule IDs"
    )

    # Boolean flags
    is_validated: Optional[bool] = Field(
        default=None, description="Whether event is validated"
    )
    requires_promotion: Optional[bool] = Field(
        default=None, description="Whether promotion is required"
    )
    is_shadow_mode: Optional[bool] = Field(
        default=None, description="Whether in shadow mode"
    )

    # Counts and metrics
    event_count: Optional[int] = Field(default=None, description="Number of events")
    success_count: Optional[int] = Field(
        default=None, description="Number of successes"
    )
    failure_count: Optional[int] = Field(default=None, description="Number of failures")


class ModelEventMetadata(BaseModel):
    """Strongly typed metadata for intelligence events."""

    # Source information
    source_type: Optional[str] = Field(default=None, description="Type of event source")
    source_version: Optional[str] = Field(
        default=None, description="Source component version"
    )
    source_environment: Optional[str] = Field(
        default=None, description="Source environment"
    )

    # Processing information
    retry_count: Optional[int] = Field(
        default=None, description="Number of processing retries"
    )
    processing_node: Optional[str] = Field(
        default=None, description="Node that processed event"
    )
    queue_name: Optional[str] = Field(
        default=None, description="Queue that handled event"
    )

    # Timing information
    enqueued_at: Optional[datetime] = Field(
        default=None, description="When event was queued"
    )
    processing_started_at: Optional[datetime] = Field(
        default=None, description="When processing started"
    )
    processing_completed_at: Optional[datetime] = Field(
        default=None, description="When processing completed"
    )

    # Tags and labels
    tags: List[str] = Field(default_factory=list, description="Event tags")
    labels: Dict[str, str] = Field(default_factory=dict, description="Key-value labels")

    # Additional context
    user_agent: Optional[str] = Field(
        default=None, description="User agent if applicable"
    )
    request_id: Optional[str] = Field(
        default=None, description="Request identifier if applicable"
    )
    session_context: Optional[str] = Field(default=None, description="Session context")


class ModelValidationResult(BaseModel):
    """Strongly typed validation result data."""

    validation_id: str = Field(description="Unique validation identifier")
    validation_type: str = Field(description="Type of validation performed")
    validation_status: str = Field(description="passed, failed, partial")

    # Validation metrics
    accuracy_score: Optional[float] = Field(
        default=None, description="Validation accuracy"
    )
    precision_score: Optional[float] = Field(
        default=None, description="Validation precision"
    )
    recall_score: Optional[float] = Field(default=None, description="Validation recall")

    # Validation details
    rules_tested: List[str] = Field(
        default_factory=list, description="Rules that were tested"
    )
    patterns_validated: List[str] = Field(
        default_factory=list, description="Patterns validated"
    )
    test_cases_passed: int = Field(default=0, description="Number of test cases passed")
    test_cases_failed: int = Field(default=0, description="Number of test cases failed")

    # Error information
    validation_errors: List[str] = Field(
        default_factory=list, description="Validation error messages"
    )
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")

    # Timestamps
    validation_started_at: datetime = Field(description="When validation started")
    validation_completed_at: Optional[datetime] = Field(
        default=None, description="When validation completed"
    )


class ModelWorkflowContextData(BaseModel):
    """Strongly typed workflow context data."""

    # Workflow identification
    workflow_name: str = Field(description="Human-readable workflow name")
    workflow_version: str = Field(default="1.0.0", description="Workflow version")
    parent_workflow_id: Optional[str] = Field(
        default=None, description="Parent workflow if nested"
    )

    # Workflow configuration
    max_execution_time_seconds: Optional[int] = Field(
        default=None, description="Maximum execution time"
    )
    retry_policy: Optional[str] = Field(
        default=None, description="Retry policy configuration"
    )
    failure_handling: Optional[str] = Field(
        default=None, description="Failure handling strategy"
    )

    # Progress tracking
    total_steps: Optional[int] = Field(default=None, description="Total workflow steps")
    completed_steps: int = Field(default=0, description="Steps completed")
    failed_steps: int = Field(default=0, description="Steps that failed")
    skipped_steps: int = Field(default=0, description="Steps that were skipped")

    # Resource usage
    cpu_usage_seconds: Optional[float] = Field(
        default=None, description="CPU time used"
    )
    memory_usage_mb: Optional[float] = Field(
        default=None, description="Memory usage in MB"
    )
    disk_usage_mb: Optional[float] = Field(default=None, description="Disk usage in MB")

    # Dependencies and requirements
    required_services: List[str] = Field(
        default_factory=list, description="Required services"
    )
    dependent_workflows: List[str] = Field(
        default_factory=list, description="Dependent workflows"
    )
    prerequisite_conditions: List[str] = Field(
        default_factory=list, description="Prerequisites"
    )


class ModelOperationContext(BaseModel):
    """Strongly typed operation context data."""

    # Operation identification
    operation_name: str = Field(description="Name of the operation")
    operation_version: str = Field(default="1.0.0", description="Operation version")
    operation_type: str = Field(
        description="Type of operation (create, update, delete, etc.)"
    )

    # Resource information
    target_resource_type: Optional[str] = Field(
        default=None, description="Type of target resource"
    )
    target_resource_id: Optional[str] = Field(
        default=None, description="Target resource identifier"
    )
    affected_resource_count: int = Field(
        default=0, description="Number of resources affected"
    )

    # Configuration
    parameters: Dict[str, Union[str, int, float, bool]] = Field(
        default_factory=dict, description="Operation parameters"
    )
    options: List[str] = Field(default_factory=list, description="Operation options")

    # Tracking
    initiated_by: Optional[str] = Field(
        default=None, description="Who/what initiated operation"
    )
    authorization_level: Optional[str] = Field(
        default=None, description="Authorization level required"
    )
    audit_trail: bool = Field(
        default=True, description="Whether audit trail is enabled"
    )


class ModelSuccessCriteria(BaseModel):
    """Strongly typed success criteria data."""

    # Criteria definition
    criteria_name: str = Field(description="Name of success criteria")
    criteria_type: str = Field(
        description="Type of criteria (threshold, percentage, boolean)"
    )

    # Threshold values
    min_threshold: Optional[float] = Field(
        default=None, description="Minimum threshold value"
    )
    max_threshold: Optional[float] = Field(
        default=None, description="Maximum threshold value"
    )
    target_value: Optional[float] = Field(
        default=None, description="Target value to achieve"
    )

    # Percentage-based criteria
    min_success_percentage: Optional[float] = Field(
        default=None, description="Minimum success percentage"
    )
    required_completion_percentage: Optional[float] = Field(
        default=None, description="Required completion percentage"
    )

    # Boolean criteria
    all_must_succeed: bool = Field(
        default=False, description="Whether all sub-operations must succeed"
    )
    allow_partial_success: bool = Field(
        default=True, description="Whether partial success is acceptable"
    )

    # Validation requirements
    validation_required: bool = Field(
        default=True, description="Whether validation is required"
    )
    human_approval_required: bool = Field(
        default=False, description="Whether human approval is needed"
    )

    # Time constraints
    max_execution_time_seconds: Optional[int] = Field(
        default=None, description="Maximum execution time"
    )
    timeout_behavior: str = Field(
        default="fail", description="Behavior on timeout (fail, retry, partial)"
    )


class ModelBatchProcessingMetadata(BaseModel):
    """Strongly typed batch processing metadata."""

    # Batch information
    batch_size: int = Field(description="Number of items in batch")
    batch_sequence_number: int = Field(description="Sequence number of this batch")
    total_batches: Optional[int] = Field(
        default=None, description="Total number of batches"
    )

    # Processing strategy
    processing_strategy: str = Field(description="parallel, sequential, adaptive")
    max_concurrent_items: Optional[int] = Field(
        default=None, description="Max concurrent processing"
    )
    chunk_size: Optional[int] = Field(default=None, description="Processing chunk size")

    # Performance requirements
    target_throughput_per_second: Optional[float] = Field(
        default=None, description="Target throughput"
    )
    max_latency_ms: Optional[float] = Field(
        default=None, description="Maximum acceptable latency"
    )
    memory_limit_mb: Optional[float] = Field(
        default=None, description="Memory limit for processing"
    )

    # Error handling
    max_retries_per_item: int = Field(default=3, description="Maximum retries per item")
    failure_threshold_percentage: float = Field(
        default=0.1, description="Failure threshold before aborting"
    )
    continue_on_error: bool = Field(
        default=True, description="Whether to continue processing on errors"
    )

    # Progress tracking
    items_processed: int = Field(default=0, description="Number of items processed")
    items_succeeded: int = Field(
        default=0, description="Number of items that succeeded"
    )
    items_failed: int = Field(default=0, description="Number of items that failed")
    items_skipped: int = Field(default=0, description="Number of items skipped")


class ModelComponentContext(BaseModel):
    """Strongly typed component context data."""

    # Component identification
    component_name: str = Field(
        default="unknown", description="Human-readable component name"
    )
    component_type: str = Field(default="unknown", description="Type of component")
    component_role: str = Field(default="unknown", description="Role in the system")

    # Capabilities
    supported_operations: List[str] = Field(
        default_factory=list, description="Operations supported"
    )
    supported_event_types: List[str] = Field(
        default_factory=list, description="Event types handled"
    )
    performance_characteristics: Dict[str, Union[str, int, float]] = Field(
        default_factory=dict, description="Performance characteristics"
    )

    # State information
    current_load: Optional[float] = Field(
        default=None, description="Current load percentage"
    )
    health_status: str = Field(default="healthy", description="Component health status")
    availability_percentage: Optional[float] = Field(
        default=None, description="Availability percentage"
    )

    # Configuration
    configuration_version: str = Field(
        default="1.0.0", description="Configuration version"
    )
    feature_flags: Dict[str, bool] = Field(
        default_factory=dict, description="Feature flags"
    )
    environment_variables: Dict[str, str] = Field(
        default_factory=dict, description="Environment config"
    )


class ModelErrorContext(BaseModel):
    """Comprehensive error context for debugging and troubleshooting."""

    # Error identification
    error_id: str = Field(description="Unique error identifier")
    correlation_id: str = Field(description="Correlation ID for tracing")
    error_type: str = Field(
        description="Type of error (validation, operation, system, etc.)"
    )
    error_code: str = Field(description="Specific error code")
    error_message: str = Field(description="Human-readable error message")

    # Context information
    component_id: str = Field(description="Component where error occurred")
    operation_name: str = Field(description="Operation that caused the error")
    event_id: Optional[str] = Field(
        default=None, description="Related event ID if applicable"
    )

    # Technical details
    stack_trace: Optional[str] = Field(
        default=None, description="Stack trace if available"
    )
    exception_type: Optional[str] = Field(
        default=None, description="Exception class name"
    )

    # Timing and context
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="When error occurred"
    )
    execution_duration_ms: Optional[float] = Field(
        default=None, description="Time before error"
    )

    # System state
    system_state: Dict[str, Union[str, int, float, bool]] = Field(
        default_factory=dict, description="Relevant system state at error time"
    )

    # Recovery information
    is_recoverable: bool = Field(
        default=True, description="Whether error is recoverable"
    )
    suggested_actions: List[str] = Field(
        default_factory=list, description="Suggested recovery actions"
    )
    retry_count: int = Field(default=0, description="Number of retry attempts")
    max_retries: int = Field(default=3, description="Maximum retry attempts")

    # Additional context
    user_impact: str = Field(default="unknown", description="Impact on user experience")
    business_impact: str = Field(default="low", description="Business impact level")
    related_errors: List[str] = Field(
        default_factory=list, description="Related error IDs"
    )


class ModelDebugContext(BaseModel):
    """Debug context for comprehensive troubleshooting information."""

    # Debug session information
    debug_session_id: str = Field(description="Debug session identifier")
    trace_level: str = Field(
        default="info", description="Trace detail level (debug, info, warn, error)"
    )

    # Execution context
    execution_path: List[str] = Field(
        default_factory=list, description="Execution path through components"
    )
    method_calls: List[Dict[str, str]] = Field(
        default_factory=list, description="Method call chain"
    )

    # Performance data
    performance_metrics: Dict[str, float] = Field(
        default_factory=dict, description="Performance metrics during execution"
    )

    # Resource usage
    memory_usage_mb: Optional[float] = Field(
        default=None, description="Memory usage in MB"
    )
    cpu_usage_percent: Optional[float] = Field(
        default=None, description="CPU usage percentage"
    )

    # State snapshots
    state_snapshots: Dict[str, Dict] = Field(
        default_factory=dict, description="Component state snapshots at key points"
    )

    # Validation results
    validation_results: List[Dict[str, str]] = Field(
        default_factory=list, description="Validation check results"
    )

    # Environment context
    environment_info: Dict[str, str] = Field(
        default_factory=dict, description="Environment and configuration info"
    )
