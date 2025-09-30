"""
Tests for ModelEventPayload structure.

Validates event payload functionality including data handling, context management,
serialization, and ONEX strong typing compliance.
"""

import json

import pytest
from pydantic import ValidationError

from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.operations.model_event_payload import ModelEventPayload


class TestModelEventPayload:
    """Test basic event payload functionality."""

    def test_default_creation(self):
        """Test creating event payload with default values."""
        payload = ModelEventPayload()

        assert payload.event_data == {}
        assert payload.context == {}
        assert payload.attributes == {}
        assert payload.source_info == {}
        assert payload.routing_info == {}

    def test_creation_with_data(self):
        """Test creating event payload with initial data."""
        event_data = {
            "user_id": ModelSchemaValue.from_value(12345),
            "action": ModelSchemaValue.from_value("user_login"),
            "timestamp": ModelSchemaValue.from_value("2024-01-01T12:00:00Z"),
        }

        context = {
            "session_id": "abc123",
            "request_id": "req-456",
            "user_agent": "Mozilla/5.0",
        }

        attributes = {
            "severity": "info",
            "category": "authentication",
            "priority": "high",
        }

        source_info = {
            "service": "auth-service",
            "version": "1.2.3",
            "instance": "auth-01",
        }

        routing_info = {
            "destination": "user-analytics",
            "routing_key": "user.login",
            "exchange": "events",
        }

        payload = ModelEventPayload(
            event_data=event_data,
            context=context,
            attributes=attributes,
            source_info=source_info,
            routing_info=routing_info,
        )

        assert payload.event_data["user_id"].to_value() == 12345
        assert payload.event_data["action"].to_value() == "user_login"
        assert payload.context["session_id"] == "abc123"
        assert payload.attributes["severity"] == "info"
        assert payload.source_info["service"] == "auth-service"
        assert payload.routing_info["destination"] == "user-analytics"

    def test_event_data_with_various_types(self):
        """Test event data with various ModelSchemaValue types."""
        payload = ModelEventPayload()

        # Add different types of event data
        payload.event_data["string_value"] = ModelSchemaValue.from_value("test_string")
        payload.event_data["int_value"] = ModelSchemaValue.from_value(42)
        payload.event_data["float_value"] = ModelSchemaValue.from_value(3.14159)
        payload.event_data["bool_value"] = ModelSchemaValue.from_value(True)
        payload.event_data["list_value"] = ModelSchemaValue.from_value(
            ["item1", "item2", "item3"],
        )
        payload.event_data["dict_value"] = ModelSchemaValue.from_value(
            {"nested": "data"},
        )
        payload.event_data["none_value"] = ModelSchemaValue.from_value(None)

        assert payload.event_data["string_value"].to_value() == "test_string"
        assert payload.event_data["int_value"].to_value() == 42
        assert payload.event_data["float_value"].to_value() == 3.14159
        assert payload.event_data["bool_value"].to_value() is True
        assert payload.event_data["list_value"].to_value() == [
            "item1",
            "item2",
            "item3",
        ]
        assert payload.event_data["dict_value"].to_value() == {"nested": "data"}
        assert payload.event_data["none_value"].to_value() is None

    def test_context_information_management(self):
        """Test context information handling."""
        payload = ModelEventPayload()

        # Add context information
        payload.context["request_id"] = "req-123"
        payload.context["correlation_id"] = "corr-456"
        payload.context["user_context"] = "authenticated"
        payload.context["trace_id"] = "trace-789"

        assert len(payload.context) == 4
        assert payload.context["request_id"] == "req-123"
        assert payload.context["correlation_id"] == "corr-456"
        assert payload.context["user_context"] == "authenticated"
        assert payload.context["trace_id"] == "trace-789"

    def test_attributes_management(self):
        """Test event attributes handling."""
        payload = ModelEventPayload()

        # Add event attributes
        payload.attributes["priority"] = "high"
        payload.attributes["category"] = "business_event"
        payload.attributes["tags"] = "user,authentication,login"
        payload.attributes["environment"] = "production"

        assert payload.attributes["priority"] == "high"
        assert payload.attributes["category"] == "business_event"
        assert payload.attributes["tags"] == "user,authentication,login"
        assert payload.attributes["environment"] == "production"

    def test_source_info_tracking(self):
        """Test source information tracking."""
        payload = ModelEventPayload()

        # Add source information
        payload.source_info["service_name"] = "user-service"
        payload.source_info["service_version"] = "2.1.0"
        payload.source_info["hostname"] = "user-service-01"
        payload.source_info["pod_name"] = "user-service-deployment-abc123"
        payload.source_info["namespace"] = "production"

        assert payload.source_info["service_name"] == "user-service"
        assert payload.source_info["service_version"] == "2.1.0"
        assert payload.source_info["hostname"] == "user-service-01"
        assert payload.source_info["pod_name"] == "user-service-deployment-abc123"
        assert payload.source_info["namespace"] == "production"

    def test_routing_info_management(self):
        """Test routing information management."""
        payload = ModelEventPayload()

        # Add routing information
        payload.routing_info["exchange"] = "events_exchange"
        payload.routing_info["routing_key"] = "user.profile.updated"
        payload.routing_info["queue"] = "analytics_queue"
        payload.routing_info["delivery_mode"] = "persistent"

        assert payload.routing_info["exchange"] == "events_exchange"
        assert payload.routing_info["routing_key"] == "user.profile.updated"
        assert payload.routing_info["queue"] == "analytics_queue"
        assert payload.routing_info["delivery_mode"] == "persistent"


