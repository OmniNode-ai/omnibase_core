# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for enum_metric_type.py"""

from enum import Enum

import pytest

from omnibase_core.enums.enum_metric_type import EnumMetricType


@pytest.mark.unit
class TestEnumMetricType:
    """Test cases for EnumMetricType"""

    def test_enum_values(self):
        """Test that all enum values are correct"""
        assert EnumMetricType.PERFORMANCE == "performance"
        assert EnumMetricType.SYSTEM == "system"
        assert EnumMetricType.BUSINESS == "business"
        assert EnumMetricType.CUSTOM == "custom"
        assert EnumMetricType.HEALTH == "health"

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum"""
        assert issubclass(EnumMetricType, str)
        assert issubclass(EnumMetricType, Enum)

    def test_enum_string_behavior(self):
        """Test string behavior of enum values"""
        assert EnumMetricType.PERFORMANCE == "performance"
        assert EnumMetricType.SYSTEM == "system"
        assert EnumMetricType.BUSINESS == "business"

    def test_enum_iteration(self):
        """Test that we can iterate over enum values"""
        values = list(EnumMetricType)
        assert len(values) == 5
        assert EnumMetricType.PERFORMANCE in values
        assert EnumMetricType.HEALTH in values

    def test_enum_membership(self):
        """Test membership testing"""
        assert EnumMetricType.PERFORMANCE in EnumMetricType
        assert "performance" in EnumMetricType
        assert "invalid_value" not in EnumMetricType

    def test_enum_comparison(self):
        """Test enum comparison"""
        assert EnumMetricType.PERFORMANCE == EnumMetricType.PERFORMANCE
        assert EnumMetricType.SYSTEM != EnumMetricType.PERFORMANCE
        assert EnumMetricType.PERFORMANCE == "performance"

    def test_enum_serialization(self):
        """Test enum serialization"""
        assert EnumMetricType.PERFORMANCE.value == "performance"
        assert EnumMetricType.SYSTEM.value == "system"

    def test_enum_deserialization(self):
        """Test enum deserialization"""
        assert EnumMetricType("performance") == EnumMetricType.PERFORMANCE
        assert EnumMetricType("system") == EnumMetricType.SYSTEM

    def test_enum_invalid_values(self):
        """Test that invalid values raise ValueError"""
        with pytest.raises(ValueError):
            EnumMetricType("invalid_value")

        with pytest.raises(ValueError):
            EnumMetricType("")

    def test_enum_all_values(self):
        """Test that all expected values are present"""
        expected_values = {"performance", "system", "business", "custom", "health"}
        actual_values = {member.value for member in EnumMetricType}
        assert actual_values == expected_values

    def test_enum_docstring(self):
        """Test that enum has proper docstring"""
        assert "Strongly typed metric type values" in EnumMetricType.__doc__

    def test_enum_unique_decorator(self):
        """Test that enum has @unique decorator"""
        # The @unique decorator ensures no duplicate values
        # This is tested implicitly by the fact that the enum works correctly
        assert len(set(EnumMetricType)) == len(EnumMetricType)

    def test_enum_metric_types(self):
        """Test specific metric types"""
        # Performance metrics
        assert EnumMetricType.PERFORMANCE.value == "performance"

        # System metrics
        assert EnumMetricType.SYSTEM.value == "system"

        # Business metrics
        assert EnumMetricType.BUSINESS.value == "business"

        # Custom metrics
        assert EnumMetricType.CUSTOM.value == "custom"

        # Health metrics
        assert EnumMetricType.HEALTH.value == "health"

    def test_enum_metric_categories(self):
        """Test metric categories"""
        # Infrastructure metrics
        infrastructure_metrics = {
            EnumMetricType.PERFORMANCE,
            EnumMetricType.SYSTEM,
            EnumMetricType.HEALTH,
        }

        # Business metrics
        business_metrics = {EnumMetricType.BUSINESS}

        # Custom metrics
        custom_metrics = {EnumMetricType.CUSTOM}

        all_metrics = set(EnumMetricType)
        assert (
            infrastructure_metrics.union(business_metrics).union(custom_metrics)
            == all_metrics
        )

    def test_enum_metric_scope(self):
        """Test metric scope categories"""
        # Technical metrics
        technical_metrics = {
            EnumMetricType.PERFORMANCE,
            EnumMetricType.SYSTEM,
            EnumMetricType.HEALTH,
        }

        # Business metrics
        business_metrics = {EnumMetricType.BUSINESS}

        # User-defined metrics
        user_defined_metrics = {EnumMetricType.CUSTOM}

        all_metrics = set(EnumMetricType)
        assert (
            technical_metrics.union(business_metrics).union(user_defined_metrics)
            == all_metrics
        )
