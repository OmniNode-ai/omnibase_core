"""
Tests for ModelEventPayload structure.

Validates event payload functionality including data handling, context management,
serialization, and ONEX strong typing compliance with discriminated union structure.
"""

import json

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_event_type import EnumEventType
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.operations.model_error_event_data import ModelErrorEventData
from omnibase_core.models.operations.model_event_payload import ModelEventPayload
from omnibase_core.models.operations.model_system_event_data import ModelSystemEventData
from omnibase_core.models.operations.model_user_event_data import ModelUserEventData
from omnibase_core.models.operations.model_workflow_event_data import (
    ModelWorkflowEventData,
)


@pytest.mark.unit
class TestModelEventPayload:
    """Test basic event payload functionality with discriminated unions."""

    def test_system_event_creation(self):
        """Test creating system event payload."""
        event_data = ModelSystemEventData(
            event_type=EnumEventType.SYSTEM,
            system_component="auth-service",
            severity_level="info",
        )

        payload = ModelEventPayload(
            event_type=EnumEventType.SYSTEM,
            event_data=event_data,
        )

        assert payload.event_type == EnumEventType.SYSTEM
        assert payload.event_data.system_component == "auth-service"
        assert payload.event_data.severity_level == "info"

    def test_user_event_creation(self):
        """Test creating user event payload."""
        from omnibase_core.models.context import ModelSessionContext

        event_data = ModelUserEventData(
            event_type=EnumEventType.USER,
            user_action="login",
            session_context=ModelSessionContext(
                session_id="550e8400-e29b-41d4-a716-446655440000"
            ),
        )

        payload = ModelEventPayload(
            event_type=EnumEventType.USER,
            event_data=event_data,
        )

        assert payload.event_type == EnumEventType.USER
        assert payload.event_data.user_action == "login"
        assert (
            str(payload.event_data.session_context.session_id)
            == "550e8400-e29b-41d4-a716-446655440000"
        )

    def test_workflow_event_creation(self):
        """Test creating workflow event payload."""
        event_data = ModelWorkflowEventData(
            event_type=EnumEventType.WORKFLOW,
            workflow_stage="processing",
            workflow_step="validation",
            execution_metrics={"duration_ms": 150.5},
        )

        payload = ModelEventPayload(
            event_type=EnumEventType.WORKFLOW,
            event_data=event_data,
        )

        assert payload.event_type == EnumEventType.WORKFLOW
        assert payload.event_data.workflow_stage == "processing"
        assert payload.event_data.execution_metrics["duration_ms"] == 150.5

    def test_error_event_creation(self):
        """Test creating error event payload."""
        event_data = ModelErrorEventData(
            event_type=EnumEventType.ERROR,
            error_type="DatabaseError",
            error_message="Connection timeout",
            stack_trace="Error at line 42",
        )

        payload = ModelEventPayload(
            event_type=EnumEventType.ERROR,
            event_data=event_data,
        )

        assert payload.event_type == EnumEventType.ERROR
        assert payload.event_data.error_type == "DatabaseError"
        assert payload.event_data.error_message == "Connection timeout"

    def test_event_data_with_schema_values(self):
        """Test event data with ModelSchemaValue types."""
        event_data = ModelSystemEventData(
            event_type=EnumEventType.SYSTEM,
            system_component="metrics-service",
            diagnostic_data={
                "cpu_usage": ModelSchemaValue.from_value(75.5),
                "memory_mb": ModelSchemaValue.from_value(2048),
                "status": ModelSchemaValue.from_value("healthy"),
            },
        )

        payload = ModelEventPayload(
            event_type=EnumEventType.SYSTEM,
            event_data=event_data,
        )

        assert payload.event_data.diagnostic_data["cpu_usage"].to_value() == 75.5
        assert payload.event_data.diagnostic_data["memory_mb"].to_value() == 2048
        assert payload.event_data.diagnostic_data["status"].to_value() == "healthy"

    def test_context_information_in_event_data(self):
        """Test context information handling within event data."""
        event_data = ModelUserEventData(
            event_type=EnumEventType.USER,
            user_action="profile_update",
        )
        # Context is part of the event data base class
        event_data.context.environment = "production"

        payload = ModelEventPayload(
            event_type=EnumEventType.USER,
            event_data=event_data,
        )

        assert payload.event_data.context.environment == "production"

    def test_attributes_in_event_data(self):
        """Test attributes handling within event data."""
        event_data = ModelSystemEventData(
            event_type=EnumEventType.SYSTEM,
            system_component="cache-service",
        )
        event_data.attributes.category = "performance"
        event_data.attributes.importance = "high"
        event_data.attributes.tags = ["cache", "performance", "monitoring"]

        payload = ModelEventPayload(
            event_type=EnumEventType.SYSTEM,
            event_data=event_data,
        )

        assert payload.event_data.attributes.category == "performance"
        assert payload.event_data.attributes.importance == "high"
        assert len(payload.event_data.attributes.tags) == 3

    def test_source_info_in_event_data(self):
        """Test source information tracking within event data."""
        event_data = ModelUserEventData(
            event_type=EnumEventType.USER,
            user_action="checkout",
        )
        event_data.source_info.service_name = "payment-service"
        event_data.source_info.host_name = "payment-01"

        payload = ModelEventPayload(
            event_type=EnumEventType.USER,
            event_data=event_data,
        )

        assert payload.event_data.source_info.service_name == "payment-service"
        assert payload.event_data.source_info.host_name == "payment-01"

    def test_routing_info_management(self):
        """Test structured routing information."""
        event_data = ModelSystemEventData(
            event_type=EnumEventType.SYSTEM,
            system_component="notification-service",
        )

        payload = ModelEventPayload(
            event_type=EnumEventType.SYSTEM,
            event_data=event_data,
        )

        # Update routing info
        payload.routing_info.target_queue = "notifications"
        payload.routing_info.routing_key = "system.notification"
        payload.routing_info.priority = "high"
        payload.routing_info.broadcast = True

        assert payload.routing_info.target_queue == "notifications"
        assert payload.routing_info.routing_key == "system.notification"
        assert payload.routing_info.priority == "high"
        assert payload.routing_info.broadcast is True