class TestModelEventPayloadSerialization:
    """Test serialization and deserialization capabilities."""

    def test_json_serialization(self):
        """Test JSON serialization of event payload."""
        payload = ModelEventPayload(
            event_data={
                "user_id": ModelSchemaValue.from_value(12345),
                "action": ModelSchemaValue.from_value("profile_update"),
            },
            context={"session_id": "sess_123", "ip_address": "192.168.1.100"},
            attributes={"priority": "medium", "category": "user_event"},
            source_info={"service": "profile-service", "version": "1.0.0"},
            routing_info={"destination": "audit-service", "routing_key": "user.audit"},
        )

        # Serialize to dictionary
        serialized = payload.model_dump()

        assert "event_data" in serialized
        assert "context" in serialized
        assert "attributes" in serialized
        assert "source_info" in serialized
        assert "routing_info" in serialized

        # Check event_data serialization (ModelSchemaValue objects)
        assert serialized["event_data"]["user_id"]["number_value"]["value"] == 12345.0
        assert serialized["event_data"]["action"]["string_value"] == "profile_update"

        # Check other fields (simple strings)
        assert serialized["context"]["session_id"] == "sess_123"
        assert serialized["attributes"]["priority"] == "medium"
        assert serialized["source_info"]["service"] == "profile-service"
        assert serialized["routing_info"]["destination"] == "audit-service"

    def test_json_deserialization(self):
        """Test JSON deserialization of event payload."""
        json_data = {
            "event_data": {
                "operation": {
                    "string_value": "delete_user",
                    "number_value": None,
                    "boolean_value": None,
                    "null_value": None,
                    "array_value": None,
                    "object_value": None,
                    "value_type": "string",
                },
                "target_id": {
                    "string_value": None,
                    "number_value": {
                        "value": 67890.0,
                        "value_type": "float",
                        "is_validated": True,
                        "source": None,
                    },
                    "boolean_value": None,
                    "null_value": None,
                    "array_value": None,
                    "object_value": None,
                    "value_type": "number",
                },
            },
            "context": {"admin_user": "admin@company.com", "reason": "account_cleanup"},
            "attributes": {"severity": "high", "requires_approval": "true"},
            "source_info": {"service": "admin-service", "version": "2.0.0"},
            "routing_info": {
                "approval_queue": "admin_approvals",
                "notification_targets": "admin_team",
            },
        }

        payload = ModelEventPayload.model_validate(json_data)

        # Verify event data
        assert payload.event_data["operation"].to_value() == "delete_user"
        assert payload.event_data["target_id"].to_value() == 67890

        # Verify other sections
        assert payload.context["admin_user"] == "admin@company.com"
        assert payload.attributes["severity"] == "high"
        assert payload.source_info["service"] == "admin-service"
        assert payload.routing_info["approval_queue"] == "admin_approvals"

    def test_round_trip_serialization(self):
        """Test full round-trip serialization."""
        original = ModelEventPayload(
            event_data={
                "metric_name": ModelSchemaValue.from_value("response_time"),
                "metric_value": ModelSchemaValue.from_value(150.75),
                "tags": ModelSchemaValue.from_value(["performance", "api", "prod"]),
            },
            context={"environment": "production", "region": "us-west-2"},
            attributes={"alert_threshold": "200", "measurement_unit": "milliseconds"},
            source_info={"collector": "prometheus", "scrape_interval": "30s"},
            routing_info={"metrics_store": "influxdb", "retention_policy": "30d"},
        )

        # Serialize to JSON string
        json_str = original.model_dump_json()

        # Parse JSON and create new instance
        json_data = json.loads(json_str)
        deserialized = ModelEventPayload.model_validate(json_data)

        # Verify all fields match
        assert deserialized.event_data["metric_name"].to_value() == "response_time"
        assert deserialized.event_data["metric_value"].to_value() == 150.75
        assert deserialized.event_data["tags"].to_value() == [
            "performance",
            "api",
            "prod",
        ]
        assert deserialized.context["environment"] == "production"
        assert deserialized.attributes["alert_threshold"] == "200"
        assert deserialized.source_info["collector"] == "prometheus"
        assert deserialized.routing_info["metrics_store"] == "influxdb"


