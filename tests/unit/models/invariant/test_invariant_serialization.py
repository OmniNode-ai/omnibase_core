# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for invariant model serialization."""

import json
import uuid

import pytest

from omnibase_core.enums import EnumInvariantType, EnumSeverity
from omnibase_core.models.invariant import (
    ModelInvariant,
    ModelInvariantResult,
    ModelInvariantSet,
)

# Test UUIDs for consistent testing
TEST_UUID = uuid.UUID("12345678-1234-5678-1234-567812345678")
TEST_UUID_STR = "12345678-1234-5678-1234-567812345678"


@pytest.mark.unit
class TestInvariantSerialization:
    """Test ModelInvariant serialization."""

    def test_invariant_to_dict_and_back(self) -> None:
        """Model -> dict -> Model should preserve all fields."""
        original = ModelInvariant(
            name="Test invariant",
            type=EnumInvariantType.LATENCY,
            severity=EnumSeverity.CRITICAL,
            config={"max_ms": 5000},
            enabled=False,
            description="Test description",
        )

        data = original.model_dump()
        restored = ModelInvariant.model_validate(data)

        assert restored.name == original.name
        assert restored.type == original.type
        assert restored.severity == original.severity
        assert restored.config == original.config
        assert restored.enabled == original.enabled
        assert restored.description == original.description

    def test_invariant_json_serialization(self) -> None:
        """Invariant should serialize to valid JSON."""
        inv = ModelInvariant(
            name="Test",
            type=EnumInvariantType.LATENCY,
            config={"max_ms": 5000},
        )

        json_str = inv.model_dump_json()
        assert isinstance(json_str, str)

        # Should be valid JSON
        parsed = json.loads(json_str)
        assert parsed["name"] == "Test"
        assert parsed["config"]["max_ms"] == 5000

    def test_invariant_json_deserialization(self) -> None:
        """Invariant should deserialize from JSON."""
        json_str = json.dumps(
            {
                "id": TEST_UUID_STR,
                "name": "Test",
                "type": "latency",
                "severity": "warning",
                "config": {"max_ms": 5000},
                "enabled": True,
            }
        )

        inv = ModelInvariant.model_validate_json(json_str)
        assert inv.name == "Test"
        assert inv.type == EnumInvariantType.LATENCY
        assert inv.severity == EnumSeverity.WARNING
        assert inv.id == TEST_UUID

    def test_invariant_preserves_complex_config(self) -> None:
        """Serialization preserves complex nested config."""
        complex_config = {
            "json_schema": {
                "type": "object",
                "properties": {
                    "response": {
                        "type": "object",
                        "properties": {"content": {"type": "string"}},
                    }
                },
            }
        }

        original = ModelInvariant(
            name="Schema check",
            type=EnumInvariantType.SCHEMA,
            config=complex_config,
        )

        data = original.model_dump()
        restored = ModelInvariant.model_validate(data)

        assert restored.config == complex_config

    def test_invariant_enum_serialization(self) -> None:
        """Test enum serialization behavior in model_dump() vs model_dump_json().

        Pydantic's default behavior (without use_enum_values=True in ConfigDict):
        - model_dump(): Returns enum MEMBERS (not string values)
        - model_dump(mode="json"): Returns string VALUES for JSON compatibility
        - model_dump_json(): Returns JSON string with enum values as strings

        This test verifies the actual behavior explicitly to document the API.
        """
        inv = ModelInvariant(
            name="Test",
            type=EnumInvariantType.LATENCY,
            severity=EnumSeverity.CRITICAL,
            config={"max_ms": 5000},
        )

        # Standard model_dump() returns enum MEMBERS, not strings
        data = inv.model_dump()

        # Verify type is the enum class, not str
        assert type(data["type"]) is EnumInvariantType, (
            f"Expected model_dump() to return enum member, "
            f"got {type(data['type']).__name__}"
        )
        assert data["type"] is EnumInvariantType.LATENCY, (
            f"Expected EnumInvariantType.LATENCY, got {data['type']!r}"
        )

        assert type(data["severity"]) is EnumSeverity, (
            f"Expected model_dump() to return enum member, "
            f"got {type(data['severity']).__name__}"
        )
        assert data["severity"] is EnumSeverity.CRITICAL, (
            f"Expected EnumSeverity.CRITICAL, got {data['severity']!r}"
        )

        # model_dump(mode="json") returns string values for JSON compatibility
        json_data = inv.model_dump(mode="json")

        assert type(json_data["type"]) is str, (
            f"Expected model_dump(mode='json') to return str, "
            f"got {type(json_data['type']).__name__}"
        )
        assert json_data["type"] == "latency", (
            f"Expected 'latency', got {json_data['type']!r}"
        )

        assert type(json_data["severity"]) is str, (
            f"Expected model_dump(mode='json') to return str, "
            f"got {type(json_data['severity']).__name__}"
        )
        assert json_data["severity"] == "critical", (
            f"Expected 'critical', got {json_data['severity']!r}"
        )


