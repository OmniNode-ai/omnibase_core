# SPDX-License-Identifier: MIT
# Copyright (c) 2025 OmniNode Team
"""
Unit tests for EnumHandlerRoutingStrategy enum.

Tests cover:
- Enum value validation
- String equality (str inheritance)
- Serialization/deserialization
- Pydantic model integration

Related:
    - OMN-1295: Update tests to use enum values instead of string literals
    - src/omnibase_core/enums/enum_handler_routing_strategy.py
"""

from __future__ import annotations

import json

import pytest
from pydantic import BaseModel

from omnibase_core.enums.enum_handler_routing_strategy import EnumHandlerRoutingStrategy


@pytest.mark.unit
class TestEnumHandlerRoutingStrategy:
    """Test EnumHandlerRoutingStrategy enum values and behavior."""

    def test_enum_values_exist(self) -> None:
        """Test that all expected enum values are defined."""
        assert hasattr(EnumHandlerRoutingStrategy, "PAYLOAD_TYPE_MATCH")
        assert hasattr(EnumHandlerRoutingStrategy, "OPERATION_MATCH")
        assert hasattr(EnumHandlerRoutingStrategy, "TOPIC_PATTERN")

    def test_enum_values_match_strings(self) -> None:
        """Test that enum values equal their string representations."""
        assert EnumHandlerRoutingStrategy.PAYLOAD_TYPE_MATCH == "payload_type_match"
        assert EnumHandlerRoutingStrategy.OPERATION_MATCH == "operation_match"
        assert EnumHandlerRoutingStrategy.TOPIC_PATTERN == "topic_pattern"

    def test_enum_value_attribute(self) -> None:
        """Test that .value returns the expected string."""
        assert (
            EnumHandlerRoutingStrategy.PAYLOAD_TYPE_MATCH.value == "payload_type_match"
        )
        assert EnumHandlerRoutingStrategy.OPERATION_MATCH.value == "operation_match"
        assert EnumHandlerRoutingStrategy.TOPIC_PATTERN.value == "topic_pattern"

    def test_enum_inherits_from_str(self) -> None:
        """Test that enum inherits from str for JSON compatibility."""
        for strategy in EnumHandlerRoutingStrategy:
            assert isinstance(strategy, str)
            # String operations should work
            assert strategy.upper() == strategy.value.upper()

    def test_enum_iteration(self) -> None:
        """Test iterating over all enum values."""
        strategies = list(EnumHandlerRoutingStrategy)
        assert len(strategies) == 3
        assert EnumHandlerRoutingStrategy.PAYLOAD_TYPE_MATCH in strategies
        assert EnumHandlerRoutingStrategy.OPERATION_MATCH in strategies
        assert EnumHandlerRoutingStrategy.TOPIC_PATTERN in strategies

    def test_enum_no_duplicate_values(self) -> None:
        """Test that no enum has duplicate values."""
        values = [e.value for e in EnumHandlerRoutingStrategy]
        assert len(values) == len(set(values)), "Enum has duplicate values"


