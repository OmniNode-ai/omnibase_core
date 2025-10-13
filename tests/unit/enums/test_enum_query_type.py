"""Tests for EnumQueryType."""

import json
from enum import Enum

import pytest

from omnibase_core.enums.enum_query_type import EnumQueryType


class TestEnumQueryType:
    """Test suite for EnumQueryType."""

    def test_enum_values(self):
        """Test that all enum values are defined correctly."""
        # General query types
        assert EnumQueryType.EXPLANATION == "explanation"
        assert EnumQueryType.GENERAL == "general"
        assert EnumQueryType.CONVERSATION == "conversation"
        assert EnumQueryType.DOCUMENTATION == "documentation"

        # Technical query types
        assert EnumQueryType.CODE == "code"
        assert EnumQueryType.TECHNICAL == "technical"
        assert EnumQueryType.IMPLEMENTATION == "implementation"
        assert EnumQueryType.DEBUGGING == "debugging"

        # Analysis query types
        assert EnumQueryType.ANALYSIS == "analysis"
        assert EnumQueryType.COMPARISON == "comparison"
        assert EnumQueryType.EVALUATION == "evaluation"

        # Search and retrieval types
        assert EnumQueryType.SEARCH == "search"
        assert EnumQueryType.LOOKUP == "lookup"
        assert EnumQueryType.REFERENCE == "reference"

        # Creative and planning types
        assert EnumQueryType.CREATIVE == "creative"
        assert EnumQueryType.PLANNING == "planning"
        assert EnumQueryType.BRAINSTORMING == "brainstorming"

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumQueryType, str)
        assert issubclass(EnumQueryType, Enum)

    def test_enum_string_behavior(self):
        """Test string behavior of enum values."""
        query = EnumQueryType.CODE
        assert isinstance(query, str)
        assert query == "code"
        assert len(query) == 4

    def test_enum_iteration(self):
        """Test that all enum values can be iterated."""
        values = list(EnumQueryType)
        assert len(values) == 17
        assert EnumQueryType.CODE in values
        assert EnumQueryType.BRAINSTORMING in values

    def test_enum_membership(self):
        """Test membership testing."""
        assert EnumQueryType.TECHNICAL in EnumQueryType
        assert "technical" in [e.value for e in EnumQueryType]

    def test_enum_comparison(self):
        """Test enum comparison."""
        query1 = EnumQueryType.ANALYSIS
        query2 = EnumQueryType.ANALYSIS
        query3 = EnumQueryType.SEARCH

        assert query1 == query2
        assert query1 != query3
        assert query1 == "analysis"

    def test_enum_serialization(self):
        """Test enum serialization."""
        query = EnumQueryType.IMPLEMENTATION
        serialized = query.value
        assert serialized == "implementation"
        json_str = json.dumps(query)
        assert json_str == '"implementation"'

    def test_enum_deserialization(self):
        """Test enum deserialization."""
        query = EnumQueryType("debugging")
        assert query == EnumQueryType.DEBUGGING

    def test_enum_invalid_value(self):
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumQueryType("invalid_query")

    def test_enum_all_values(self):
        """Test that all expected values are present."""
        expected_values = {
            "explanation",
            "general",
            "conversation",
            "documentation",
            "code",
            "technical",
            "implementation",
            "debugging",
            "analysis",
            "comparison",
            "evaluation",
            "search",
            "lookup",
            "reference",
            "creative",
            "planning",
            "brainstorming",
        }
        actual_values = {e.value for e in EnumQueryType}
        assert actual_values == expected_values

    def test_enum_docstring(self):
        """Test that enum has proper docstring."""
        assert EnumQueryType.__doc__ is not None
        assert "query" in EnumQueryType.__doc__.lower()

    def test_general_query_types(self):
        """Test general query type grouping."""
        general_queries = {
            EnumQueryType.EXPLANATION,
            EnumQueryType.GENERAL,
            EnumQueryType.CONVERSATION,
            EnumQueryType.DOCUMENTATION,
        }
        assert all(q in EnumQueryType for q in general_queries)

    def test_technical_query_types(self):
        """Test technical query type grouping."""
        technical_queries = {
            EnumQueryType.CODE,
            EnumQueryType.TECHNICAL,
            EnumQueryType.IMPLEMENTATION,
            EnumQueryType.DEBUGGING,
        }
        assert all(q in EnumQueryType for q in technical_queries)

    def test_analysis_query_types(self):
        """Test analysis query type grouping."""
        analysis_queries = {
            EnumQueryType.ANALYSIS,
            EnumQueryType.COMPARISON,
            EnumQueryType.EVALUATION,
        }
        assert all(q in EnumQueryType for q in analysis_queries)

    def test_search_query_types(self):
        """Test search and retrieval query type grouping."""
        search_queries = {
            EnumQueryType.SEARCH,
            EnumQueryType.LOOKUP,
            EnumQueryType.REFERENCE,
        }
        assert all(q in EnumQueryType for q in search_queries)

    def test_creative_query_types(self):
        """Test creative and planning query type grouping."""
        creative_queries = {
            EnumQueryType.CREATIVE,
            EnumQueryType.PLANNING,
            EnumQueryType.BRAINSTORMING,
        }
        assert all(q in EnumQueryType for q in creative_queries)

    def test_all_query_types_categorized(self):
        """Test that all query types are properly categorized."""
        general = {
            EnumQueryType.EXPLANATION,
            EnumQueryType.GENERAL,
            EnumQueryType.CONVERSATION,
            EnumQueryType.DOCUMENTATION,
        }
        technical = {
            EnumQueryType.CODE,
            EnumQueryType.TECHNICAL,
            EnumQueryType.IMPLEMENTATION,
            EnumQueryType.DEBUGGING,
        }
        analysis = {
            EnumQueryType.ANALYSIS,
            EnumQueryType.COMPARISON,
            EnumQueryType.EVALUATION,
        }
        search = {
            EnumQueryType.SEARCH,
            EnumQueryType.LOOKUP,
            EnumQueryType.REFERENCE,
        }
        creative = {
            EnumQueryType.CREATIVE,
            EnumQueryType.PLANNING,
            EnumQueryType.BRAINSTORMING,
        }

        all_queries = general | technical | analysis | search | creative
        assert all_queries == set(EnumQueryType)
