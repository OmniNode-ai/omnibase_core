"""
Typed metadata models for replacing dict[str, Any] patterns.

This module provides strongly-typed models for common metadata patterns
found across discovery, effect, reducer, and other model modules.
"""

from typing import Self
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.common.model_envelope_payload import ModelEnvelopePayload
from omnibase_core.models.common.model_graph_node_parameters import (
    ModelGraphNodeParameters,
)
from omnibase_core.models.common.model_output_mapping import ModelOutputMapping
from omnibase_core.models.common.model_query_parameters import ModelQueryParameters
from omnibase_core.models.errors.model_onex_error import ModelOnexError


class ModelToolMetadataFields(BaseModel):
    """
    Typed metadata for discovered tools.

    Replaces dict[str, Any] metadata field in ModelDiscoveredTool
    with explicit typed fields for common tool metadata.
    """

    author: str | None = Field(
        default=None,
        description="Author or maintainer of the tool",
    )
    trust_score: float | None = Field(
        default=None,
        description="Trust score for the tool (0.0 to 1.0)",
        ge=0.0,
        le=1.0,
    )
    documentation_url: str | None = Field(
        default=None,
        description="URL to tool documentation",
    )
    source_repository: str | None = Field(
        default=None,
        description="Source code repository URL",
    )
    license: str | None = Field(
        default=None,
        description="Software license identifier",
    )
    category: str | None = Field(
        default=None,
        description="Tool category for classification",
    )
    capabilities: list[str] = Field(
        default_factory=list,
        description="List of tool capabilities",
    )
    dependencies: list[str] = Field(
        default_factory=list,
        description="List of tool dependencies",
    )


class ModelNodeCapabilitiesMetadata(BaseModel):
    """
    Typed metadata for node capabilities.

    Replaces dict[str, Any] metadata field in ModelNodeCapabilities
    with explicit typed fields for common node metadata.
    """

    author: str | None = Field(
        default=None,
        description="Author or maintainer of the node",
    )
    trust_score: float | None = Field(
        default=None,
        description="Trust score for the node (0.0 to 1.0)",
        ge=0.0,
        le=1.0,
    )
    documentation_url: str | None = Field(
        default=None,
        description="URL to node documentation",
    )
    source_repository: str | None = Field(
        default=None,
        description="Source code repository URL",
    )
    license: str | None = Field(
        default=None,
        description="Software license identifier",
    )
    maintainers: list[str] = Field(
        default_factory=list,
        description="List of node maintainers",
    )


class ModelRequestMetadata(BaseModel):
    """
    Typed metadata for discovery/effect/reducer requests.

    Replaces dict[str, Any] metadata field in request models
    with explicit typed fields for common request metadata.
    """

    source: str | None = Field(
        default=None,
        description="Source identifier of the request",
    )
    trace_id: str | None = Field(
        default=None,
        description="Distributed tracing identifier",
    )
    span_id: str | None = Field(
        default=None,
        description="Span identifier for tracing",
    )
    user_agent: str | None = Field(
        default=None,
        description="User agent making the request",
    )
    environment: str | None = Field(
        default=None,
        description="Deployment environment (dev, staging, prod)",
    )
    priority: str | None = Field(
        default=None,
        description="Request priority level",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Tags for request categorization",
    )


class ModelShutdownMetrics(BaseModel):
    """
    Typed metrics for node shutdown events.

    Replaces dict[str, Any] final_metrics field in ModelNodeShutdownEvent
    with explicit typed fields for shutdown metrics.
    """

    error_message: str | None = Field(
        default=None,
        description="Error message if shutdown was due to error",
    )
    maintenance_reason: str | None = Field(
        default=None,
        description="Reason for maintenance shutdown",
    )
    force_reason: str | None = Field(
        default=None,
        description="Reason for forced shutdown",
    )
    total_requests: int | None = Field(
        default=None,
        description="Total requests processed during lifetime",
        ge=0,
    )
    total_errors: int | None = Field(
        default=None,
        description="Total errors encountered during lifetime",
        ge=0,
    )
    average_response_time_ms: float | None = Field(
        default=None,
        description="Average response time in milliseconds",
        ge=0.0,
    )
    peak_memory_mb: int | None = Field(
        default=None,
        description="Peak memory usage in megabytes",
        ge=0,
    )
    cpu_time_seconds: float | None = Field(
        default=None,
        description="Total CPU time consumed in seconds",
        ge=0.0,
    )


