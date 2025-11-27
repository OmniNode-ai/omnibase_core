"""
Unit tests for event_types constants module.

Tests cover:
- Event type constants are all defined
- Event types have unique values
- Event types are used correctly in event models
- Event type serialization
- normalize_legacy_event_type function behavior
"""


class TestEventTypeConstants:
    """Test event type constant definitions."""

    def test_event_types_all_defined(self):
        """Test that all expected event type constants are defined."""
        from omnibase_core.constants import event_types

        # Tool-related events
        assert hasattr(event_types, "TOOL_INVOCATION")
        assert hasattr(event_types, "TOOL_RESPONSE")
        assert hasattr(event_types, "TOOL_DISCOVERY_REQUEST")
        assert hasattr(event_types, "TOOL_DISCOVERY_RESPONSE")

        # Introspection and discovery events
        assert hasattr(event_types, "NODE_INTROSPECTION_EVENT")
        assert hasattr(event_types, "REQUEST_REAL_TIME_INTROSPECTION")
        assert hasattr(event_types, "REAL_TIME_INTROSPECTION_RESPONSE")

        # Additional core events
        assert hasattr(event_types, "NODE_HEALTH_CHECK")
        assert hasattr(event_types, "NODE_HEALTH_EVENT")
        assert hasattr(event_types, "NODE_SHUTDOWN_EVENT")
        assert hasattr(event_types, "SERVICE_DISCOVERY")

        # Node lifecycle events
        assert hasattr(event_types, "NODE_START")
        assert hasattr(event_types, "NODE_SUCCESS")
        assert hasattr(event_types, "NODE_FAILURE")

    def test_event_types_unique_values(self):
        """Test that all event type constants have unique values."""
        from omnibase_core.constants import event_types

        event_type_values = [
            event_types.TOOL_INVOCATION,
            event_types.TOOL_RESPONSE,
            event_types.TOOL_DISCOVERY_REQUEST,
            event_types.TOOL_DISCOVERY_RESPONSE,
            event_types.NODE_INTROSPECTION_EVENT,
            event_types.REQUEST_REAL_TIME_INTROSPECTION,
            event_types.REAL_TIME_INTROSPECTION_RESPONSE,
            event_types.NODE_HEALTH_CHECK,
            event_types.NODE_HEALTH_EVENT,
            event_types.NODE_SHUTDOWN_EVENT,
            event_types.SERVICE_DISCOVERY,
            event_types.NODE_START,
            event_types.NODE_SUCCESS,
            event_types.NODE_FAILURE,
        ]

        # All values should be unique
        assert len(event_type_values) == len(set(event_type_values))

    def test_event_types_are_strings(self):
        """Test that all event type constants are strings."""
        from omnibase_core.constants import event_types

        event_type_constants = [
            event_types.TOOL_INVOCATION,
            event_types.TOOL_RESPONSE,
            event_types.TOOL_DISCOVERY_REQUEST,
            event_types.TOOL_DISCOVERY_RESPONSE,
            event_types.NODE_INTROSPECTION_EVENT,
            event_types.REQUEST_REAL_TIME_INTROSPECTION,
            event_types.REAL_TIME_INTROSPECTION_RESPONSE,
            event_types.NODE_HEALTH_CHECK,
            event_types.NODE_HEALTH_EVENT,
            event_types.NODE_SHUTDOWN_EVENT,
            event_types.SERVICE_DISCOVERY,
            event_types.NODE_START,
            event_types.NODE_SUCCESS,
            event_types.NODE_FAILURE,
        ]

        for event_type in event_type_constants:
            assert isinstance(event_type, str)

    def test_event_types_follow_naming_convention(self):
        """Test that event type values follow snake_case convention."""
        from omnibase_core.constants import event_types

        event_type_values = [
            event_types.TOOL_INVOCATION,
            event_types.TOOL_RESPONSE,
            event_types.NODE_INTROSPECTION_EVENT,
            event_types.NODE_HEALTH_CHECK,
            event_types.NODE_START,
        ]

        for event_type in event_type_values:
            # Should be lowercase with underscores (snake_case)
            assert event_type.islower() or "_" in event_type
            assert " " not in event_type  # No spaces


