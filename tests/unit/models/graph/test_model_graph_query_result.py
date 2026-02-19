# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for ModelGraphQueryResult and related models."""

import pytest
from pydantic import ValidationError

from omnibase_core.models.graph.model_graph_query_result import (
    ModelGraphQueryCounters,
    ModelGraphQueryResult,
    ModelGraphQuerySummary,
)


@pytest.mark.unit
class TestModelGraphQueryCountersBasics:
    """Test basic ModelGraphQueryCounters functionality."""

    def test_default_initialization(self):
        """Test default initialization with zero values."""
        counters = ModelGraphQueryCounters()

        assert counters.nodes_created == 0
        assert counters.nodes_deleted == 0
        assert counters.relationships_created == 0
        assert counters.relationships_deleted == 0
        assert counters.properties_set == 0
        assert counters.labels_added == 0
        assert counters.labels_removed == 0

    def test_initialization_with_values(self):
        """Test initialization with non-zero values."""
        counters = ModelGraphQueryCounters(
            nodes_created=5,
            relationships_created=3,
            properties_set=10,
        )

        assert counters.nodes_created == 5
        assert counters.relationships_created == 3
        assert counters.properties_set == 10

    def test_negative_values_invalid(self):
        """Test that negative values are invalid."""
        with pytest.raises(ValidationError):
            ModelGraphQueryCounters(nodes_created=-1)


@pytest.mark.unit
class TestModelGraphQuerySummaryBasics:
    """Test basic ModelGraphQuerySummary functionality."""

    def test_default_initialization(self):
        """Test default initialization."""
        summary = ModelGraphQuerySummary()

        assert summary.query_type == "unknown"
        assert summary.database is None
        assert summary.contains_updates is False

    def test_initialization_with_values(self):
        """Test initialization with values."""
        summary = ModelGraphQuerySummary(
            query_type="write",
            database="neo4j",
            contains_updates=True,
        )

        assert summary.query_type == "write"
        assert summary.database == "neo4j"
        assert summary.contains_updates is True


@pytest.mark.unit
class TestModelGraphQueryResultBasics:
    """Test basic ModelGraphQueryResult functionality."""

    def test_default_initialization(self):
        """Test default initialization with empty values."""
        result = ModelGraphQueryResult()

        assert result.records == []
        assert result.summary.query_type == "unknown"
        assert result.counters.nodes_created == 0
        assert result.execution_time_ms == 0.0

    def test_initialization_with_records(self):
        """Test initialization with records."""
        records = [
            {"name": "John", "age": 30},
            {"name": "Jane", "age": 25},
        ]

        result = ModelGraphQueryResult(
            records=records,
            execution_time_ms=10.5,
        )

        assert len(result.records) == 2
        assert result.records[0]["name"] == "John"
        assert result.execution_time_ms == 10.5

    def test_initialization_with_all_fields(self):
        """Test initialization with all fields."""
        summary = ModelGraphQuerySummary(
            query_type="write",
            database="neo4j",
            contains_updates=True,
        )
        counters = ModelGraphQueryCounters(
            nodes_created=2,
            properties_set=5,
        )

        result = ModelGraphQueryResult(
            records=[{"id": 1}],
            summary=summary,
            counters=counters,
            execution_time_ms=50.0,
        )

        assert result.summary.query_type == "write"
        assert result.counters.nodes_created == 2
        assert result.execution_time_ms == 50.0


@pytest.mark.unit
class TestModelGraphQueryResultValidation:
    """Test ModelGraphQueryResult validation."""

    def test_negative_execution_time_invalid(self):
        """Test that negative execution time is invalid."""
        with pytest.raises(ValidationError):
            ModelGraphQueryResult(execution_time_ms=-1.0)

    def test_extra_fields_forbidden(self):
        """Test that extra fields are forbidden."""
        with pytest.raises(ValidationError):
            ModelGraphQueryResult(unknown_field="value")


@pytest.mark.unit
class TestModelGraphQueryResultImmutability:
    """Test ModelGraphQueryResult immutability."""

    def test_frozen_model(self):
        """Test that model is frozen and cannot be modified."""
        result = ModelGraphQueryResult(execution_time_ms=10.0)

        with pytest.raises(ValidationError):
            result.execution_time_ms = 20.0


@pytest.mark.unit
class TestModelGraphQueryResultSerialization:
    """Test ModelGraphQueryResult serialization."""

    def test_model_dump(self):
        """Test model serialization to dict."""
        result = ModelGraphQueryResult(
            records=[{"x": 1}],
            execution_time_ms=5.0,
        )

        data = result.model_dump()

        assert data["records"] == [{"x": 1}]
        assert data["execution_time_ms"] == 5.0
        assert "summary" in data
        assert "counters" in data