class ModelConfigSchemaProperty(BaseModel):
    """
    Typed schema property for mixin configuration.

    Replaces nested dict[str, Any] in config_schema field
    with explicit typed fields for JSON Schema properties.
    """

    type: str = Field(
        default="string",
        description="Property type (string, number, integer, boolean, array, object)",
    )
    description: str | None = Field(
        default=None,
        description="Property description",
    )
    default: str | int | float | bool | None = Field(
        default=None,
        description="Default value (type should match the 'type' field)",
    )
    enum: list[str | int | float | bool | None] | None = Field(
        default=None,
        description="Allowed enum values (supports strings, numbers, booleans, and null)",
    )
    required: bool = Field(
        default=False,
        description="Whether this property is required",
    )
    min_value: float | None = Field(
        default=None,
        description="Minimum value for numeric types",
    )
    max_value: float | None = Field(
        default=None,
        description="Maximum value for numeric types",
    )

    @model_validator(mode="after")
    def validate_type_default_consistency(self) -> Self:
        """Validate that default value type matches declared type.

        Enforces type consistency between the 'type' field and 'default' value:
        - type="string" requires default to be str
        - type="number" or type="float" requires default to be int or float
        - type="integer" or type="int" requires default to be int (not float)
        - type="boolean" or type="bool" requires default to be bool

        Note: int is acceptable for float/number types (widening conversion),
        but bool is NOT acceptable for int types (even though bool is int subclass).

        Raises:
            ModelOnexError: If default value type doesn't match declared type.
        """
        if self.default is None:
            return self

        declared_type = self.type.lower()
        actual_type = type(self.default)
        actual_type_name = actual_type.__name__

        # Define type mappings: declared_type -> (valid_types, description)
        type_validations: dict[str, tuple[tuple[type, ...], str]] = {
            "string": ((str,), "string"),
            "str": ((str,), "string"),
            "number": ((int, float), "number (int or float)"),
            "float": ((int, float), "number (int or float)"),
            "integer": ((int,), "integer"),
            "int": ((int,), "integer"),
            "boolean": ((bool,), "boolean"),
            "bool": ((bool,), "boolean"),
        }

        if declared_type in type_validations:
            valid_types, type_desc = type_validations[declared_type]

            # Special case: bool is subclass of int, but we don't want bool for int/integer
            if declared_type in ("integer", "int") and isinstance(self.default, bool):
                raise ModelOnexError(
                    message=(
                        f"Type mismatch: default value has type '{actual_type_name}' "
                        f"but declared type is '{self.type}'. "
                        f"Boolean values are not valid for integer type."
                    ),
                    error_code=EnumCoreErrorCode.PARAMETER_TYPE_MISMATCH,
                    context={
                        "declared_type": self.type,
                        "actual_type": actual_type_name,
                        "default_value": str(self.default),
                    },
                )

            # For number/float types, also reject bool (bool is int subclass)
            if declared_type in ("number", "float") and isinstance(self.default, bool):
                raise ModelOnexError(
                    message=(
                        f"Type mismatch: default value has type '{actual_type_name}' "
                        f"but declared type is '{self.type}'. "
                        f"Boolean values are not valid for numeric types."
                    ),
                    error_code=EnumCoreErrorCode.PARAMETER_TYPE_MISMATCH,
                    context={
                        "declared_type": self.type,
                        "actual_type": actual_type_name,
                        "default_value": str(self.default),
                    },
                )

            if not isinstance(self.default, valid_types):
                raise ModelOnexError(
                    message=(
                        f"Type mismatch: default value has type '{actual_type_name}' "
                        f"but declared type is '{self.type}'. "
                        f"Expected {type_desc}."
                    ),
                    error_code=EnumCoreErrorCode.PARAMETER_TYPE_MISMATCH,
                    context={
                        "declared_type": self.type,
                        "actual_type": actual_type_name,
                        "default_value": str(self.default),
                    },
                )

        return self