@pytest.mark.unit
class TestInvariantResultSerialization:
    """Test ModelInvariantResult serialization."""

    def test_result_serialization_preserves_actual_value(self) -> None:
        """Result with complex actual_value serializes correctly."""
        result = ModelInvariantResult(
            invariant_id=TEST_UUID,
            invariant_name="Test",
            passed=False,
            severity=EnumSeverity.CRITICAL,
            actual_value={"nested": {"value": 123}},
            expected_value={"nested": {"value": 100}},
            message="Value mismatch",
        )

        data = result.model_dump()
        restored = ModelInvariantResult.model_validate(data)

        assert restored.actual_value == {"nested": {"value": 123}}
        assert restored.passed is False

    def test_result_serialization_with_none_values(self) -> None:
        """Result handles None values correctly."""
        result = ModelInvariantResult(
            invariant_id=TEST_UUID,
            invariant_name="Test",
            passed=True,
            severity=EnumSeverity.WARNING,
            actual_value=None,
            expected_value=None,
        )

        data = result.model_dump()
        restored = ModelInvariantResult.model_validate(data)

        assert restored.actual_value is None
        assert restored.expected_value is None
        assert restored.message == ""

    def test_result_json_serialization(self) -> None:
        """Result should serialize to valid JSON."""
        result = ModelInvariantResult(
            invariant_id=TEST_UUID,
            invariant_name="Test",
            passed=True,
            severity=EnumSeverity.INFO,
        )

        json_str = result.model_dump_json()
        assert isinstance(json_str, str)

        parsed = json.loads(json_str)
        assert parsed["invariant_id"] == TEST_UUID_STR  # JSON serializes UUID to str
        assert parsed["passed"] is True

    def test_result_with_list_actual_value(self) -> None:
        """Result handles list actual_value correctly."""
        result = ModelInvariantResult(
            invariant_id=TEST_UUID,
            invariant_name="Fields check",
            passed=False,
            severity=EnumSeverity.CRITICAL,
            actual_value=["response"],
            expected_value=["response", "model", "usage"],
            message="Missing fields: model, usage",
        )

        data = result.model_dump()
        restored = ModelInvariantResult.model_validate(data)

        assert restored.actual_value == ["response"]
        assert restored.expected_value == ["response", "model", "usage"]

    def test_result_with_numeric_values(self) -> None:
        """Result handles numeric actual/expected values."""
        result = ModelInvariantResult(
            invariant_id=TEST_UUID,
            invariant_name="Latency check",
            passed=False,
            severity=EnumSeverity.WARNING,
            actual_value=6500,
            expected_value=5000,
            message="Latency exceeded threshold: 6500ms > 5000ms",
        )

        data = result.model_dump()
        restored = ModelInvariantResult.model_validate(data)

        assert restored.actual_value == 6500
        assert restored.expected_value == 5000


