"""
Demonstration of Union Type Refactoring for node_gateway.py

This file shows the exact changes needed to replace Union types with proper Pydantic models.
"""

from datetime import datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

# Import our new strongly typed models
from omnibase_core.model.gateway.model_gateway_metadata import (
    GatewayMetadata,
    LoadBalancingDecision,
)


# Existing enums (unchanged)
class RoutingStrategy:
    ROUND_ROBIN = "round_robin"
    WEIGHTED = "weighted"
    LEAST_CONNECTIONS = "least_connections"


class ProtocolType:
    HTTP = "http"
    GRPC = "grpc"
    WEBSOCKET = "websocket"


# ============================================================================
# BEFORE: Original Union-heavy models
# ============================================================================


class ModelGatewayInputBefore(BaseModel):
    """Original model with Union types."""

    # This uses weak typing - any string key with any primitive value
    message_data: dict[str, Union[str, int, float, bool]]
    destination_endpoints: list[str]
    operation_id: str | None = Field(default_factory=lambda: str(uuid4()))
    routing_strategy: str = RoutingStrategy.ROUND_ROBIN

    # More weak typing - generic metadata dictionary
    metadata: dict[str, Union[str, int, float, bool]] | None = Field(
        default_factory=dict,
    )
    timestamp: datetime = Field(default_factory=datetime.now)


class ModelGatewayOutputBefore(BaseModel):
    """Original output model with Union types."""

    # Weak return type - could be anything
    result: dict[str, Union[str, int, float, bool]]
    operation_id: str
    routing_strategy: str
    selected_endpoint: str
    response_time_ms: float

    # Weak metadata typing
    load_balance_decision: dict[str, Union[str, int, float]] | None = None
    metadata: dict[str, Union[str, int, float, bool]] | None = Field(
        default_factory=dict,
    )


# ============================================================================
# AFTER: Refactored with strong Pydantic typing
# ============================================================================


class GatewayMessageData(BaseModel):
    """Strongly typed message data instead of generic Dict."""

    # Define expected message fields based on actual usage patterns
    request_id: str = Field(description="Unique request identifier")
    payload_type: str = Field(description="Type of message payload")
    content_length: int = Field(ge=0, description="Size of message content")
    priority: int = Field(default=1, ge=1, le=10, description="Message priority")
    compression_enabled: bool = Field(
        default=False,
        description="Whether content is compressed",
    )

    # Allow additional fields for flexibility, but validate known ones
    additional_data: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional message data",
    )

    class Config:
        extra = "ignore"  # Ignore unknown fields in demo
        validate_assignment = True


class GatewayResult(BaseModel):
    """Strongly typed result instead of generic Dict."""

    status: str = Field(description="Operation status")
    endpoint: str = Field(description="Selected endpoint")
    message_id: str = Field(description="Message identifier")
    processed_at: str = Field(description="Processing timestamp")

    # Performance metrics
    processing_time_ms: float = Field(ge=0.0, description="Processing time")
    bytes_transferred: int = Field(default=0, ge=0, description="Bytes transferred")

    class Config:
        validate_assignment = True


class ModelGatewayInputAfter(BaseModel):
    """Refactored input model with strong typing."""

    # Strongly typed message data
    message_data: GatewayMessageData
    destination_endpoints: list[str]
    operation_id: str | None = Field(default_factory=lambda: str(uuid4()))
    routing_strategy: str = RoutingStrategy.ROUND_ROBIN
    protocol_source: str = ProtocolType.HTTP
    protocol_target: str = ProtocolType.HTTP

    # Configuration with validation
    timeout_ms: int = Field(default=30000, ge=1000, le=300000)
    retry_enabled: bool = True
    max_retries: int = Field(default=3, ge=0, le=10)
    circuit_breaker_enabled: bool = True
    load_balancing_enabled: bool = True
    response_aggregation_enabled: bool = False

    # Strongly typed metadata instead of generic Dict
    metadata: GatewayMetadata = Field(default_factory=GatewayMetadata)
    timestamp: datetime = Field(default_factory=datetime.now)

    class Config:
        arbitrary_types_allowed = True
        validate_assignment = True


class ModelGatewayOutputAfter(BaseModel):
    """Refactored output model with strong typing."""

    # Strongly typed result
    result: GatewayResult
    operation_id: str
    routing_strategy: str
    selected_endpoint: str
    response_time_ms: float
    retry_count: int = 0
    endpoints_tried: list[str] = Field(default_factory=list)
    circuit_breaker_triggered: bool = False

    # Strongly typed load balancing decision
    load_balance_decision: LoadBalancingDecision | None = None
    aggregated_responses: list[GatewayResult] | None = None

    # Strongly typed metadata
    metadata: GatewayMetadata = Field(default_factory=GatewayMetadata)
    timestamp: datetime = Field(default_factory=datetime.now)

    class Config:
        arbitrary_types_allowed = True
        validate_assignment = True


# ============================================================================
# Usage Demonstration
# ============================================================================


def demonstrate_improvements():
    """Show the improvements gained from refactoring."""

    print("=== BEFORE: Weak typing with Unions ===")

    # Before: Weak typing allows any structure
    before_input = ModelGatewayInputBefore(
        message_data={
            "unknown_field": "could be anything",  # No validation
            "number_field": 42,
            "bool_field": True,
        },
        destination_endpoints=["http://service1", "http://service2"],
        metadata={
            "random_key": "random_value",  # No structure validation
            "another_key": 123,
        },
    )

    print(f"Before - message_data: {before_input.message_data}")
    print(f"Before - metadata: {before_input.metadata}")

    print("\n=== AFTER: Strong typing with Pydantic models ===")

    # After: Strong typing with validation
    after_input = ModelGatewayInputAfter(
        message_data=GatewayMessageData(
            request_id="req_123",
            payload_type="json",
            content_length=1024,
            priority=5,  # Validated: must be 1-10
            compression_enabled=True,
        ),
        destination_endpoints=["http://service1", "http://service2"],
        metadata=GatewayMetadata(
            node_type="canary_gateway",
            operation_type="route_message",
            timeout_ms=25000,  # Validated: must be 1000-300000
            circuit_breaker_enabled=True,
            load_balance_weight=1.5,  # Validated: must be 0.0-10.0
        ),
    )

    print(f"After - message_data: {after_input.message_data}")
    print(f"After - metadata: {after_input.metadata}")

    # Demonstrate validation
    print("\n=== VALIDATION BENEFITS ===")

    try:
        # This would fail validation due to invalid timeout
        invalid_metadata = GatewayMetadata(timeout_ms=500)  # Below minimum 1000
    except Exception as e:
        print(f"Validation caught invalid timeout: {e}")

    try:
        # This would fail validation due to invalid priority
        invalid_message = GatewayMessageData(
            request_id="req_456",
            payload_type="xml",
            content_length=-1,  # Negative content length
            priority=15,  # Above maximum 10
        )
    except Exception as e:
        print(f"Validation caught invalid message data: {e}")


# ============================================================================
# Migration Strategy
# ============================================================================


def migration_steps():
    """Outline the migration process."""

    steps = [
        "1. Create strongly typed models (like GatewayMessageData, GatewayMetadata)",
        "2. Update input/output models to use new types",
        "3. Update method signatures to use new models",
        "4. Update tests to use new models",
        "5. Run validation to ensure no regressions",
        "6. Remove old Union-based patterns",
    ]

    print("\n=== MIGRATION STEPS ===")
    for step in steps:
        print(step)


if __name__ == "__main__":
    demonstrate_improvements()
    migration_steps()