class ModelMixinConfigSchema(BaseModel):
    """
    Typed configuration schema for mixins.

    Replaces dict[str, Any] config_schema field in ModelMixinInfo
    with explicit typed fields for mixin configuration.
    """

    properties: dict[str, ModelConfigSchemaProperty] = Field(
        default_factory=dict,
        description="Schema properties mapped by name",
    )
    required_properties: list[str] = Field(
        default_factory=list,
        description="List of required property names",
    )
    additional_properties_allowed: bool = Field(
        default=True,
        description="Whether additional properties are allowed",
    )

    @model_validator(mode="after")
    def _validate_required_properties_subset(self) -> "ModelMixinConfigSchema":
        """Validate that required_properties is a subset of properties keys."""
        if not self.required_properties:
            return self

        property_names = set(self.properties.keys())
        required_set = set(self.required_properties)
        undefined_required = required_set - property_names

        if undefined_required:
            raise ValueError(
                f"required_properties contains undefined properties: "
                f"{sorted(undefined_required)}. "
                f"Valid properties are: {sorted(property_names)}"
            )

        return self


class ModelOperationData(BaseModel):
    """
    Typed operation data for effect input.

    Replaces dict[str, Any] operation_data field in ModelEffectInput
    with explicit typed fields for effect operations.
    """

    # Common fields across all effect types
    action: str | None = Field(
        default=None,
        description="Action to perform",
    )
    target: str | None = Field(
        default=None,
        description="Target resource for the operation",
    )

    # Database operation fields
    table: str | None = Field(
        default=None,
        description="Database table name",
    )
    query: str | None = Field(
        default=None,
        description="Database query string",
    )
    parameters: ModelQueryParameters = Field(
        default_factory=ModelQueryParameters,
        description="Query parameters",
    )

    # API call fields
    url: str | None = Field(
        default=None,
        description="API endpoint URL",
    )
    method: str | None = Field(
        default=None,
        description="HTTP method (GET, POST, PUT, DELETE)",
    )
    headers: dict[str, str] = Field(
        default_factory=dict,
        description="HTTP headers",
    )
    body: str | None = Field(
        default=None,
        description="Request body as string",
    )

    # File operation fields
    path: str | None = Field(
        default=None,
        description="File system path",
    )
    content: str | None = Field(
        default=None,
        description="File content for write operations",
    )

    # Message queue fields
    queue_name: str | None = Field(
        default=None,
        description="Message queue name",
    )
    message: str | None = Field(
        default=None,
        description="Message content",
    )

    # Event envelope payload (for event-driven processing)
    envelope_payload: ModelEnvelopePayload = Field(
        default_factory=ModelEnvelopePayload,
        description="Event envelope payload data",
    )


class ModelEffectMetadata(BaseModel):
    """
    Typed metadata for effect input/output.

    Replaces dict[str, Any] metadata field in ModelEffectInput/Output
    with explicit typed fields for effect metadata.
    """

    source: str | None = Field(
        default=None,
        description="Source identifier",
    )
    trace_id: str | None = Field(
        default=None,
        description="Distributed tracing identifier",
    )
    span_id: str | None = Field(
        default=None,
        description="Span identifier for tracing",
    )
    correlation_id: str | None = Field(
        default=None,
        description="Correlation ID for request tracking",
    )
    environment: str | None = Field(
        default=None,
        description="Deployment environment",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Tags for categorization",
    )
    priority: str | None = Field(
        default=None,
        description="Operation priority",
    )
    retry_count: int | None = Field(
        default=None,
        description="Number of retry attempts",
        ge=0,
    )