@pytest.mark.unit
class TestModelEventPayloadSerialization:
    """Test serialization and deserialization with discriminated unions."""

    def test_system_event_serialization(self):
        """Test JSON serialization of system event."""
        event_data = ModelSystemEventData(
            event_type=EnumEventType.SYSTEM,
            system_component="database-monitor",
            severity_level="warning",
            diagnostic_data={
                "connections": ModelSchemaValue.from_value(95),
                "max_connections": ModelSchemaValue.from_value(100),
            },
        )

        payload = ModelEventPayload(
            event_type=EnumEventType.SYSTEM,
            event_data=event_data,
        )

        serialized = payload.model_dump()

        assert serialized["event_type"] == EnumEventType.SYSTEM
        assert serialized["event_data"]["system_component"] == "database-monitor"
        assert serialized["event_data"]["severity_level"] == "warning"

    def test_user_event_serialization(self):
        """Test JSON serialization of user event."""
        from omnibase_core.models.common.model_request_metadata import (
            ModelRequestMetadata,
        )
        from omnibase_core.models.context import ModelSessionContext

        event_data = ModelUserEventData(
            event_type=EnumEventType.USER,
            user_action="password_reset",
            session_context=ModelSessionContext(
                session_id="550e8400-e29b-41d4-a716-446655440001"
            ),
            request_metadata=ModelRequestMetadata(ip_address="192.168.1.1"),
        )

        payload = ModelEventPayload(
            event_type=EnumEventType.USER,
            event_data=event_data,
        )

        serialized = payload.model_dump()

        assert serialized["event_type"] == EnumEventType.USER
        assert serialized["event_data"]["user_action"] == "password_reset"
        assert (
            str(serialized["event_data"]["session_context"]["session_id"])
            == "550e8400-e29b-41d4-a716-446655440001"
        )

    def test_workflow_event_deserialization(self):
        """Test JSON deserialization of workflow event."""
        json_data = {
            "event_type": "workflow",
            "event_data": {
                "event_type": "workflow",
                "workflow_stage": "execution",
                "workflow_step": "data_processing",
                "execution_metrics": {"records_processed": 1000, "duration_ms": 5500.0},
                "state_changes": {},
                "context": {
                    "correlation_id": None,
                    "causation_id": None,
                    "session_id": None,
                    "tenant_id": None,
                    "environment": "production",
                    "version": {"major": 1, "minor": 0, "patch": 0},
                },
                "attributes": {
                    "category": "",
                    "importance": "medium",
                    "tags": [],
                    "custom_attributes": {},
                    "classification": "",
                },
                "source_info": {
                    "service_name": "workflow-engine",
                    "service_version": None,
                    "host_name": "",
                    "instance_id": None,
                    "request_id": None,
                    "user_agent": "",
                },
            },
            "routing_info": {
                "target_queue": "workflow-events",
                "routing_key": "workflow.execution",
                "priority": "normal",
                "broadcast": False,
                "retry_routing": True,
                "dead_letter_queue": "",
            },
        }

        payload = ModelEventPayload.model_validate(json_data)

        assert payload.event_type == EnumEventType.WORKFLOW
        assert payload.event_data.workflow_stage == "execution"
        assert payload.event_data.execution_metrics["records_processed"] == 1000
        assert payload.routing_info.target_queue == "workflow-events"

    def test_error_event_deserialization(self):
        """Test JSON deserialization of error event."""
        json_data = {
            "event_type": "error",
            "event_data": {
                "event_type": "error",
                "error_type": "ValidationError",
                "error_message": "Invalid input data",
                "stack_trace": "Error at validation.py:100",
                "recovery_actions": ["retry", "manual_review"],
                "impact_assessment": {"severity": "medium", "users_affected": "1"},
                "context": {
                    "correlation_id": None,
                    "causation_id": None,
                    "session_id": None,
                    "tenant_id": None,
                    "environment": "",
                    "version": {"major": 1, "minor": 0, "patch": 0},
                },
                "attributes": {
                    "category": "",
                    "importance": "medium",
                    "tags": [],
                    "custom_attributes": {},
                    "classification": "",
                },
                "source_info": {
                    "service_name": "",
                    "service_version": None,
                    "host_name": "",
                    "instance_id": None,
                    "request_id": None,
                    "user_agent": "",
                },
            },
            "routing_info": {
                "target_queue": "",
                "routing_key": "",
                "priority": "normal",
                "broadcast": False,
                "retry_routing": True,
                "dead_letter_queue": "",
            },
        }

        payload = ModelEventPayload.model_validate(json_data)

        assert payload.event_type == EnumEventType.ERROR
        assert payload.event_data.error_type == "ValidationError"
        assert payload.event_data.error_message == "Invalid input data"
        assert len(payload.event_data.recovery_actions) == 2

    def test_round_trip_serialization(self):
        """Test full round-trip serialization."""
        event_data = ModelSystemEventData(
            event_type=EnumEventType.SYSTEM,
            system_component="metrics-collector",
            severity_level="info",
            diagnostic_data={
                "cpu_percent": ModelSchemaValue.from_value(45.2),
                "memory_gb": ModelSchemaValue.from_value(8.5),
            },
        )

        original = ModelEventPayload(
            event_type=EnumEventType.SYSTEM,
            event_data=event_data,
        )

        # Serialize to JSON string
        json_str = original.model_dump_json()

        # Parse JSON and create new instance
        json_data = json.loads(json_str)
        deserialized = ModelEventPayload.model_validate(json_data)

        # Verify all fields match
        assert deserialized.event_type == original.event_type
        assert (
            deserialized.event_data.system_component
            == original.event_data.system_component
        )
        assert (
            deserialized.event_data.diagnostic_data["cpu_percent"].to_value()
            == original.event_data.diagnostic_data["cpu_percent"].to_value()
        )


