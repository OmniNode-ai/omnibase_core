# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for EnumPublisherType."""

import json
from enum import Enum

import pytest

from omnibase_core.enums.enum_publisher_type import EnumPublisherType


@pytest.mark.unit
class TestEnumPublisherType:
    """Test suite for EnumPublisherType."""

    def test_enum_values(self):
        """Test that all enum values are defined correctly."""
        assert EnumPublisherType.IN_MEMORY == "IN_MEMORY"
        assert EnumPublisherType.AUTO == "AUTO"
        assert EnumPublisherType.HYBRID == "HYBRID"

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumPublisherType, str)
        assert issubclass(EnumPublisherType, Enum)

    def test_enum_string_behavior(self):
        """Test string behavior of enum values."""
        publisher = EnumPublisherType.IN_MEMORY
        assert isinstance(publisher, str)
        assert publisher == "IN_MEMORY"
        assert len(publisher) == 9

    def test_enum_iteration(self):
        """Test that all enum values can be iterated."""
        values = list(EnumPublisherType)
        assert len(values) == 3
        assert EnumPublisherType.IN_MEMORY in values
        assert EnumPublisherType.HYBRID in values

    def test_enum_membership(self):
        """Test membership testing."""
        assert EnumPublisherType.AUTO in EnumPublisherType
        assert "AUTO" in [e.value for e in EnumPublisherType]

    def test_enum_comparison(self):
        """Test enum comparison."""
        publisher1 = EnumPublisherType.IN_MEMORY
        publisher2 = EnumPublisherType.IN_MEMORY
        publisher3 = EnumPublisherType.AUTO

        assert publisher1 == publisher2
        assert publisher1 != publisher3
        assert publisher1 == "IN_MEMORY"

    def test_enum_serialization(self):
        """Test enum serialization."""
        publisher = EnumPublisherType.HYBRID
        serialized = publisher.value
        assert serialized == "HYBRID"
        json_str = json.dumps(publisher)
        assert json_str == '"HYBRID"'

    def test_enum_deserialization(self):
        """Test enum deserialization."""
        publisher = EnumPublisherType("AUTO")
        assert publisher == EnumPublisherType.AUTO

    def test_enum_invalid_value(self):
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumPublisherType("INVALID_TYPE")

    def test_enum_all_values(self):
        """Test that all expected values are present."""
        expected_values = {"IN_MEMORY", "AUTO", "HYBRID"}
        actual_values = {e.value for e in EnumPublisherType}
        assert actual_values == expected_values

    def test_enum_docstring(self):
        """Test that enum has proper docstring."""
        assert EnumPublisherType.__doc__ is not None
        assert "publisher" in EnumPublisherType.__doc__.lower()

    def test_publisher_types_categorization(self):
        """Test publisher type categorization."""
        # Explicit types
        explicit = {EnumPublisherType.IN_MEMORY, EnumPublisherType.HYBRID}
        # Automatic type
        automatic = {EnumPublisherType.AUTO}

        assert all(p in EnumPublisherType for p in explicit)
        assert all(p in EnumPublisherType for p in automatic)

    def test_all_publishers_categorized(self):
        """Test that all publishers can be categorized."""
        # Manual selection
        manual = {EnumPublisherType.IN_MEMORY, EnumPublisherType.HYBRID}
        # Automatic selection
        auto_select = {EnumPublisherType.AUTO}

        all_publishers = manual | auto_select
        assert all_publishers == set(EnumPublisherType)
