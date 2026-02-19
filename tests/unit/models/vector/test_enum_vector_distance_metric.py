# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for EnumVectorDistanceMetric."""

import pytest

from omnibase_core.models.vector import EnumVectorDistanceMetric


@pytest.mark.unit
class TestEnumVectorDistanceMetric:
    """Tests for EnumVectorDistanceMetric enumeration."""

    def test_cosine_value(self):
        """Test COSINE enum value."""
        assert EnumVectorDistanceMetric.COSINE.value == "cosine"

    def test_euclidean_value(self):
        """Test EUCLIDEAN enum value."""
        assert EnumVectorDistanceMetric.EUCLIDEAN.value == "euclidean"

    def test_dot_product_value(self):
        """Test DOT_PRODUCT enum value."""
        assert EnumVectorDistanceMetric.DOT_PRODUCT.value == "dot_product"

    def test_manhattan_value(self):
        """Test MANHATTAN enum value."""
        assert EnumVectorDistanceMetric.MANHATTAN.value == "manhattan"

    def test_all_values_unique(self):
        """Test that all enum values are unique."""
        values = [m.value for m in EnumVectorDistanceMetric]
        assert len(values) == len(set(values))

    def test_string_representation(self):
        """Test string representation via .value attribute."""
        assert EnumVectorDistanceMetric.COSINE.value == "cosine"
        assert EnumVectorDistanceMetric.EUCLIDEAN.value == "euclidean"

    def test_enum_from_value(self):
        """Test creating enum from string value."""
        assert EnumVectorDistanceMetric("cosine") == EnumVectorDistanceMetric.COSINE
        assert (
            EnumVectorDistanceMetric("euclidean") == EnumVectorDistanceMetric.EUCLIDEAN
        )

    def test_invalid_value_raises(self):
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumVectorDistanceMetric("invalid_metric")