class ModelIntentPayload(BaseModel):
    """
    Typed payload for intent declarations.

    Replaces dict[str, Any] payload field in ModelIntent
    with explicit typed fields for intent payloads.
    """

    # Event emission fields
    event_type: str | None = Field(
        default=None,
        description="Event type to emit",
    )
    event_data: dict[str, str] = Field(
        default_factory=dict,
        description="Event data as key-value pairs",
    )

    # Logging fields
    log_level: str | None = Field(
        default=None,
        description="Log level (debug, info, warn, error)",
    )
    log_message: str | None = Field(
        default=None,
        description="Log message content",
    )

    # Storage fields
    storage_key: str | None = Field(
        default=None,
        description="Storage key for write operations",
    )
    storage_value: str | None = Field(
        default=None,
        description="Value to store",
    )

    # Notification fields
    notification_type: str | None = Field(
        default=None,
        description="Type of notification",
    )
    recipients: list[str] = Field(
        default_factory=list,
        description="Notification recipients",
    )
    subject: str | None = Field(
        default=None,
        description="Notification subject",
    )
    body: str | None = Field(
        default=None,
        description="Notification body",
    )

    # HTTP request fields
    url: str | None = Field(
        default=None,
        description="HTTP request URL",
    )
    method: str | None = Field(
        default=None,
        description="HTTP method",
    )
    headers: dict[str, str] = Field(
        default_factory=dict,
        description="HTTP headers",
    )
    request_body: str | None = Field(
        default=None,
        description="HTTP request body",
    )


class ModelReducerMetadata(BaseModel):
    """
    Typed metadata for reducer input.

    Replaces dict[str, Any] metadata field in ModelReducerInput
    with explicit typed fields for reducer metadata.
    """

    source: str | None = Field(
        default=None,
        description="Source identifier",
    )
    trace_id: str | None = Field(
        default=None,
        description="Distributed tracing identifier",
    )
    span_id: str | None = Field(
        default=None,
        description="Span identifier for tracing",
    )
    correlation_id: str | None = Field(
        default=None,
        description="Correlation ID for request tracking",
    )
    group_key: str | None = Field(
        default=None,
        description="Key for grouping operations",
    )
    partition_id: UUID | None = Field(
        default=None,
        description="Partition identifier for distributed processing",
    )
    window_id: UUID | None = Field(
        default=None,
        description="Window identifier for streaming operations",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Tags for categorization",
    )


class ModelCustomHealthMetrics(BaseModel):
    """
    Typed custom metrics for health monitoring.

    Replaces dict[str, Any] custom_metrics field in ModelHealthMetrics
    with explicit typed fields for custom health metrics.
    """

    status: str | None = Field(
        default=None,
        description="Health status (healthy, warning, critical, error)",
    )
    status_code: float | None = Field(
        default=None,
        description="Numeric status code (1.0=healthy, 0.5=warning, 0.0=critical)",
    )
    queue_depth: int | None = Field(
        default=None,
        description="Current queue depth",
        ge=0,
    )
    cache_hit_rate: float | None = Field(
        default=None,
        description="Cache hit rate (0.0 to 1.0)",
        ge=0.0,
        le=1.0,
    )
    thread_count: int | None = Field(
        default=None,
        description="Current thread count",
        ge=0,
    )
    open_connections: int | None = Field(
        default=None,
        description="Number of open connections",
        ge=0,
    )
    disk_usage_percent: float | None = Field(
        default=None,
        description="Disk usage percentage",
        ge=0.0,
        le=100.0,
    )
    network_io_bytes: int | None = Field(
        default=None,
        description="Network I/O in bytes",
        ge=0,
    )
    custom_values: dict[str, float] = Field(
        default_factory=dict,
        description="Additional custom numeric metrics",
    )


class ModelIntrospectionCustomMetrics(BaseModel):
    """
    Typed custom metrics for introspection additional info.

    Replaces dict[str, Any] custom_metrics field in ModelIntrospectionAdditionalInfo
    with explicit typed fields for introspection metrics.
    """

    request_count: int | None = Field(
        default=None,
        description="Total request count",
        ge=0,
    )
    error_count: int | None = Field(
        default=None,
        description="Total error count",
        ge=0,
    )
    average_latency_ms: float | None = Field(
        default=None,
        description="Average latency in milliseconds",
        ge=0.0,
    )
    p99_latency_ms: float | None = Field(
        default=None,
        description="99th percentile latency in milliseconds",
        ge=0.0,
    )
    throughput_per_second: float | None = Field(
        default=None,
        description="Throughput in requests per second",
        ge=0.0,
    )
    cache_size: int | None = Field(
        default=None,
        description="Current cache size",
        ge=0,
    )
    custom_values: dict[str, float] = Field(
        default_factory=dict,
        description="Additional custom numeric metrics",
    )