@pytest.mark.unit
class TestEnumHandlerRoutingStrategyPydanticIntegration:
    """Test EnumHandlerRoutingStrategy integration with Pydantic models."""

    def test_pydantic_model_with_enum(self) -> None:
        """Test using enum in a Pydantic model."""

        class TestModel(BaseModel):
            routing_strategy: EnumHandlerRoutingStrategy

        model = TestModel(
            routing_strategy=EnumHandlerRoutingStrategy.PAYLOAD_TYPE_MATCH
        )
        assert model.routing_strategy == EnumHandlerRoutingStrategy.PAYLOAD_TYPE_MATCH
        assert model.routing_strategy == "payload_type_match"

    def test_pydantic_model_with_string_input(self) -> None:
        """Test that Pydantic accepts string values for enum fields."""

        class TestModel(BaseModel):
            routing_strategy: EnumHandlerRoutingStrategy

        # Pydantic should coerce string to enum
        model = TestModel(routing_strategy="operation_match")
        assert model.routing_strategy == EnumHandlerRoutingStrategy.OPERATION_MATCH

    def test_pydantic_model_serialization(self) -> None:
        """Test that enum serializes correctly in Pydantic models."""

        class TestModel(BaseModel):
            routing_strategy: EnumHandlerRoutingStrategy

        model = TestModel(routing_strategy=EnumHandlerRoutingStrategy.TOPIC_PATTERN)
        model_dict = model.model_dump()
        assert model_dict == {"routing_strategy": "topic_pattern"}

    def test_pydantic_model_json_serialization(self) -> None:
        """Test that enum serializes correctly to JSON."""

        class TestModel(BaseModel):
            routing_strategy: EnumHandlerRoutingStrategy

        model = TestModel(
            routing_strategy=EnumHandlerRoutingStrategy.PAYLOAD_TYPE_MATCH
        )
        json_str = model.model_dump_json()
        loaded = json.loads(json_str)
        assert loaded == {"routing_strategy": "payload_type_match"}

    def test_yaml_string_coercion_in_subcontract(self) -> None:
        """Test that YAML-style string inputs are coerced to enum in subcontract.

        Verifies Pydantic's automatic string-to-enum coercion works correctly
        for ModelHandlerRoutingSubcontract, enabling backward compatibility
        with existing YAML contracts that use string values.
        """
        from omnibase_core.models.contracts.subcontracts.model_handler_routing_subcontract import (
            ModelHandlerRoutingSubcontract,
        )
        from omnibase_core.models.primitives.model_semver import ModelSemVer

        # String input (as would come from YAML parsing)
        subcontract = ModelHandlerRoutingSubcontract(
            version=ModelSemVer(major=1, minor=0, patch=0),
            routing_strategy="payload_type_match",  # String, not enum
            handlers=[],
            default_handler="fallback",
        )

        # Should be coerced to enum member
        assert isinstance(subcontract.routing_strategy, EnumHandlerRoutingStrategy)
        assert (
            subcontract.routing_strategy
            == EnumHandlerRoutingStrategy.PAYLOAD_TYPE_MATCH
        )
        assert subcontract.routing_strategy.value == "payload_type_match"


@pytest.mark.unit
class TestEnumHandlerRoutingStrategySerialization:
    """Test EnumHandlerRoutingStrategy serialization behavior."""

    def test_json_serializable(self) -> None:
        """Test that enum values can be serialized to JSON."""
        data = {"strategy": EnumHandlerRoutingStrategy.PAYLOAD_TYPE_MATCH.value}
        json_str = json.dumps(data)
        loaded = json.loads(json_str)
        assert loaded["strategy"] == "payload_type_match"

    def test_deserialization_from_string(self) -> None:
        """Test that strings can be converted back to enum values."""
        for strategy in EnumHandlerRoutingStrategy:
            reconstructed = EnumHandlerRoutingStrategy(strategy.value)
            assert reconstructed == strategy
            assert reconstructed is strategy  # Same enum member

    def test_string_comparison_case_sensitive(self) -> None:
        """Test that string comparison is case-sensitive."""
        # Enum values are lowercase
        assert EnumHandlerRoutingStrategy.PAYLOAD_TYPE_MATCH == "payload_type_match"
        # Should not equal uppercase
        assert EnumHandlerRoutingStrategy.PAYLOAD_TYPE_MATCH != "PAYLOAD_TYPE_MATCH"
        assert EnumHandlerRoutingStrategy.PAYLOAD_TYPE_MATCH != "Payload_Type_Match"


@pytest.mark.unit
class TestEnumHandlerRoutingStrategyDocstrings:
    """Test that enum values have proper documentation."""

    def test_enum_has_docstring(self) -> None:
        """Test that the enum class has a docstring."""
        assert EnumHandlerRoutingStrategy.__doc__ is not None
        assert len(EnumHandlerRoutingStrategy.__doc__) > 0

    def test_enum_member_count(self) -> None:
        """Test that all expected members exist (no more, no less)."""
        expected_members = {"PAYLOAD_TYPE_MATCH", "OPERATION_MATCH", "TOPIC_PATTERN"}
        actual_members = {member.name for member in EnumHandlerRoutingStrategy}
        assert actual_members == expected_members, (
            f"Expected {expected_members}, got {actual_members}"
        )