class TestModelEventPayloadValidation:
    """Test validation and error handling."""

    def test_valid_payload_creation(self):
        """Test that valid payloads are created successfully."""
        # All fields optional, so empty payload should be valid
        payload = ModelEventPayload()
        assert isinstance(payload, ModelEventPayload)

        # Payload with all fields should also be valid
        payload_full = ModelEventPayload(
            event_data={"key": ModelSchemaValue.from_value("value")},
            context={"ctx": "value"},
            attributes={"attr": "value"},
            source_info={"src": "value"},
            routing_info={"route": "value"},
        )
        assert isinstance(payload_full, ModelEventPayload)

    def test_invalid_event_data_type(self):
        """Test validation error for invalid event_data type."""
        with pytest.raises(ValidationError):
            # event_data should be dict[str, ModelSchemaValue], not dict[str, str]
            ModelEventPayload(
                event_data={
                    "key": "raw_string_not_schema_value",
                },  # Should be ModelSchemaValue
            )

    def test_invalid_context_type(self):
        """Test validation error for invalid context type."""
        with pytest.raises(ValidationError):
            # context should be dict[str, str], not dict[str, int]
            ModelEventPayload(context={"key": 123})  # Should be string

    def test_invalid_attributes_type(self):
        """Test validation error for invalid attributes type."""
        with pytest.raises(ValidationError):
            # attributes should be dict[str, str]
            ModelEventPayload(
                attributes={"key": ["list", "not", "string"]},  # Should be string
            )

    def test_field_type_validation(self):
        """Test field type validation for all sections."""
        # Valid payload
        valid_payload = ModelEventPayload(
            event_data={"valid_data": ModelSchemaValue.from_value("test")},
            context={"valid_context": "string_value"},
            attributes={"valid_attr": "string_value"},
            source_info={"valid_source": "string_value"},
            routing_info={"valid_routing": "string_value"},
        )

        assert len(valid_payload.event_data) == 1
        assert len(valid_payload.context) == 1
        assert len(valid_payload.attributes) == 1
        assert len(valid_payload.source_info) == 1
        assert len(valid_payload.routing_info) == 1


