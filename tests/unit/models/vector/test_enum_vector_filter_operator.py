# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

#
# SPDX-License-Identifier: Apache-2.0
"""Tests for EnumVectorFilterOperator."""

import pytest

from omnibase_core.models.vector import EnumVectorFilterOperator


@pytest.mark.unit
class TestEnumVectorFilterOperator:
    """Tests for EnumVectorFilterOperator enumeration."""

    def test_eq_value(self):
        """Test EQ enum value."""
        assert EnumVectorFilterOperator.EQ.value == "eq"

    def test_ne_value(self):
        """Test NE enum value."""
        assert EnumVectorFilterOperator.NE.value == "ne"

    def test_comparison_operators(self):
        """Test comparison operator values."""
        assert EnumVectorFilterOperator.GT.value == "gt"
        assert EnumVectorFilterOperator.GTE.value == "gte"
        assert EnumVectorFilterOperator.LT.value == "lt"
        assert EnumVectorFilterOperator.LTE.value == "lte"

    def test_collection_operators(self):
        """Test collection operator values."""
        assert EnumVectorFilterOperator.IN.value == "in"
        assert EnumVectorFilterOperator.NOT_IN.value == "not_in"

    def test_string_operators(self):
        """Test string operator values."""
        assert EnumVectorFilterOperator.CONTAINS.value == "contains"
        assert EnumVectorFilterOperator.STARTS_WITH.value == "starts_with"

    def test_exists_operator(self):
        """Test EXISTS operator value."""
        assert EnumVectorFilterOperator.EXISTS.value == "exists"

    def test_all_values_unique(self):
        """Test that all enum values are unique."""
        values = [op.value for op in EnumVectorFilterOperator]
        assert len(values) == len(set(values))

    def test_enum_from_value(self):
        """Test creating enum from string value."""
        assert EnumVectorFilterOperator("eq") == EnumVectorFilterOperator.EQ
        assert EnumVectorFilterOperator("gte") == EnumVectorFilterOperator.GTE