class TestEventTypeSpecificValues:
    """Test specific event type constant values."""

    def test_tool_event_types(self):
        """Test tool-related event type values."""
        from omnibase_core.constants import event_types

        assert event_types.TOOL_INVOCATION == "tool_invocation"
        assert event_types.TOOL_RESPONSE == "tool_response"
        assert event_types.TOOL_DISCOVERY_REQUEST == "tool_discovery_request"
        assert event_types.TOOL_DISCOVERY_RESPONSE == "tool_discovery_response"

    def test_introspection_event_types(self):
        """Test introspection-related event type values."""
        from omnibase_core.constants import event_types

        assert event_types.NODE_INTROSPECTION_EVENT == "node_introspection_event"
        assert (
            event_types.REQUEST_REAL_TIME_INTROSPECTION
            == "request_real_time_introspection"
        )
        assert (
            event_types.REAL_TIME_INTROSPECTION_RESPONSE
            == "real_time_introspection_response"
        )

    def test_health_event_types(self):
        """Test health-related event type values."""
        from omnibase_core.constants import event_types

        assert event_types.NODE_HEALTH_CHECK == "node_health_check"
        assert event_types.NODE_HEALTH_EVENT == "node_health_event"
        assert event_types.NODE_SHUTDOWN_EVENT == "node_shutdown_event"

    def test_lifecycle_event_types(self):
        """Test lifecycle event type values."""
        from omnibase_core.constants import event_types

        assert event_types.NODE_START == "node_start"
        assert event_types.NODE_SUCCESS == "node_success"
        assert event_types.NODE_FAILURE == "node_failure"


class TestNormalizeLegacyEventType:
    """Test normalize_legacy_event_type function."""

    def test_normalize_legacy_event_type_with_string(self):
        """Test normalization with string input."""
        from omnibase_core.constants.event_types import normalize_legacy_event_type

        result = normalize_legacy_event_type("tool_invocation")
        assert result == "tool_invocation"
        assert isinstance(result, str)

    def test_normalize_legacy_event_type_with_object_value_attribute(self):
        """Test normalization with object having .value attribute."""
        from omnibase_core.constants.event_types import normalize_legacy_event_type

        class MockEventType:
            def __init__(self, value):
                self.value = value

        event_obj = MockEventType("tool_response")
        result = normalize_legacy_event_type(event_obj)

        assert result == "tool_response"
        assert isinstance(result, str)

    def test_normalize_legacy_event_type_with_dict_value_key(self):
        """Test normalization with dict containing 'value' key."""
        from omnibase_core.constants.event_types import normalize_legacy_event_type

        event_dict = {"value": "node_health_event"}
        result = normalize_legacy_event_type(event_dict)

        assert result == "node_health_event"
        assert isinstance(result, str)

    def test_normalize_legacy_event_type_with_dict_event_type_key(self):
        """Test normalization with dict containing 'event_type' key."""
        from omnibase_core.constants.event_types import normalize_legacy_event_type

        event_dict = {"event_type": "node_start"}
        result = normalize_legacy_event_type(event_dict)

        assert result == "node_start"
        assert isinstance(result, str)

    def test_normalize_legacy_event_type_with_fallback_to_string(self):
        """Test normalization falls back to str() for unknown types."""
        from omnibase_core.constants.event_types import normalize_legacy_event_type

        class UnknownType:
            def __str__(self):
                return "custom_event"

        result = normalize_legacy_event_type(UnknownType())
        assert result == "custom_event"
        assert isinstance(result, str)

    def test_normalize_legacy_event_type_with_numeric_value(self):
        """Test normalization with numeric input (fallback to string)."""
        from omnibase_core.constants.event_types import normalize_legacy_event_type

        result = normalize_legacy_event_type(42)
        assert result == "42"
        assert isinstance(result, str)

    def test_normalize_legacy_event_type_preserves_string_value(self):
        """Test that string values are returned unchanged."""
        from omnibase_core.constants.event_types import normalize_legacy_event_type

        test_strings = [
            "tool_invocation",
            "node_health_event",
            "custom_event_type",
        ]

        for test_str in test_strings:
            result = normalize_legacy_event_type(test_str)
            assert result == test_str
            assert result is test_str  # Same object