class TestModelEventPayloadUsagePatterns:
    """Test real-world usage patterns and integration scenarios."""

    def test_user_authentication_event(self):
        """Test user authentication event payload pattern."""
        auth_payload = ModelEventPayload(
            event_data={
                "user_id": ModelSchemaValue.from_value("user_12345"),
                "authentication_method": ModelSchemaValue.from_value("oauth2"),
                "success": ModelSchemaValue.from_value(True),
                "attempt_count": ModelSchemaValue.from_value(1),
                "client_info": ModelSchemaValue.from_value(
                    {
                        "client_id": "mobile_app_v2",
                        "client_version": "2.1.0",
                        "platform": "ios",
                    },
                ),
            },
            context={
                "session_id": "sess_abc123def456",
                "request_id": "req_789012ghi345",
                "ip_address": "192.168.1.100",
                "user_agent": "MyApp/2.1.0 (iOS 17.0)",
            },
            attributes={
                "event_type": "authentication",
                "category": "security",
                "severity": "info",
                "tags": "auth,mobile,oauth2",
            },
            source_info={
                "service": "authentication-service",
                "version": "3.2.1",
                "hostname": "auth-server-01",
                "environment": "production",
            },
            routing_info={
                "destination_services": "analytics,audit,notification",
                "routing_key": "user.auth.success",
                "priority": "normal",
            },
        )

        # Verify authentication event structure
        assert auth_payload.event_data["user_id"].to_value() == "user_12345"
        assert auth_payload.event_data["success"].to_value() is True
        assert auth_payload.context["ip_address"] == "192.168.1.100"
        assert auth_payload.attributes["event_type"] == "authentication"
        assert auth_payload.source_info["service"] == "authentication-service"
        assert "analytics" in auth_payload.routing_info["destination_services"]

    def test_system_error_event(self):
        """Test system error event payload pattern."""
        error_payload = ModelEventPayload(
            event_data={
                "error_code": ModelSchemaValue.from_value("DB_CONNECTION_TIMEOUT"),
                "error_message": ModelSchemaValue.from_value(
                    "Database connection timed out after 30 seconds",
                ),
                "stack_trace": ModelSchemaValue.from_value(
                    "Error at line 42 in database.py",
                ),
                "affected_operation": ModelSchemaValue.from_value("user_profile_fetch"),
                "duration_ms": ModelSchemaValue.from_value(30000),
            },
            context={
                "request_id": "req_error_123",
                "correlation_id": "corr_error_456",
                "user_id": "user_affected_789",
            },
            attributes={
                "event_type": "system_error",
                "severity": "high",
                "category": "database",
                "alert_required": "true",
            },
            source_info={
                "service": "user-profile-service",
                "version": "1.5.2",
                "hostname": "profile-srv-03",
                "pod_name": "profile-deployment-xyz789",
            },
            routing_info={
                "alert_manager": "prometheus_alertmanager",
                "oncall_notification": "enabled",
                "escalation_policy": "database_errors",
            },
        )

        # Verify error event structure
        assert (
            error_payload.event_data["error_code"].to_value() == "DB_CONNECTION_TIMEOUT"
        )
        assert error_payload.event_data["duration_ms"].to_value() == 30000
        assert error_payload.attributes["severity"] == "high"
        assert error_payload.attributes["alert_required"] == "true"
        assert error_payload.routing_info["oncall_notification"] == "enabled"

    def test_business_metrics_event(self):
        """Test business metrics event payload pattern."""
        metrics_payload = ModelEventPayload(
            event_data={
                "metric_family": ModelSchemaValue.from_value("business_kpis"),
                "metric_name": ModelSchemaValue.from_value("daily_active_users"),
                "metric_value": ModelSchemaValue.from_value(15420),
                "measurement_time": ModelSchemaValue.from_value("2024-01-01T23:59:59Z"),
                "dimensions": ModelSchemaValue.from_value(
                    {"region": "us-west", "platform": "web", "user_segment": "premium"},
                ),
            },
            context={
                "collection_job_id": "daily_metrics_20240101",
                "data_source": "user_activity_aggregator",
                "collection_timestamp": "2024-01-02T00:15:00Z",
            },
            attributes={
                "event_type": "business_metrics",
                "frequency": "daily",
                "data_quality": "verified",
                "retention_days": "365",
            },
            source_info={
                "service": "metrics-collector",
                "version": "4.1.0",
                "collector_type": "batch_processor",
            },
            routing_info={
                "metrics_store": "timeseries_db",
                "dashboard_refresh": "enabled",
                "alert_evaluation": "scheduled",
            },
        )

        # Verify metrics event structure
        assert (
            metrics_payload.event_data["metric_name"].to_value() == "daily_active_users"
        )
        assert metrics_payload.event_data["metric_value"].to_value() == 15420
        assert (
            metrics_payload.event_data["dimensions"].to_value()["region"] == "us-west"
        )
        assert metrics_payload.attributes["retention_days"] == "365"
        assert metrics_payload.routing_info["metrics_store"] == "timeseries_db"

    def test_event_payload_modification_workflow(self):
        """Test modifying event payload through workflow stages."""
        # Start with basic event
        payload = ModelEventPayload(
            event_data={"base_event": ModelSchemaValue.from_value("order_created")},
            context={"initial_context": "basic"},
        )

        # Stage 1: Enrich with processing context
        payload.context["processing_stage"] = "validation"
        payload.context["processor_id"] = "validator_01"
        payload.attributes["validation_status"] = "pending"

        # Stage 2: Add validation results
        payload.event_data["validation_result"] = ModelSchemaValue.from_value("passed")
        payload.attributes["validation_status"] = "completed"
        payload.context["processing_stage"] = "enrichment"

        # Stage 3: Add enrichment data
        payload.event_data["customer_tier"] = ModelSchemaValue.from_value("premium")
        payload.event_data["fulfillment_center"] = ModelSchemaValue.from_value(
            "west_coast",
        )
        payload.context["processing_stage"] = "routing"

        # Stage 4: Add routing information
        payload.routing_info["fulfillment_queue"] = "premium_orders"
        payload.routing_info["notification_targets"] = "customer,fulfillment"
        payload.routing_info["priority"] = "high"

        # Verify final enriched payload
        assert payload.event_data["base_event"].to_value() == "order_created"
        assert payload.event_data["validation_result"].to_value() == "passed"
        assert payload.event_data["customer_tier"].to_value() == "premium"
        assert payload.context["processing_stage"] == "routing"
        assert payload.attributes["validation_status"] == "completed"
        assert payload.routing_info["priority"] == "high"