@pytest.mark.unit
class TestModelEventPayloadValidation:
    """Test validation and error handling."""

    def test_missing_required_fields(self):
        """Test validation error for missing required fields."""
        with pytest.raises(ValidationError) as exc_info:
            ModelEventPayload()

        errors = exc_info.value.errors()
        assert len(errors) == 2
        assert any(e["loc"] == ("event_type",) for e in errors)
        assert any(e["loc"] == ("event_data",) for e in errors)

    def test_invalid_event_type(self):
        """Test validation error for invalid event type."""
        with pytest.raises(ValidationError):
            ModelEventPayload(
                event_type="invalid_type",  # Not a valid EnumEventType
                event_data=ModelSystemEventData(
                    event_type=EnumEventType.SYSTEM,
                    system_component="test",
                ),
            )

    def test_mismatched_event_types(self):
        """Test that mismatched event types are allowed (discriminator uses event_data.event_type)."""
        # The discriminated union is based on event_data.event_type, so top-level event_type
        # can differ without raising a validation error
        payload = ModelEventPayload(
            event_type=EnumEventType.SYSTEM,
            event_data=ModelUserEventData(
                event_type=EnumEventType.USER,
                user_action="login",
            ),
        )
        # Verify payload was created successfully with mismatched types
        assert payload.event_type == EnumEventType.SYSTEM
        assert payload.event_data.event_type == EnumEventType.USER

    def test_valid_system_event(self):
        """Test valid system event creation."""
        event_data = ModelSystemEventData(
            event_type=EnumEventType.SYSTEM,
            system_component="test-component",
        )
        payload = ModelEventPayload(
            event_type=EnumEventType.SYSTEM,
            event_data=event_data,
        )
        assert isinstance(payload, ModelEventPayload)

    def test_valid_user_event(self):
        """Test valid user event creation."""
        event_data = ModelUserEventData(
            event_type=EnumEventType.USER,
            user_action="test-action",
        )
        payload = ModelEventPayload(
            event_type=EnumEventType.USER,
            event_data=event_data,
        )
        assert isinstance(payload, ModelEventPayload)

    def test_valid_workflow_event(self):
        """Test valid workflow event creation."""
        event_data = ModelWorkflowEventData(
            event_type=EnumEventType.WORKFLOW,
            workflow_stage="test-stage",
            workflow_step="test-step",
        )
        payload = ModelEventPayload(
            event_type=EnumEventType.WORKFLOW,
            event_data=event_data,
        )
        assert isinstance(payload, ModelEventPayload)

    def test_valid_error_event(self):
        """Test valid error event creation."""
        event_data = ModelErrorEventData(
            event_type=EnumEventType.ERROR,
            error_type="TestError",
            error_message="Test error message",
        )
        payload = ModelEventPayload(
            event_type=EnumEventType.ERROR,
            event_data=event_data,
        )
        assert isinstance(payload, ModelEventPayload)


