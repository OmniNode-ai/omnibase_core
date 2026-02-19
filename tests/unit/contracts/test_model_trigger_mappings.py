#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

import pytest

"""
ModelTriggerMappings Comprehensive Unit Tests

This module provides comprehensive test coverage for ModelTriggerMappings,
the strongly-typed trigger mappings model for event-to-workflow coordination.

Coverage Requirements:
- >95% line coverage for all methods
- 100% coverage for error handling paths
- Comprehensive validation scenarios
- Method testing for get_all_mappings and add_mapping

Comprehensive testing required for all code paths.
"""

from uuid import UUID

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.contracts.model_trigger_mappings import ModelTriggerMappings
from omnibase_core.models.errors.model_onex_error import ModelOnexError as OnexError


@pytest.mark.unit
class TestModelTriggerMappings:
    """Comprehensive tests for ModelTriggerMappings with full coverage."""

    def setup_method(self):
        """Set up test fixtures for each test method."""

    # =================== VALID CONSTRUCTION TESTS ===================

    def test_valid_construction_defaults(self):
        """Test valid construction with default values."""
        mappings = ModelTriggerMappings()

        assert mappings.correlation_id is not None
        assert isinstance(mappings.correlation_id, UUID)
        assert mappings.event_pattern_mappings == {}
        assert mappings.workflow_start_events == {}
        assert mappings.workflow_stop_events == {}
        assert mappings.workflow_pause_events == {}
        assert mappings.workflow_resume_events == {}
        assert mappings.error_handling_mappings == {}
        assert mappings.compensation_trigger_mappings == {}
        assert mappings.state_change_mappings == {}
        assert mappings.custom_action_mappings == {}
        assert mappings.notification_mappings == {}
        assert mappings.routing_mappings == {}

    def test_valid_construction_with_mappings(self):
        """Test valid construction with populated mappings."""
        mappings = ModelTriggerMappings(
            event_pattern_mappings={"order.created": "start_order_workflow"},
            workflow_start_events={"payment.completed": "workflow_12345"},
            workflow_stop_events={"system.shutdown": "stop_all"},
            workflow_pause_events={"maintenance.scheduled": "pause_workflows"},
            workflow_resume_events={"maintenance.completed": "resume_workflows"},
            error_handling_mappings={"error.payment_failed": "handle_payment_error"},
            compensation_trigger_mappings={
                "compensation.required": "compensation_plan_abc",
            },
            state_change_mappings={"state.pending_to_active": "activate_workflow"},
            custom_action_mappings={"custom.trigger": "custom_action_123"},
            notification_mappings={"notification.send": "email_template_v1"},
            routing_mappings={"route.to_service_a": "service_a_endpoint"},
        )

        assert len(mappings.event_pattern_mappings) == 1
        assert len(mappings.workflow_start_events) == 1
        assert len(mappings.workflow_stop_events) == 1
        assert len(mappings.workflow_pause_events) == 1
        assert len(mappings.workflow_resume_events) == 1
        assert len(mappings.error_handling_mappings) == 1
        assert len(mappings.compensation_trigger_mappings) == 1
        assert len(mappings.state_change_mappings) == 1
        assert len(mappings.custom_action_mappings) == 1
        assert len(mappings.notification_mappings) == 1
        assert len(mappings.routing_mappings) == 1

    def test_correlation_id_auto_generation(self):
        """Test that correlation_id is auto-generated if not provided."""
        mappings1 = ModelTriggerMappings()
        mappings2 = ModelTriggerMappings()

        assert mappings1.correlation_id is not None
        assert mappings2.correlation_id is not None
        assert mappings1.correlation_id != mappings2.correlation_id

    # =================== MAPPING VALIDATION TESTS ===================

    def test_validate_string_mappings_with_valid_data(self):
        """Test mapping validation with valid string-to-string data."""
        mappings = ModelTriggerMappings(
            event_pattern_mappings={
                "event.type.1": "action_1",
                "event.type.2": "action_2",
            },
        )

        assert len(mappings.event_pattern_mappings) == 2
        assert mappings.event_pattern_mappings["event.type.1"] == "action_1"
        assert mappings.event_pattern_mappings["event.type.2"] == "action_2"

    def test_validate_string_mappings_with_whitespace_trimming(self):
        """Test mapping validation trims whitespace from keys and values."""
        mappings = ModelTriggerMappings(
            event_pattern_mappings={
                "  event.key  ": "  action_value  ",
            },
        )

        assert "event.key" in mappings.event_pattern_mappings
        assert mappings.event_pattern_mappings["event.key"] == "action_value"

    def test_validate_string_mappings_skips_empty_keys(self):
        """Test mapping validation skips empty keys."""
        mappings = ModelTriggerMappings(
            event_pattern_mappings={
                "": "should_be_skipped",
                "valid_key": "valid_value",
            },
        )

        assert "valid_key" in mappings.event_pattern_mappings
        assert "" not in mappings.event_pattern_mappings
        assert len(mappings.event_pattern_mappings) == 1

    def test_validate_string_mappings_skips_empty_values(self):
        """Test mapping validation skips empty values."""
        mappings = ModelTriggerMappings(
            event_pattern_mappings={
                "key_with_empty_value": "",
                "key_with_whitespace": "   ",
                "valid_key": "valid_value",
            },
        )

        # Empty values should be skipped
        assert "valid_key" in mappings.event_pattern_mappings
        assert len(mappings.event_pattern_mappings) == 1

    def test_validate_string_mappings_key_too_long(self):
        """Test mapping validation fails when key exceeds 500 characters."""
        long_key = "a" * 501

        with pytest.raises(OnexError) as exc_info:
            ModelTriggerMappings(
                event_pattern_mappings={
                    long_key: "action",
                },
            )

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "too long" in str(exc_info.value)
        assert "Maximum 500 characters" in str(exc_info.value)

    def test_validate_string_mappings_value_too_long(self):
        """Test mapping validation fails when value exceeds 500 characters."""
        long_value = "a" * 501

        with pytest.raises(OnexError) as exc_info:
            ModelTriggerMappings(
                event_pattern_mappings={
                    "event.key": long_value,
                },
            )

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "too long" in str(exc_info.value)
        assert "Maximum 500 characters" in str(exc_info.value)

    def test_validate_string_mappings_value_not_string(self):
        """Test mapping validation fails when value is not a string."""
        # Pydantic validates dict[str, str] type before our custom validator
        with pytest.raises(Exception):  # Pydantic ValidationError
            ModelTriggerMappings(
                event_pattern_mappings={
                    "event.key": 12345,  # Not a string
                },
            )

    def test_validate_all_mapping_types(self):
        """Test validation applies to all mapping field types."""
        # Test each mapping type with valid data
        mappings = ModelTriggerMappings(
            event_pattern_mappings={"event": "action"},
            workflow_start_events={"start": "workflow"},
            workflow_stop_events={"stop": "action"},
            workflow_pause_events={"pause": "action"},
            workflow_resume_events={"resume": "action"},
            error_handling_mappings={"error": "handler"},
            compensation_trigger_mappings={"comp": "plan"},
            state_change_mappings={"state": "action"},
            custom_action_mappings={"custom": "action"},
            notification_mappings={"notify": "template"},
            routing_mappings={"route": "dest"},
        )

        # All should have one entry
        assert len(mappings.event_pattern_mappings) == 1
        assert len(mappings.workflow_start_events) == 1
        assert len(mappings.workflow_stop_events) == 1
        assert len(mappings.workflow_pause_events) == 1
        assert len(mappings.workflow_resume_events) == 1
        assert len(mappings.error_handling_mappings) == 1
        assert len(mappings.compensation_trigger_mappings) == 1
        assert len(mappings.state_change_mappings) == 1
        assert len(mappings.custom_action_mappings) == 1
        assert len(mappings.notification_mappings) == 1
        assert len(mappings.routing_mappings) == 1

    # =================== GET_ALL_MAPPINGS METHOD TESTS ===================

    def test_get_all_mappings_empty(self):
        """Test get_all_mappings returns empty dict when no mappings are set."""
        mappings = ModelTriggerMappings()

        all_mappings = mappings.get_all_mappings()

        assert all_mappings == {}

    def test_get_all_mappings_single_category(self):
        """Test get_all_mappings with one category populated."""
        mappings = ModelTriggerMappings(
            event_pattern_mappings={"event.a": "action_a"},
        )

        all_mappings = mappings.get_all_mappings()

        assert len(all_mappings) == 1
        assert all_mappings["event.a"] == "action_a"

    def test_get_all_mappings_multiple_categories(self):
        """Test get_all_mappings flattens all mapping categories."""
        mappings = ModelTriggerMappings(
            event_pattern_mappings={"event.a": "action_a"},
            workflow_start_events={"start.b": "workflow_b"},
            error_handling_mappings={"error.c": "handler_c"},
            notification_mappings={"notify.d": "template_d"},
        )

        all_mappings = mappings.get_all_mappings()

        assert len(all_mappings) == 4
        assert all_mappings["event.a"] == "action_a"
        assert all_mappings["start.b"] == "workflow_b"
        assert all_mappings["error.c"] == "handler_c"
        assert all_mappings["notify.d"] == "template_d"

    def test_get_all_mappings_overlapping_keys(self):
        """Test get_all_mappings with overlapping keys (later categories override)."""
        mappings = ModelTriggerMappings(
            event_pattern_mappings={"event.key": "action_1"},
            workflow_start_events={"event.key": "action_2"},  # Same key
        )

        all_mappings = mappings.get_all_mappings()

        # Later category should override
        assert all_mappings["event.key"] == "action_2"

    def test_get_all_mappings_comprehensive(self):
        """Test get_all_mappings with all categories populated."""
        mappings = ModelTriggerMappings(
            event_pattern_mappings={"ep.1": "ep_action"},
            workflow_start_events={"ws.2": "ws_action"},
            workflow_stop_events={"wst.3": "wst_action"},
            workflow_pause_events={"wp.4": "wp_action"},
            workflow_resume_events={"wr.5": "wr_action"},
            error_handling_mappings={"eh.6": "eh_action"},
            compensation_trigger_mappings={"ct.7": "ct_action"},
            state_change_mappings={"sc.8": "sc_action"},
            custom_action_mappings={"ca.9": "ca_action"},
            notification_mappings={"nm.10": "nm_action"},
            routing_mappings={"rm.11": "rm_action"},
        )

        all_mappings = mappings.get_all_mappings()

        assert len(all_mappings) == 11
        assert all_mappings["ep.1"] == "ep_action"
        assert all_mappings["ws.2"] == "ws_action"
        assert all_mappings["wst.3"] == "wst_action"
        assert all_mappings["wp.4"] == "wp_action"
        assert all_mappings["wr.5"] == "wr_action"
        assert all_mappings["eh.6"] == "eh_action"
        assert all_mappings["ct.7"] == "ct_action"
        assert all_mappings["sc.8"] == "sc_action"
        assert all_mappings["ca.9"] == "ca_action"
        assert all_mappings["nm.10"] == "nm_action"
        assert all_mappings["rm.11"] == "rm_action"

    # =================== ADD_MAPPING METHOD TESTS ===================

    def test_add_mapping_event_pattern(self):
        """Test add_mapping for event_pattern category."""
        mappings = ModelTriggerMappings()

        mappings.add_mapping("event_pattern", "event.created", "handle_creation")

        assert "event.created" in mappings.event_pattern_mappings
        assert mappings.event_pattern_mappings["event.created"] == "handle_creation"

    def test_add_mapping_workflow_start(self):
        """Test add_mapping for workflow_start category."""
        mappings = ModelTriggerMappings()

        mappings.add_mapping("workflow_start", "trigger.start", "workflow_123")

        assert "trigger.start" in mappings.workflow_start_events
        assert mappings.workflow_start_events["trigger.start"] == "workflow_123"

    def test_add_mapping_workflow_stop(self):
        """Test add_mapping for workflow_stop category."""
        mappings = ModelTriggerMappings()

        mappings.add_mapping("workflow_stop", "trigger.stop", "stop_action")

        assert "trigger.stop" in mappings.workflow_stop_events
        assert mappings.workflow_stop_events["trigger.stop"] == "stop_action"

    def test_add_mapping_workflow_pause(self):
        """Test add_mapping for workflow_pause category."""
        mappings = ModelTriggerMappings()

        mappings.add_mapping("workflow_pause", "trigger.pause", "pause_action")

        assert "trigger.pause" in mappings.workflow_pause_events
        assert mappings.workflow_pause_events["trigger.pause"] == "pause_action"

    def test_add_mapping_workflow_resume(self):
        """Test add_mapping for workflow_resume category."""
        mappings = ModelTriggerMappings()

        mappings.add_mapping("workflow_resume", "trigger.resume", "resume_action")

        assert "trigger.resume" in mappings.workflow_resume_events
        assert mappings.workflow_resume_events["trigger.resume"] == "resume_action"

    def test_add_mapping_error_handling(self):
        """Test add_mapping for error_handling category."""
        mappings = ModelTriggerMappings()

        mappings.add_mapping("error_handling", "error.type", "handle_error")

        assert "error.type" in mappings.error_handling_mappings
        assert mappings.error_handling_mappings["error.type"] == "handle_error"

    def test_add_mapping_compensation(self):
        """Test add_mapping for compensation category."""
        mappings = ModelTriggerMappings()

        mappings.add_mapping("compensation", "comp.trigger", "comp_plan_id")

        assert "comp.trigger" in mappings.compensation_trigger_mappings
        assert mappings.compensation_trigger_mappings["comp.trigger"] == "comp_plan_id"

    def test_add_mapping_state_change(self):
        """Test add_mapping for state_change category."""
        mappings = ModelTriggerMappings()

        mappings.add_mapping("state_change", "state.transition", "state_action")

        assert "state.transition" in mappings.state_change_mappings
        assert mappings.state_change_mappings["state.transition"] == "state_action"

    def test_add_mapping_custom_action(self):
        """Test add_mapping for custom_action category."""
        mappings = ModelTriggerMappings()

        mappings.add_mapping("custom_action", "custom.event", "custom_action_id")

        assert "custom.event" in mappings.custom_action_mappings
        assert mappings.custom_action_mappings["custom.event"] == "custom_action_id"

    def test_add_mapping_notification(self):
        """Test add_mapping for notification category."""
        mappings = ModelTriggerMappings()

        mappings.add_mapping("notification", "notify.event", "template_id")

        assert "notify.event" in mappings.notification_mappings
        assert mappings.notification_mappings["notify.event"] == "template_id"

    def test_add_mapping_routing(self):
        """Test add_mapping for routing category."""
        mappings = ModelTriggerMappings()

        mappings.add_mapping("routing", "route.event", "destination")

        assert "route.event" in mappings.routing_mappings
        assert mappings.routing_mappings["route.event"] == "destination"

    def test_add_mapping_invalid_category(self):
        """Test add_mapping fails with invalid category."""
        mappings = ModelTriggerMappings()

        with pytest.raises(OnexError) as exc_info:
            mappings.add_mapping("invalid_category", "event", "action")

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "Invalid mapping category" in str(exc_info.value)

    def test_add_mapping_with_whitespace_trimming(self):
        """Test add_mapping trims whitespace from event_pattern and action."""
        mappings = ModelTriggerMappings()

        mappings.add_mapping("event_pattern", "  event.key  ", "  action_value  ")

        assert "event.key" in mappings.event_pattern_mappings
        assert mappings.event_pattern_mappings["event.key"] == "action_value"

    def test_add_mapping_multiple_times(self):
        """Test adding multiple mappings to the same category."""
        mappings = ModelTriggerMappings()

        mappings.add_mapping("event_pattern", "event.1", "action.1")
        mappings.add_mapping("event_pattern", "event.2", "action.2")
        mappings.add_mapping("event_pattern", "event.3", "action.3")

        assert len(mappings.event_pattern_mappings) == 3
        assert mappings.event_pattern_mappings["event.1"] == "action.1"
        assert mappings.event_pattern_mappings["event.2"] == "action.2"
        assert mappings.event_pattern_mappings["event.3"] == "action.3"

    # =================== COMPREHENSIVE INTEGRATION TESTS ===================

    def test_complex_trigger_mappings_configuration(self):
        """Test complex trigger mappings configuration with all features."""
        mappings = ModelTriggerMappings(
            event_pattern_mappings={
                "order.created": "start_order_processing",
                "order.updated": "update_order_workflow",
            },
            workflow_start_events={
                "payment.received": "workflow_payment_123",
            },
            workflow_stop_events={
                "system.maintenance": "stop_all_workflows",
            },
            error_handling_mappings={
                "error.payment_declined": "handle_payment_decline",
                "error.service_unavailable": "handle_service_error",
            },
            compensation_trigger_mappings={
                "compensation.order_cancelled": "order_compensation_plan",
            },
        )

        # Verify categories
        assert len(mappings.event_pattern_mappings) == 2
        assert len(mappings.workflow_start_events) == 1
        assert len(mappings.workflow_stop_events) == 1
        assert len(mappings.error_handling_mappings) == 2
        assert len(mappings.compensation_trigger_mappings) == 1

        # Add more mappings dynamically
        mappings.add_mapping("notification", "order.completed", "order_complete_email")
        mappings.add_mapping("routing", "order.ship", "shipping_service")

        # Verify all mappings (2+1+1+2+1 = 7 from construction, +2 from add_mapping = 9 total)
        all_mappings = mappings.get_all_mappings()
        assert len(all_mappings) == 9

    def test_model_config_validate_assignment(self):
        """Test that field assignments are validated as per model_config."""
        mappings = ModelTriggerMappings()

        # This should trigger validation
        with pytest.raises(Exception):
            mappings.event_pattern_mappings = "invalid_not_dict"