@pytest.mark.unit
class TestInvariantSetSerialization:
    """Test ModelInvariantSet serialization."""

    def test_invariant_set_serialization(self) -> None:
        """InvariantSet with multiple invariants serializes correctly."""
        inv1 = ModelInvariant(
            name="Latency check",
            type=EnumInvariantType.LATENCY,
            severity=EnumSeverity.WARNING,
            config={"max_ms": 5000},
        )
        inv2 = ModelInvariant(
            name="Cost check",
            type=EnumInvariantType.COST,
            severity=EnumSeverity.CRITICAL,
            config={"max_cost": 0.10, "per": "request"},
        )

        inv_set = ModelInvariantSet(
            name="Test Set",
            target="node_llm_call",
            invariants=[inv1, inv2],
        )

        data = inv_set.model_dump()
        restored = ModelInvariantSet.model_validate(data)

        assert len(restored.invariants) == 2
        assert restored.name == "Test Set"
        assert restored.target == "node_llm_call"

    def test_invariant_set_preserves_invariant_order(self) -> None:
        """InvariantSet preserves order of invariants."""
        invariants = [
            ModelInvariant(
                name=f"Check {i}",
                type=EnumInvariantType.LATENCY,
                config={"max_ms": 1000 * i},
            )
            for i in range(1, 6)
        ]

        inv_set = ModelInvariantSet(
            name="Ordered Set",
            target="node_test",
            invariants=invariants,
        )

        data = inv_set.model_dump()
        restored = ModelInvariantSet.model_validate(data)

        for i, inv in enumerate(restored.invariants):
            assert inv.name == f"Check {i + 1}"

    def test_invariant_set_json_serialization(self) -> None:
        """InvariantSet should serialize to valid JSON."""
        inv = ModelInvariant(
            name="Test",
            type=EnumInvariantType.LATENCY,
            config={"max_ms": 5000},
        )

        inv_set = ModelInvariantSet(
            name="Test Set",
            target="node_test",
            invariants=[inv],
        )

        json_str = inv_set.model_dump_json()
        assert isinstance(json_str, str)

        parsed = json.loads(json_str)
        assert parsed["name"] == "Test Set"
        assert len(parsed["invariants"]) == 1

    def test_invariant_set_with_empty_invariants(self) -> None:
        """InvariantSet with empty invariants list."""
        inv_set = ModelInvariantSet(
            name="Empty Set",
            target="node_test",
            invariants=[],
        )

        data = inv_set.model_dump()
        restored = ModelInvariantSet.model_validate(data)

        assert len(restored.invariants) == 0
        assert restored.name == "Empty Set"

    def test_invariant_set_with_description(self) -> None:
        """InvariantSet with optional description."""
        inv_set = ModelInvariantSet(
            name="Described Set",
            target="node_llm_call",
            invariants=[],
            description="A set of invariants for LLM call validation",
        )

        data = inv_set.model_dump()
        restored = ModelInvariantSet.model_validate(data)

        assert restored.description == "A set of invariants for LLM call validation"


