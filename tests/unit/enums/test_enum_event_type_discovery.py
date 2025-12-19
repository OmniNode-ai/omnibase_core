"""
Tests for EnumEventTypeDiscovery enum.
"""

from enum import Enum

import pytest

from omnibase_core.enums.enum_event_type_discovery import EnumEventTypeDiscovery


@pytest.mark.unit
class TestEnumEventTypeDiscovery:
    """Test cases for EnumEventTypeDiscovery enum."""

    def test_enum_values(self):
        """Test that all enum values are correct."""
        assert EnumEventTypeDiscovery.SERVICE_DISCOVERY == "service_discovery"
        assert EnumEventTypeDiscovery.SERVICE_REGISTRATION == "service_registration"
        assert EnumEventTypeDiscovery.SERVICE_DEREGISTRATION == "service_deregistration"
        assert EnumEventTypeDiscovery.CONTAINER_PROVISIONING == "container_provisioning"
        assert EnumEventTypeDiscovery.CONTAINER_HEALTH_CHECK == "container_health_check"
        assert EnumEventTypeDiscovery.MESH_COORDINATION == "mesh_coordination"
        assert EnumEventTypeDiscovery.HUB_STATUS_UPDATE == "hub_status_update"

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumEventTypeDiscovery, str)
        assert issubclass(EnumEventTypeDiscovery, Enum)

    def test_enum_string_behavior(self):
        """Test string behavior of enum values."""
        assert (
            str(EnumEventTypeDiscovery.SERVICE_DISCOVERY)
            == "EnumEventTypeDiscovery.SERVICE_DISCOVERY"
        )
        assert (
            str(EnumEventTypeDiscovery.SERVICE_REGISTRATION)
            == "EnumEventTypeDiscovery.SERVICE_REGISTRATION"
        )
        assert (
            str(EnumEventTypeDiscovery.SERVICE_DEREGISTRATION)
            == "EnumEventTypeDiscovery.SERVICE_DEREGISTRATION"
        )
        assert (
            str(EnumEventTypeDiscovery.CONTAINER_PROVISIONING)
            == "EnumEventTypeDiscovery.CONTAINER_PROVISIONING"
        )
        assert (
            str(EnumEventTypeDiscovery.CONTAINER_HEALTH_CHECK)
            == "EnumEventTypeDiscovery.CONTAINER_HEALTH_CHECK"
        )
        assert (
            str(EnumEventTypeDiscovery.MESH_COORDINATION)
            == "EnumEventTypeDiscovery.MESH_COORDINATION"
        )
        assert (
            str(EnumEventTypeDiscovery.HUB_STATUS_UPDATE)
            == "EnumEventTypeDiscovery.HUB_STATUS_UPDATE"
        )

    def test_enum_iteration(self):
        """Test that we can iterate over enum values."""
        values = list(EnumEventTypeDiscovery)
        assert len(values) == 7
        assert EnumEventTypeDiscovery.SERVICE_DISCOVERY in values
        assert EnumEventTypeDiscovery.SERVICE_REGISTRATION in values
        assert EnumEventTypeDiscovery.SERVICE_DEREGISTRATION in values
        assert EnumEventTypeDiscovery.CONTAINER_PROVISIONING in values
        assert EnumEventTypeDiscovery.CONTAINER_HEALTH_CHECK in values
        assert EnumEventTypeDiscovery.MESH_COORDINATION in values
        assert EnumEventTypeDiscovery.HUB_STATUS_UPDATE in values

    def test_enum_membership(self):
        """Test membership testing."""
        assert "service_discovery" in EnumEventTypeDiscovery
        assert "service_registration" in EnumEventTypeDiscovery
        assert "service_deregistration" in EnumEventTypeDiscovery
        assert "container_provisioning" in EnumEventTypeDiscovery
        assert "container_health_check" in EnumEventTypeDiscovery
        assert "mesh_coordination" in EnumEventTypeDiscovery
        assert "hub_status_update" in EnumEventTypeDiscovery
        assert "invalid" not in EnumEventTypeDiscovery

    def test_enum_comparison(self):
        """Test enum comparison."""
        assert EnumEventTypeDiscovery.SERVICE_DISCOVERY == "service_discovery"
        assert EnumEventTypeDiscovery.SERVICE_REGISTRATION == "service_registration"
        assert EnumEventTypeDiscovery.SERVICE_DEREGISTRATION == "service_deregistration"
        assert EnumEventTypeDiscovery.CONTAINER_PROVISIONING == "container_provisioning"
        assert EnumEventTypeDiscovery.CONTAINER_HEALTH_CHECK == "container_health_check"
        assert EnumEventTypeDiscovery.MESH_COORDINATION == "mesh_coordination"
        assert EnumEventTypeDiscovery.HUB_STATUS_UPDATE == "hub_status_update"

    def test_enum_serialization(self):
        """Test enum serialization."""
        assert EnumEventTypeDiscovery.SERVICE_DISCOVERY.value == "service_discovery"
        assert (
            EnumEventTypeDiscovery.SERVICE_REGISTRATION.value == "service_registration"
        )
        assert (
            EnumEventTypeDiscovery.SERVICE_DEREGISTRATION.value
            == "service_deregistration"
        )
        assert (
            EnumEventTypeDiscovery.CONTAINER_PROVISIONING.value
            == "container_provisioning"
        )
        assert (
            EnumEventTypeDiscovery.CONTAINER_HEALTH_CHECK.value
            == "container_health_check"
        )
        assert EnumEventTypeDiscovery.MESH_COORDINATION.value == "mesh_coordination"
        assert EnumEventTypeDiscovery.HUB_STATUS_UPDATE.value == "hub_status_update"

    def test_enum_deserialization(self):
        """Test enum deserialization."""
        assert (
            EnumEventTypeDiscovery("service_discovery")
            == EnumEventTypeDiscovery.SERVICE_DISCOVERY
        )
        assert (
            EnumEventTypeDiscovery("service_registration")
            == EnumEventTypeDiscovery.SERVICE_REGISTRATION
        )
        assert (
            EnumEventTypeDiscovery("service_deregistration")
            == EnumEventTypeDiscovery.SERVICE_DEREGISTRATION
        )
        assert (
            EnumEventTypeDiscovery("container_provisioning")
            == EnumEventTypeDiscovery.CONTAINER_PROVISIONING
        )
        assert (
            EnumEventTypeDiscovery("container_health_check")
            == EnumEventTypeDiscovery.CONTAINER_HEALTH_CHECK
        )
        assert (
            EnumEventTypeDiscovery("mesh_coordination")
            == EnumEventTypeDiscovery.MESH_COORDINATION
        )
        assert (
            EnumEventTypeDiscovery("hub_status_update")
            == EnumEventTypeDiscovery.HUB_STATUS_UPDATE
        )

    def test_enum_invalid_values(self):
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumEventTypeDiscovery("invalid")

    def test_enum_all_values(self):
        """Test that all enum values are accessible."""
        all_values = [event_type.value for event_type in EnumEventTypeDiscovery]
        expected_values = [
            "service_discovery",
            "service_registration",
            "service_deregistration",
            "container_provisioning",
            "container_health_check",
            "mesh_coordination",
            "hub_status_update",
        ]
        assert set(all_values) == set(expected_values)

    def test_enum_docstring(self):
        """Test that enum has proper docstring."""
        assert (
            "Event types supported by the Event Registry"
            in EnumEventTypeDiscovery.__doc__
        )
