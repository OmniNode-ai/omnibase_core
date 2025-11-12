"""
Unit tests for ModelRoutingSubcontract validators.

Tests validator conversion from @field_validator to @model_validator(mode="after").
"""

import pytest

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.contracts.subcontracts.model_route_definition import (
    ModelRouteDefinition,
)
from omnibase_core.models.contracts.subcontracts.model_routing_subcontract import (
    ModelRoutingSubcontract,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError


class TestRoutingSubcontractValidators:
    """Test ModelRoutingSubcontract validators."""

    def test_valid_routing_subcontract_default(self):
        """Test creating routing subcontract with defaults."""
        subcontract = ModelRoutingSubcontract()

        assert subcontract.routing_enabled is True
        assert subcontract.routing_strategy == "service_mesh_aware"
        assert subcontract.routes == []
        assert subcontract.trace_sampling_rate == 0.1

    def test_valid_routing_with_unique_priorities(self):
        """Test routing with unique priorities per pattern."""
        route1 = ModelRouteDefinition(
            route_name="route1",
            route_pattern="/api/v1",
            priority=1,
            service_targets=["service1"],
        )
        route2 = ModelRouteDefinition(
            route_name="route2",
            route_pattern="/api/v1",
            priority=2,
            service_targets=["service2"],
        )

        subcontract = ModelRoutingSubcontract(routes=[route1, route2])

        assert len(subcontract.routes) == 2
        assert subcontract.routes[0].priority == 1
        assert subcontract.routes[1].priority == 2

    def test_duplicate_priority_same_pattern_raises_error(self):
        """Test that duplicate priorities in same pattern raise validation error."""
        route1 = ModelRouteDefinition(
            route_name="route1",
            route_pattern="/api/v1",
            priority=1,
            service_targets=["service1"],
        )
        route2 = ModelRouteDefinition(
            route_name="route2",
            route_pattern="/api/v1",
            priority=1,  # Duplicate priority
            service_targets=["service2"],
        )

        with pytest.raises(ModelOnexError) as exc_info:
            ModelRoutingSubcontract(routes=[route1, route2])

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "Duplicate priority" in exc_info.value.message
        assert exc_info.value.model.context["pattern"] == "/api/v1"
        assert exc_info.value.model.context["priority"] == 1

    def test_same_priority_different_patterns_allowed(self):
        """Test that same priority across different patterns is allowed."""
        route1 = ModelRouteDefinition(
            route_name="route1",
            route_pattern="/api/v1",
            priority=1,
            service_targets=["service1"],
        )
        route2 = ModelRouteDefinition(
            route_name="route2",
            route_pattern="/api/v2",
            priority=1,  # Same priority but different pattern
            service_targets=["service2"],
        )

        subcontract = ModelRoutingSubcontract(routes=[route1, route2])

        assert len(subcontract.routes) == 2
        assert subcontract.routes[0].priority == 1
        assert subcontract.routes[1].priority == 1
        assert (
            subcontract.routes[0].route_pattern != subcontract.routes[1].route_pattern
        )

    def test_valid_trace_sampling_rate_low(self):
        """Test valid low trace sampling rate."""
        subcontract = ModelRoutingSubcontract(trace_sampling_rate=0.1)

        assert subcontract.trace_sampling_rate == 0.1

    def test_valid_trace_sampling_rate_max_allowed(self):
        """Test valid trace sampling rate at maximum allowed (0.5)."""
        subcontract = ModelRoutingSubcontract(trace_sampling_rate=0.5)

        assert subcontract.trace_sampling_rate == 0.5

    def test_trace_sampling_rate_above_threshold_raises_error(self):
        """Test that trace sampling rate above 50% raises validation error."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelRoutingSubcontract(trace_sampling_rate=0.6)

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "sampling rate above 50%" in exc_info.value.message.lower()
        assert exc_info.value.model.context["sampling_rate"] == 0.6
        assert exc_info.value.model.context["max_recommended"] == 0.5

    def test_trace_sampling_rate_at_100_percent_raises_error(self):
        """Test that 100% trace sampling rate raises validation error."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelRoutingSubcontract(trace_sampling_rate=1.0)

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "sampling rate above 50%" in exc_info.value.message.lower()

    def test_multiple_routes_complex_validation(self):
        """Test complex routing scenario with multiple routes."""
        routes = [
            ModelRouteDefinition(
                route_name="route1",
                route_pattern="/api/v1/users",
                priority=1,
                service_targets=["user_service"],
            ),
            ModelRouteDefinition(
                route_name="route2",
                route_pattern="/api/v1/users",
                priority=2,
                service_targets=["user_service_backup"],
            ),
            ModelRouteDefinition(
                route_name="route3",
                route_pattern="/api/v1/orders",
                priority=1,
                service_targets=["order_service"],
            ),
        ]

        subcontract = ModelRoutingSubcontract(
            routes=routes,
            trace_sampling_rate=0.3,
            routing_strategy="path_based",
        )

        assert len(subcontract.routes) == 3
        assert subcontract.trace_sampling_rate == 0.3
        assert subcontract.routing_strategy == "path_based"

    def test_validator_runs_on_model_update(self):
        """Test that validators run when model is updated (validate_assignment=True)."""
        subcontract = ModelRoutingSubcontract(trace_sampling_rate=0.1)

        # This should raise validation error due to validate_assignment=True
        with pytest.raises(ModelOnexError) as exc_info:
            subcontract.trace_sampling_rate = 0.8

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