class ModelGraphNodeData(BaseModel):
    """
    Typed data for graph nodes.

    Replaces dict[str, Any] data field in ModelGraphNode
    with explicit typed fields for graph node data.
    """

    state: str | None = Field(
        default=None,
        description="Current node state",
    )
    priority: int | None = Field(
        default=None,
        description="Node execution priority (0-100, higher = more urgent)",
        ge=0,
        le=100,
    )
    timeout_ms: int | None = Field(
        default=None,
        description="Node execution timeout in milliseconds",
        ge=0,
    )
    retry_count: int | None = Field(
        default=None,
        description="Maximum retry count",
        ge=0,
    )
    condition: str | None = Field(
        default=None,
        description="Condition expression for decision nodes",
    )
    output_mapping: dict[str, str] = Field(
        default_factory=dict,
        description="Output variable mappings",
    )
    error_handler: str | None = Field(
        default=None,
        description="Error handler node ID",
    )


class ModelGraphNodeInputs(BaseModel):
    """
    Typed inputs for graph nodes.

    Replaces dict[str, Any] inputs field in ModelGraphNode
    with explicit typed fields for graph node inputs.
    """

    parameters: ModelGraphNodeParameters = Field(
        default_factory=ModelGraphNodeParameters,
        description="Input parameters as key-value pairs",
    )
    from_outputs: ModelOutputMapping = Field(
        default_factory=ModelOutputMapping,
        description="Mappings from other node outputs",
    )
    constants: dict[str, str] = Field(
        default_factory=dict,
        description="Constant input values as strings",
    )
    environment_vars: list[str] = Field(
        default_factory=list,
        description="Environment variables to inject",
    )


class ModelToolResultData(BaseModel):
    """
    Typed result data for tool responses.

    Replaces dict[str, Any] result field in ModelToolResponseEvent
    with explicit typed fields for tool execution results.
    """

    output: str | None = Field(
        default=None,
        description="Tool output content",
    )
    status: str | None = Field(
        default=None,
        description="Execution status",
    )
    artifacts: list[str] = Field(
        default_factory=list,
        description="Generated artifact paths or IDs",
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Non-fatal warnings during execution",
    )
    metrics: dict[str, float] = Field(
        default_factory=dict,
        description="Execution metrics",
    )
    data_fields: dict[str, str] = Field(
        default_factory=dict,
        description="Additional result data as key-value pairs",
    )


class ModelEventSubscriptionConfig(BaseModel):
    """
    Typed event subscription configuration.

    Replaces list[dict[str, Any]] event_subscriptions field in ModelYamlContract
    with explicit typed fields for event subscriptions.
    """

    event_type: str = Field(
        ...,
        description="Event type pattern to subscribe to",
    )
    filter_expression: str | None = Field(
        default=None,
        description="Filter expression for event matching",
    )
    handler: str | None = Field(
        default=None,
        description="Handler method or function name",
    )
    priority: int = Field(
        default=0,
        description="Subscription priority (0-100, higher = more urgent)",
        ge=0,
        le=100,
    )
    batch_size: int | None = Field(
        default=None,
        description="Batch size for batched processing",
        ge=1,
    )
    timeout_ms: int | None = Field(
        default=None,
        description="Processing timeout in milliseconds",
        ge=0,
    )


__all__ = [
    "ModelToolMetadataFields",
    "ModelNodeCapabilitiesMetadata",
    "ModelRequestMetadata",
    "ModelShutdownMetrics",
    "ModelConfigSchemaProperty",
    "ModelMixinConfigSchema",
    "ModelOperationData",
    "ModelEffectMetadata",
    "ModelIntentPayload",
    "ModelReducerMetadata",
    "ModelCustomHealthMetrics",
    "ModelIntrospectionCustomMetrics",
    "ModelGraphNodeData",
    "ModelGraphNodeInputs",
    "ModelToolResultData",
    "ModelEventSubscriptionConfig",
]
