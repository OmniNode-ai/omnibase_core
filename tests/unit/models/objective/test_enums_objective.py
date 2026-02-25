# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for objective function enums.

Tests cover: EnumGateType, EnumRewardTargetType, EnumPolicyType, EnumObjectiveLayer.
Part of OMN-2537.
"""

import pytest

from omnibase_core.enums.enum_gate_type import EnumGateType
from omnibase_core.enums.enum_objective_layer import EnumObjectiveLayer
from omnibase_core.enums.enum_policy_type import EnumPolicyType
from omnibase_core.enums.enum_reward_target_type import EnumRewardTargetType


@pytest.mark.unit
class TestEnumGateType:
    """Test EnumGateType exhaustiveness and values."""

    def test_all_values_present(self) -> None:
        """All seven gate types are present in the enum."""
        expected = {
            "test_pass",
            "gate_pass",
            "budget",
            "latency",
            "schema_fingerprint",
            "security",
            "blacklist",
        }
        actual = {e.value for e in EnumGateType}
        assert actual == expected

    def test_string_coercible(self) -> None:
        """EnumGateType values coerce to their string values via __str__."""
        assert str(EnumGateType.TEST_PASS) == "test_pass"
        assert str(EnumGateType.SCHEMA_FINGERPRINT) == "schema_fingerprint"

    def test_importable_from_enums_module(self) -> None:
        """EnumGateType is importable from the top-level enums module."""
        from omnibase_core.enums import EnumGateType as GateTypeFromInit

        assert GateTypeFromInit.TEST_PASS == EnumGateType.TEST_PASS


@pytest.mark.unit
class TestEnumRewardTargetType:
    """Test EnumRewardTargetType exhaustiveness and values."""

    def test_all_values_present(self) -> None:
        """All four reward target types are present."""
        expected = {"tool", "model", "pattern", "agent"}
        actual = {e.value for e in EnumRewardTargetType}
        assert actual == expected

    def test_string_coercible(self) -> None:
        """EnumRewardTargetType values coerce to their string values."""
        assert str(EnumRewardTargetType.TOOL) == "tool"
        assert str(EnumRewardTargetType.PATTERN) == "pattern"

    def test_importable_from_enums_module(self) -> None:
        """EnumRewardTargetType is importable from the top-level enums module."""
        from omnibase_core.enums import EnumRewardTargetType as RTFromInit

        assert RTFromInit.AGENT == EnumRewardTargetType.AGENT


@pytest.mark.unit
class TestEnumPolicyType:
    """Test EnumPolicyType exhaustiveness and values."""

    def test_all_values_present(self) -> None:
        """All four policy types are present."""
        expected = {
            "tool_reliability",
            "pattern_effectiveness",
            "model_routing_confidence",
            "retry_threshold",
        }
        actual = {e.value for e in EnumPolicyType}
        assert actual == expected

    def test_string_coercible(self) -> None:
        """EnumPolicyType values coerce to their string values."""
        assert str(EnumPolicyType.TOOL_RELIABILITY) == "tool_reliability"
        assert str(EnumPolicyType.RETRY_THRESHOLD) == "retry_threshold"

    def test_importable_from_enums_module(self) -> None:
        """EnumPolicyType is importable from the top-level enums module."""
        from omnibase_core.enums import EnumPolicyType as PTFromInit

        assert (
            PTFromInit.MODEL_ROUTING_CONFIDENCE
            == EnumPolicyType.MODEL_ROUTING_CONFIDENCE
        )


@pytest.mark.unit
class TestEnumObjectiveLayer:
    """Test EnumObjectiveLayer exhaustiveness and values."""

    def test_all_values_present(self) -> None:
        """All three objective layers are present."""
        expected = {"task", "policy", "system"}
        actual = {e.value for e in EnumObjectiveLayer}
        assert actual == expected

    def test_string_coercible(self) -> None:
        """EnumObjectiveLayer values coerce to their string values."""
        assert str(EnumObjectiveLayer.TASK) == "task"
        assert str(EnumObjectiveLayer.SYSTEM) == "system"

    def test_importable_from_enums_module(self) -> None:
        """EnumObjectiveLayer is importable from the top-level enums module."""
        from omnibase_core.enums import EnumObjectiveLayer as OLFromInit

        assert OLFromInit.POLICY == EnumObjectiveLayer.POLICY