class TestNormalizeLegacyEventTypeEdgeCases:
    """Test edge cases for normalize_legacy_event_type."""

    def test_normalize_legacy_event_type_with_empty_string(self):
        """Test normalization with empty string."""
        from omnibase_core.constants.event_types import normalize_legacy_event_type

        result = normalize_legacy_event_type("")
        assert result == ""
        assert isinstance(result, str)

    def test_normalize_legacy_event_type_with_none(self):
        """Test normalization with None value."""
        from omnibase_core.constants.event_types import normalize_legacy_event_type

        result = normalize_legacy_event_type(None)
        assert result == "None"
        assert isinstance(result, str)

    def test_normalize_legacy_event_type_with_dict_priority(self):
        """Test that 'value' key takes priority over 'event_type' in dict."""
        from omnibase_core.constants.event_types import normalize_legacy_event_type

        event_dict = {
            "value": "should_use_this",
            "event_type": "not_this",
        }
        result = normalize_legacy_event_type(event_dict)

        assert result == "should_use_this"

    def test_normalize_legacy_event_type_with_empty_dict(self):
        """Test normalization with empty dict."""
        from omnibase_core.constants.event_types import normalize_legacy_event_type

        result = normalize_legacy_event_type({})
        assert isinstance(result, str)
        # Should fall back to str({})

    def test_normalize_legacy_event_type_with_complex_object(self):
        """Test normalization with complex nested object."""
        from omnibase_core.constants.event_types import normalize_legacy_event_type

        class ComplexEventType:
            def __init__(self):
                self.value = "complex_event"
                self.metadata = {"key": "value"}

        complex_obj = ComplexEventType()
        result = normalize_legacy_event_type(complex_obj)

        assert result == "complex_event"


class TestEventTypeSerialization:
    """Test event type serialization and usage."""

    def test_event_types_serialization(self):
        """Test that event types can be serialized to JSON."""
        import json

        from omnibase_core.constants import event_types

        event_data = {
            "event_type": event_types.TOOL_INVOCATION,
            "timestamp": "2024-01-01T00:00:00Z",
        }

        # Should serialize without errors
        serialized = json.dumps(event_data)
        assert isinstance(serialized, str)

        # Should deserialize correctly
        deserialized = json.loads(serialized)
        assert deserialized["event_type"] == "tool_invocation"

    def test_event_types_in_lists(self):
        """Test event types work correctly in lists and sets."""
        from omnibase_core.constants import event_types

        event_list = [
            event_types.NODE_START,
            event_types.NODE_SUCCESS,
            event_types.NODE_FAILURE,
        ]

        assert len(event_list) == 3
        assert event_types.NODE_START in event_list
        assert "node_start" in event_list

    def test_event_types_in_dictionaries(self):
        """Test event types work as dictionary keys."""
        from omnibase_core.constants import event_types

        event_handlers = {
            event_types.TOOL_INVOCATION: "handle_invocation",
            event_types.TOOL_RESPONSE: "handle_response",
            event_types.NODE_HEALTH_EVENT: "handle_health",
        }

        assert event_handlers[event_types.TOOL_INVOCATION] == "handle_invocation"
        assert len(event_handlers) == 3


class TestEventTypeUsagePatterns:
    """Test common event type usage patterns."""

    def test_event_type_comparison(self):
        """Test event type comparison operations."""
        from omnibase_core.constants import event_types

        # String comparison should work
        assert event_types.NODE_START == "node_start"
        assert event_types.NODE_SUCCESS != "node_failure"

    def test_event_type_in_conditional(self):
        """Test event types in conditional statements."""
        from omnibase_core.constants import event_types

        def handle_event(event_type):
            if event_type == event_types.NODE_START:
                return "starting"
            elif event_type == event_types.NODE_SUCCESS:
                return "success"
            else:
                return "other"

        assert handle_event(event_types.NODE_START) == "starting"
        assert handle_event(event_types.NODE_SUCCESS) == "success"
        assert handle_event("unknown") == "other"

    def test_event_type_string_operations(self):
        """Test string operations on event types."""
        from omnibase_core.constants import event_types

        # Should support string methods
        assert event_types.NODE_HEALTH_EVENT.startswith("node_")
        assert event_types.TOOL_INVOCATION.endswith("_invocation")
        assert "health" in event_types.NODE_HEALTH_EVENT


class TestEventTypeModuleStructure:
    """Test event_types module structure and documentation."""

    def test_event_types_module_has_docstring(self):
        """Test that event_types module has a docstring."""
        from omnibase_core.constants import event_types

        assert event_types.__doc__ is not None
        assert len(event_types.__doc__) > 0

    def test_event_types_module_docstring_describes_purpose(self):
        """Test that module docstring describes its purpose."""
        from omnibase_core.constants import event_types

        docstring = event_types.__doc__.lower()
        assert "event" in docstring or "onex" in docstring

    def test_normalize_function_has_docstring(self):
        """Test that normalize_legacy_event_type has docstring."""
        from omnibase_core.constants.event_types import normalize_legacy_event_type

        assert normalize_legacy_event_type.__doc__ is not None
        assert len(normalize_legacy_event_type.__doc__) > 0