@pytest.mark.unit
class TestSerializationRoundTrips:
    """Test complete serialization round trips."""

    def test_full_invariant_set_roundtrip(self) -> None:
        """Complete InvariantSet round trip through JSON."""
        # Create a comprehensive invariant set
        invariants = [
            ModelInvariant(
                name="Latency check",
                type=EnumInvariantType.LATENCY,
                severity=EnumSeverity.WARNING,
                config={"max_ms": 5000},
                description="Check response time",
            ),
            ModelInvariant(
                name="Cost check",
                type=EnumInvariantType.COST,
                severity=EnumSeverity.CRITICAL,
                config={"max_cost": 0.10, "per": "request"},
                enabled=True,
            ),
            ModelInvariant(
                name="Field check",
                type=EnumInvariantType.FIELD_PRESENCE,
                severity=EnumSeverity.WARNING,
                config={"fields": ["response", "model"]},
            ),
            ModelInvariant(
                name="Schema check",
                type=EnumInvariantType.SCHEMA,
                severity=EnumSeverity.CRITICAL,
                config={
                    "json_schema": {
                        "type": "object",
                        "required": ["response"],
                    }
                },
            ),
        ]

        original_set = ModelInvariantSet(
            name="Comprehensive Validation",
            target="node_llm_call",
            invariants=invariants,
            description="Complete validation set",
        )

        # Serialize to JSON
        json_str = original_set.model_dump_json()

        # Deserialize back
        restored_set = ModelInvariantSet.model_validate_json(json_str)

        # Verify everything preserved
        assert restored_set.name == original_set.name
        assert restored_set.target == original_set.target
        assert restored_set.description == original_set.description
        assert len(restored_set.invariants) == len(original_set.invariants)

        for orig, rest in zip(
            original_set.invariants, restored_set.invariants, strict=True
        ):
            assert rest.name == orig.name
            assert rest.type == orig.type
            assert rest.severity == orig.severity
            assert rest.config == orig.config

    def test_result_list_roundtrip(self) -> None:
        """List of InvariantResults round trip."""
        # Generate unique UUIDs for each result
        test_uuids = [uuid.uuid4() for _ in range(5)]
        results = [
            ModelInvariantResult(
                invariant_id=test_uuids[i],
                invariant_name=f"Check {i}",
                passed=i % 2 == 0,
                severity=EnumSeverity.WARNING,
                actual_value=i * 100,
                expected_value=500,
            )
            for i in range(5)
        ]

        # Serialize each
        json_strs = [r.model_dump_json() for r in results]

        # Deserialize back
        restored = [ModelInvariantResult.model_validate_json(j) for j in json_strs]

        assert len(restored) == 5
        for i, r in enumerate(restored):
            assert r.invariant_name == f"Check {i}"
            assert r.passed == (i % 2 == 0)


@pytest.mark.unit
class TestSerializationEdgeCases:
    """Test serialization edge cases."""

    def test_invariant_with_special_characters(self) -> None:
        """Invariant name with special characters."""
        inv = ModelInvariant(
            name='Check: Response "quoted" & <escaped>',
            type=EnumInvariantType.LATENCY,
            config={"max_ms": 5000},
        )

        json_str = inv.model_dump_json()
        restored = ModelInvariant.model_validate_json(json_str)

        assert restored.name == 'Check: Response "quoted" & <escaped>'

    def test_invariant_with_unicode(self) -> None:
        """Invariant with unicode characters."""
        inv = ModelInvariant(
            name="Check latency",
            type=EnumInvariantType.LATENCY,
            config={"max_ms": 5000},
            description="Verify response time",
        )

        json_str = inv.model_dump_json()
        restored = ModelInvariant.model_validate_json(json_str)

        assert "latency" in restored.name

    def test_invariant_with_large_config(self) -> None:
        """Invariant with large config object."""
        large_schema = {
            "type": "object",
            "properties": {f"field_{i}": {"type": "string"} for i in range(100)},
        }

        inv = ModelInvariant(
            name="Large schema check",
            type=EnumInvariantType.SCHEMA,
            config={"json_schema": large_schema},
        )

        json_str = inv.model_dump_json()
        restored = ModelInvariant.model_validate_json(json_str)

        assert len(restored.config["json_schema"]["properties"]) == 100

    def test_result_with_very_long_message(self) -> None:
        """Result with very long message."""
        long_message = "Error: " + "x" * 10000

        result = ModelInvariantResult(
            invariant_id=TEST_UUID,
            invariant_name="Test",
            passed=False,
            severity=EnumSeverity.CRITICAL,
            message=long_message,
        )

        json_str = result.model_dump_json()
        restored = ModelInvariantResult.model_validate_json(json_str)

        assert len(restored.message) == len(long_message)
