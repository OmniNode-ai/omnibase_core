# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for EnumStepType."""

from enum import Enum

import pytest

from omnibase_core.enums.enum_step_type import EnumStepType


@pytest.mark.unit
class TestEnumStepType:
    """Test suite for EnumStepType enumeration."""

    def test_string_returns_value(self) -> None:
        """Test that str() returns the .value (StrValueHelper behavior)."""
        assert str(EnumStepType.COMPUTE) == "compute"
        assert str(EnumStepType.EFFECT) == "effect"
        assert str(EnumStepType.REDUCER) == "reducer"
        assert str(EnumStepType.ORCHESTRATOR) == "orchestrator"
        assert str(EnumStepType.PARALLEL) == "parallel"
        assert str(EnumStepType.CUSTOM) == "custom"

    def test_value_property(self) -> None:
        """Test that .value returns the correct string."""
        assert EnumStepType.COMPUTE.value == "compute"
        assert EnumStepType.EFFECT.value == "effect"
        assert EnumStepType.REDUCER.value == "reducer"
        assert EnumStepType.ORCHESTRATOR.value == "orchestrator"
        assert EnumStepType.PARALLEL.value == "parallel"
        assert EnumStepType.CUSTOM.value == "custom"

    def test_all_members_exist(self) -> None:
        """Test that all expected enum members exist."""
        values = [m.value for m in EnumStepType]
        assert "compute" in values
        assert "effect" in values
        assert "reducer" in values
        assert "orchestrator" in values
        assert "parallel" in values
        assert "custom" in values

    def test_unique_values(self) -> None:
        """Test that all enum values are unique."""
        values = [m.value for m in EnumStepType]
        assert len(values) == len(set(values))

    def test_enum_count(self) -> None:
        """Test that enum has exactly 6 members."""
        members = list(EnumStepType)
        assert len(members) == 6

    def test_enum_inheritance(self) -> None:
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumStepType, str)
        assert issubclass(EnumStepType, Enum)

    def test_enum_string_equality(self) -> None:
        """Test that enum members equal their string values."""
        assert EnumStepType.COMPUTE == "compute"
        assert EnumStepType.EFFECT == "effect"
        assert EnumStepType.REDUCER == "reducer"
        assert EnumStepType.ORCHESTRATOR == "orchestrator"
        assert EnumStepType.PARALLEL == "parallel"
        assert EnumStepType.CUSTOM == "custom"

    def test_enum_comparison(self) -> None:
        """Test enum member equality."""
        step1 = EnumStepType.COMPUTE
        step2 = EnumStepType.COMPUTE
        step3 = EnumStepType.EFFECT

        assert step1 == step2
        assert step1 != step3
        assert step1 is step2

    def test_enum_membership(self) -> None:
        """Test membership testing."""
        assert EnumStepType.COMPUTE in EnumStepType
        assert "compute" in EnumStepType
        assert "invalid_type" not in EnumStepType

    def test_enum_deserialization(self) -> None:
        """Test enum deserialization from string."""
        assert EnumStepType("compute") == EnumStepType.COMPUTE
        assert EnumStepType("orchestrator") == EnumStepType.ORCHESTRATOR

    def test_enum_invalid_values(self) -> None:
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumStepType("invalid_type")

        with pytest.raises(ValueError):
            EnumStepType("")

    def test_onex_core_node_types(self) -> None:
        """Test that core ONEX node types are present."""
        # The four core ONEX node architecture types
        core_types = {"compute", "effect", "reducer", "orchestrator"}
        values = {m.value for m in EnumStepType}
        assert core_types.issubset(values)