@pytest.mark.unit
class TestModelEventPayloadUsagePatterns:
    """Test real-world usage patterns and integration scenarios."""

    def test_user_authentication_event(self):
        """Test user authentication event payload pattern."""
        from omnibase_core.models.common.model_request_metadata import (
            ModelRequestMetadata,
        )
        from omnibase_core.models.context import (
            ModelAuthorizationContext,
            ModelSessionContext,
        )

        event_data = ModelUserEventData(
            event_type=EnumEventType.USER,
            user_action="authentication",
            session_context=ModelSessionContext(
                session_id="550e8400-e29b-41d4-a716-446655440002",
                authentication_method="oauth2",
            ),
            request_metadata=ModelRequestMetadata(
                ip_address="192.168.1.100",
                user_agent="MyApp/2.1.0 (iOS 17.0)",
            ),
            authorization_context=ModelAuthorizationContext(
                client_id="mobile_app_v2",
                scopes=["user:profile", "user:email"],
            ),
        )
        event_data.context.environment = "production"
        event_data.attributes.category = "security"
        event_data.attributes.importance = "high"
        event_data.source_info.service_name = "authentication-service"

        payload = ModelEventPayload(
            event_type=EnumEventType.USER,
            event_data=event_data,
        )
        payload.routing_info.routing_key = "user.auth.success"
        payload.routing_info.priority = "high"

        # Verify authentication event structure
        assert payload.event_type == EnumEventType.USER
        assert payload.event_data.user_action == "authentication"
        assert payload.event_data.session_context.authentication_method == "oauth2"
        assert payload.event_data.context.environment == "production"
        assert payload.routing_info.routing_key == "user.auth.success"

    def test_system_error_event(self):
        """Test system error event payload pattern."""
        event_data = ModelErrorEventData(
            event_type=EnumEventType.ERROR,
            error_type="DB_CONNECTION_TIMEOUT",
            error_message="Database connection timed out after 30 seconds",
            stack_trace="Error at line 42 in database.py\nConnection.connect()",
            recovery_actions=["retry_connection", "check_db_status", "alert_oncall"],
            impact_assessment={
                "severity": "high",
                "users_affected": "all",
                "services_impacted": "user-profile,orders",
            },
        )
        event_data.context.environment = "production"
        event_data.attributes.category = "database"
        event_data.attributes.importance = "high"
        event_data.source_info.service_name = "user-profile-service"
        event_data.source_info.host_name = "profile-srv-03"

        payload = ModelEventPayload(
            event_type=EnumEventType.ERROR,
            event_data=event_data,
        )
        payload.routing_info.target_queue = "error-alerts"
        payload.routing_info.priority = "high"

        # Verify error event structure
        assert payload.event_type == EnumEventType.ERROR
        assert payload.event_data.error_type == "DB_CONNECTION_TIMEOUT"
        assert payload.event_data.impact_assessment["severity"] == "high"
        assert len(payload.event_data.recovery_actions) == 3

    def test_workflow_execution_event(self):
        """Test workflow execution event payload pattern."""
        event_data = ModelWorkflowEventData(
            event_type=EnumEventType.WORKFLOW,
            workflow_stage="processing",
            workflow_step="data_validation",
            execution_metrics={
                "records_processed": 15420,
                "duration_ms": 5250.5,
                "success_rate": 98.7,
            },
            state_changes={
                "status": ModelSchemaValue.from_value("completed"),
                "progress": ModelSchemaValue.from_value(100),
            },
        )
        event_data.context.environment = "production"
        event_data.attributes.category = "business_workflow"
        event_data.source_info.service_name = "workflow-engine"

        payload = ModelEventPayload(
            event_type=EnumEventType.WORKFLOW,
            event_data=event_data,
        )
        payload.routing_info.target_queue = "workflow-events"

        # Verify workflow event structure
        assert payload.event_type == EnumEventType.WORKFLOW
        assert payload.event_data.workflow_stage == "processing"
        assert payload.event_data.execution_metrics["records_processed"] == 15420
        assert payload.event_data.state_changes["status"].to_value() == "completed"

    def test_event_payload_modification_workflow(self):
        """Test modifying event payload through workflow stages."""
        # Start with basic system event
        event_data = ModelSystemEventData(
            event_type=EnumEventType.SYSTEM,
            system_component="order-processor",
            severity_level="info",
        )

        payload = ModelEventPayload(
            event_type=EnumEventType.SYSTEM,
            event_data=event_data,
        )

        # Stage 1: Add processing context
        payload.event_data.context.environment = "production"
        payload.event_data.attributes.category = "order_processing"

        # Stage 2: Add diagnostic data
        payload.event_data.diagnostic_data = {
            "orders_processed": ModelSchemaValue.from_value(150),
            "avg_processing_time": ModelSchemaValue.from_value(250.5),
        }

        # Stage 3: Update routing
        payload.routing_info.target_queue = "analytics"
        payload.routing_info.priority = "normal"

        # Verify final enriched payload
        assert payload.event_data.system_component == "order-processor"
        assert payload.event_data.context.environment == "production"
        assert payload.event_data.diagnostic_data["orders_processed"].to_value() == 150
        assert payload.routing_info.target_queue == "analytics"
