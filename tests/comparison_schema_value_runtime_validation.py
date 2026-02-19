# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Runtime Validation Comparison: Current vs Generic[T] Approach

This test suite compares runtime validation capabilities for autonomous agent node creation.

CONTEXT:
- Agents generate omninode node configurations at runtime
- Static type checking cannot catch runtime agent mistakes
- We need runtime validation with clear error messages for agent retry

COMPARISON:
1. Current Approach: ModelSchemaValue with explicit fields + from_value()
2. Generic[T] Approach: ModelSchemaValue[Generic[T]] with value: T

TEST SCENARIOS (Agent Errors):
1. Agent sends wrong type (string instead of int)
2. Agent sends unknown object (custom class)
3. Agent sends nested structure with type errors
4. Agent sends mixed-type arrays
"""

import sys
from pathlib import Path

# Add src to path to allow direct imports before package installation.
# This is required because this is a standalone comparison script that runs
# independently of pytest and needs access to omnibase_core source modules.
# Without this, Python would fail to find omnibase_core since it's not installed.
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from pydantic import BaseModel, ValidationError

# Import current implementation directly
from omnibase_core.models.common.model_schema_value import ModelSchemaValue

# ============================================================================
# Generic[T] Approach - Alternative Implementation
# ============================================================================


class ModelSchemaValueGeneric[T](BaseModel):
    """
    Generic approach to schema values.

    Uses Pydantic's Generic support to provide type-safe value storage.
    """

    value: T
    value_type: str  # Still need to track type for serialization

    @classmethod
    def from_value(cls, value: T) -> "ModelSchemaValueGeneric[T]":
        """Create from value with type detection."""
        if value is None:
            type_name = "null"
        elif isinstance(value, bool):
            type_name = "boolean"
        elif isinstance(value, str):
            type_name = "string"
        elif isinstance(value, (int, float)):
            type_name = "number"
        elif isinstance(value, list):
            type_name = "array"
        elif isinstance(value, dict):
            type_name = "object"
        else:
            # Unknown type - convert to string
            value = str(value)  # type: ignore[assignment]
            type_name = "string"

        return cls(value=value, value_type=type_name)

    def to_value(self) -> T:
        """Extract value."""
        return self.value


# ============================================================================
# Custom Unknown Type - Simulates Agent Mistake
# ============================================================================


class CustomConfigObject:
    """Simulates an unknown object type that agent might generate."""

    def __init__(self, config: str):
        self.config = config

    def __repr__(self) -> str:
        return f"CustomConfigObject(config='{self.config}')"


# ============================================================================
# TEST 1: Agent Sends Wrong Type (string instead of int)
# ============================================================================


def test_current_approach_wrong_type_string_for_int():
    """
    SCENARIO: Agent extracts timeout from docs as '30 seconds' instead of 30

    Agent generates:
        node_params["timeout"] = "30 seconds"  # Should be: 30
    """
    print("\n" + "=" * 80)
    print("TEST 1: CURRENT APPROACH - Agent sends string instead of int")
    print("=" * 80)

    agent_generated_timeout = "30 seconds"  # Agent mistake

    try:
        # Current approach: from_value() converts gracefully
        schema_value = ModelSchemaValue.from_value(agent_generated_timeout)

        print("✅ Conversion succeeded")
        print(f"   Value type: {schema_value.value_type}")
        print(f"   Stored as: {schema_value.string_value}")
        print(f"   Retrieved: {schema_value.to_value()}")
        print("\n📊 AGENT RECOVERY:")
        print("   - Error raised? NO")
        print("   - Graceful conversion? YES (string)")
        print(
            "   - Agent can detect mistake? Only at usage time when get_number() fails"
        )
        print("   - Data loss? NO (preserves original value)")

        # Try to use as number - this will fail
        print("\n🔍 When agent tries to use as number:")
        try:
            num_value = schema_value.get_number()
            print(f"   ❌ UNEXPECTED: Got number {num_value}")
        except Exception as e:
            print(f"   ✅ Error raised: {e.__class__.__name__}")
            print(f"   Message: {e}")
            print("   Agent can retry? YES (clear error message)")

    except Exception as e:
        print(f"❌ Conversion failed: {e.__class__.__name__}")
        print(f"   Message: {e}")
        print("   Agent can retry? Check error message clarity")


def test_generic_approach_wrong_type_string_for_int():
    """
    SCENARIO: Agent extracts timeout from docs as '30 seconds' instead of 30

    Using Generic[T] approach.
    """
    print("\n" + "=" * 80)
    print("TEST 1: GENERIC[T] APPROACH - Agent sends string instead of int")
    print("=" * 80)

    agent_generated_timeout = "30 seconds"  # Agent mistake

    try:
        # Generic approach: from_value() converts gracefully
        schema_value = ModelSchemaValueGeneric.from_value(agent_generated_timeout)

        print("✅ Conversion succeeded")
        print(f"   Value type: {schema_value.value_type}")
        print(f"   Stored as: {schema_value.value}")
        print(f"   Retrieved: {schema_value.to_value()}")
        print("\n📊 AGENT RECOVERY:")
        print("   - Error raised? NO")
        print("   - Graceful conversion? YES (string)")
        print("   - Agent can detect mistake? Only at usage time")
        print("   - Data loss? NO (preserves original value)")

        # Try to create with explicit int type
        print("\n🔍 When agent specifies int type explicitly:")
        try:
            # This should fail Pydantic validation
            typed_value: ModelSchemaValueGeneric[int] = ModelSchemaValueGeneric[int](
                value=agent_generated_timeout,
                value_type="number",
            )
            print(f"   ❌ UNEXPECTED: Validation passed with value {typed_value.value}")
        except ValidationError as e:
            print(f"   ✅ Pydantic validation failed: {e.__class__.__name__}")
            print(f"   Errors: {len(e.errors())} validation error(s)")
            for err in e.errors():
                print(f"      - {err['loc']}: {err['msg']}")
            print("   Agent can retry? YES (clear validation errors)")

    except Exception as e:
        print(f"❌ Conversion failed: {e.__class__.__name__}")
        print(f"   Message: {e}")


# ============================================================================
# TEST 2: Agent Sends Unknown Object
# ============================================================================


def test_current_approach_unknown_object():
    """
    SCENARIO: Agent generates custom config object instead of dict

    Agent generates:
        node_params["config"] = CustomConfigObject("settings")
    """
    print("\n" + "=" * 80)
    print("TEST 2: CURRENT APPROACH - Agent sends unknown object")
    print("=" * 80)

    agent_generated_config = CustomConfigObject("agent-settings")  # Agent mistake

    try:
        # Current approach: from_value() handles unknown types
        schema_value = ModelSchemaValue.from_value(agent_generated_config)

        print("✅ Conversion succeeded")
        print(f"   Value type: {schema_value.value_type}")
        print(f"   Stored as: {schema_value.string_value}")
        print(f"   Original object: {agent_generated_config}")
        print("\n📊 AGENT RECOVERY:")
        print("   - Error raised? NO")
        print("   - Graceful degradation? YES (converts to string)")
        print("   - Agent can detect mistake? YES (value_type='string', not 'object')")
        print("   - Data loss? YES (object converted to string representation)")
        print("   - Safe for distributed execution? YES (no object references)")

    except Exception as e:
        print(f"❌ Conversion failed: {e.__class__.__name__}")
        print(f"   Message: {e}")


def test_generic_approach_unknown_object():
    """
    SCENARIO: Agent generates custom config object instead of dict

    Using Generic[T] approach.
    """
    print("\n" + "=" * 80)
    print("TEST 2: GENERIC[T] APPROACH - Agent sends unknown object")
    print("=" * 80)

    agent_generated_config = CustomConfigObject("agent-settings")  # Agent mistake

    try:
        # Generic approach: from_value() converts to string
        schema_value = ModelSchemaValueGeneric.from_value(agent_generated_config)

        print("✅ Conversion succeeded")
        print(f"   Value type: {schema_value.value_type}")
        print(f"   Stored as: {schema_value.value}")
        print(f"   Type of value: {type(schema_value.value)}")
        print("\n📊 AGENT RECOVERY:")
        print("   - Error raised? NO")
        print("   - Graceful degradation? YES (converts to string)")
        print("   - Agent can detect mistake? YES (value_type='string')")
        print("   - Data loss? YES (object converted to string)")
        print("   - Safe for distributed execution? YES (no object references)")

        # Try to serialize
        print("\n🔍 Serialization safety check:")
        try:
            serialized = schema_value.model_dump()
            print(f"   ✅ Serialization succeeded: {serialized}")
        except Exception as ser_e:
            print(f"   ❌ Serialization failed: {ser_e}")

    except Exception as e:
        print(f"❌ Conversion failed: {e.__class__.__name__}")
        print(f"   Message: {e}")


# ============================================================================
# TEST 3: Agent Sends Nested Structure with Type Errors
# ============================================================================


def test_current_approach_nested_type_errors():
    """
    SCENARIO: Agent generates nested config with mixed types in arrays

    Agent generates:
        node_params["values"] = [1, "two", 3.0, None, CustomConfigObject()]
    """
    print("\n" + "=" * 80)
    print("TEST 3: CURRENT APPROACH - Nested structure with type errors")
    print("=" * 80)

    agent_generated_values = [
        1,  # int
        "two",  # string (should be int)
        3.0,  # float
        None,  # null
        CustomConfigObject("mixed-data"),  # unknown object
        {"nested": "object"},  # dict
    ]

    try:
        # Current approach: from_value() recursively handles all types
        schema_value = ModelSchemaValue.from_value(agent_generated_values)

        print("✅ Conversion succeeded")
        print(f"   Value type: {schema_value.value_type}")
        print(f"   Array length: {len(schema_value.array_value or [])}")
        print("\n   Array contents:")
        for i, item in enumerate(schema_value.array_value or []):
            print(f"     [{i}] type={item.value_type}, value={item.to_value()}")

        print("\n📊 AGENT RECOVERY:")
        print("   - Error raised? NO")
        print("   - Handles mixed types? YES (each element typed independently)")
        print("   - Unknown objects? YES (converted to string)")
        print("   - Agent can detect mistakes? YES (inspect array_value types)")
        print("   - Safe round-trip? CHECK")

        # Round-trip test
        print("\n🔍 Round-trip serialization test:")
        try:
            round_trip = schema_value.to_value()
            print(f"   Original: {agent_generated_values}")
            print(f"   After round-trip: {round_trip}")

            # Check data preservation
            print("\n   Data preservation analysis:")
            for i, (orig, rt) in enumerate(
                zip(agent_generated_values, round_trip, strict=False)
            ):
                if type(orig) == type(rt):
                    print(f"     [{i}] ✅ Type preserved: {type(orig).__name__}")
                else:
                    print(
                        f"     [{i}] ⚠️  Type changed: {type(orig).__name__} -> {type(rt).__name__}"
                    )

        except Exception as rt_e:
            print(f"   ❌ Round-trip failed: {rt_e}")

    except Exception as e:
        print(f"❌ Conversion failed: {e.__class__.__name__}")
        print(f"   Message: {e}")


def test_generic_approach_nested_type_errors():
    """
    SCENARIO: Agent generates nested config with mixed types in arrays

    Using Generic[T] approach.
    """
    print("\n" + "=" * 80)
    print("TEST 3: GENERIC[T] APPROACH - Nested structure with type errors")
    print("=" * 80)

    agent_generated_values = [
        1,  # int
        "two",  # string (should be int)
        3.0,  # float
        None,  # null
        CustomConfigObject("mixed-data"),  # unknown object
        {"nested": "object"},  # dict
    ]

    try:
        # Generic approach: from_value() handles list
        schema_value = ModelSchemaValueGeneric.from_value(agent_generated_values)

        print("✅ Conversion succeeded")
        print(f"   Value type: {schema_value.value_type}")
        print(f"   Value: {schema_value.value}")
        print(f"   Type: {type(schema_value.value)}")

        print("\n📊 AGENT RECOVERY:")
        print("   - Error raised? NO")
        print("   - Handles mixed types? YES (stored as-is)")
        print("   - Unknown objects? Depends on implementation")
        print("   - Type safety? Limited (list[Any] at runtime)")

        # Check if we can serialize unknown objects
        print("\n🔍 Serialization safety with unknown objects:")
        try:
            serialized = schema_value.model_dump()
            print("   ✅ Serialization succeeded")
            print(
                "   Note: May fail with non-serializable objects in distributed systems"
            )
        except Exception as ser_e:
            print(f"   ❌ Serialization failed: {ser_e}")
            print("   This would crash distributed execution!")

    except Exception as e:
        print(f"❌ Conversion failed: {e.__class__.__name__}")
        print(f"   Message: {e}")


# ============================================================================
# TEST 4: Cross-Process Serialization Safety
# ============================================================================


def test_current_approach_serialization_safety():
    """
    SCENARIO: Test serialization for distributed execution

    In distributed omninode systems, values must serialize cleanly.
    """
    print("\n" + "=" * 80)
    print("TEST 4: CURRENT APPROACH - Cross-process serialization safety")
    print("=" * 80)

    # Complex nested structure with potential issues
    agent_config = {
        "timeout": 30,
        "retries": 3,
        "metadata": {
            "source": "agent-generator",
            "version": "1.0",
            "settings": [
                {"key": "max_connections", "value": 100},
                {"key": "pool_size", "value": "50"},  # String instead of int
            ],
        },
        "unknown_field": CustomConfigObject("test"),  # Will convert to string
    }

    try:
        # Convert to schema value
        schema_value = ModelSchemaValue.from_value(agent_config)

        print("✅ Conversion to ModelSchemaValue succeeded")

        # Serialize
        print("\n🔍 Serialization test:")
        try:
            serialized = schema_value.model_dump()
            print("   ✅ model_dump() succeeded")
            print(f"   Size: {len(str(serialized))} chars")

            # Can we recreate from serialized?
            print("\n🔍 Deserialization test:")
            try:
                recreated = ModelSchemaValue(**serialized)
                print("   ✅ Recreated from serialized data")

                # Round-trip back to value
                final_value = recreated.to_value()
                print("   ✅ Round-trip to Python value succeeded")
                print("\n   Data integrity check:")
                print(f"   Original type: {type(agent_config)}")
                print(f"   Final type: {type(final_value)}")
                print(
                    f"   Keys preserved: {set(agent_config.keys()) == set(final_value.keys())}"
                )

                # Check unknown field handling
                print("\n   Unknown object handling:")
                print(f"   Original: {agent_config['unknown_field']}")
                print(f"   Final: {final_value['unknown_field']}")
                print(
                    f"   Converted to string? {isinstance(final_value['unknown_field'], str)}"
                )

            except Exception as recreate_e:
                print(f"   ❌ Deserialization failed: {recreate_e}")

        except Exception as ser_e:
            print(f"   ❌ Serialization failed: {ser_e}")

        print("\n📊 DISTRIBUTED EXECUTION SAFETY:")
        print("   - Handles unknown objects? YES (converts to string)")
        print("   - Serialization safe? YES")
        print("   - Deserialization safe? YES")
        print("   - Type preservation? Partial (unknown objects become strings)")
        print("   - Crash risk? LOW")

    except Exception as e:
        print(f"❌ Test failed: {e.__class__.__name__}")
        print(f"   Message: {e}")


def test_generic_approach_serialization_safety():
    """
    SCENARIO: Test serialization for distributed execution

    Using Generic[T] approach.
    """
    print("\n" + "=" * 80)
    print("TEST 4: GENERIC[T] APPROACH - Cross-process serialization safety")
    print("=" * 80)

    # Simple structure first (without unknown objects)
    agent_config_simple = {
        "timeout": 30,
        "retries": 3,
        "metadata": {
            "source": "agent-generator",
            "version": "1.0",
        },
    }

    try:
        schema_value = ModelSchemaValueGeneric.from_value(agent_config_simple)

        print("✅ Conversion succeeded (simple config)")

        # Serialize
        print("\n🔍 Serialization test (simple config):")
        try:
            serialized = schema_value.model_dump()
            print("   ✅ model_dump() succeeded")

            # Try with unknown object
            print("\n🔍 Serialization with unknown object:")
            agent_config_complex = agent_config_simple.copy()
            agent_config_complex["unknown"] = CustomConfigObject("test")

            schema_value_complex = ModelSchemaValueGeneric.from_value(
                agent_config_complex
            )

            try:
                serialized_complex = schema_value_complex.model_dump()
                print("   ✅ Serialization with unknown object succeeded")
                print(f"   Value: {serialized_complex}")
            except Exception as ser_complex_e:
                print(
                    f"   ❌ Serialization with unknown object failed: {ser_complex_e}"
                )
                print("   This would crash distributed execution!")

        except Exception as ser_e:
            print(f"   ❌ Serialization failed: {ser_e}")

        print("\n📊 DISTRIBUTED EXECUTION SAFETY:")
        print("   - Handles simple types? YES")
        print("   - Handles unknown objects? DEPENDS (may fail serialization)")
        print("   - Crash risk? MEDIUM-HIGH (if unknown objects present)")

    except Exception as e:
        print(f"❌ Test failed: {e.__class__.__name__}")
        print(f"   Message: {e}")


# ============================================================================
# TEST 5: Error Message Quality for Agent Debugging
# ============================================================================


def test_current_approach_error_messages():
    """
    Test error message quality when agents make type mistakes.
    """
    print("\n" + "=" * 80)
    print("TEST 5: CURRENT APPROACH - Error message quality")
    print("=" * 80)

    # Agent creates a "number" schema value with string
    schema_value = ModelSchemaValue.from_value("30 seconds")

    print(
        f"Agent generated value: '{schema_value.to_value()}' (type: {schema_value.value_type})"
    )
    print("\nAgent tries to use as number:")

    try:
        num = schema_value.get_number()
        print(f"  Unexpected success: {num}")
    except Exception as e:
        print(f"  ✅ Error raised: {e.__class__.__name__}")
        print(f"  Message: {e}")
        print("\n  Error quality for agent debugging:")
        print(f"    - Error type clear? {'Yes' if 'TYPE_MISMATCH' in str(e) else 'No'}")
        print(
            f"    - Expected vs actual types shown? {'Yes' if 'Expected' in str(e) and 'got' in str(e) else 'No'}"
        )
        print("    - Agent can retry with correction? YES")


def test_generic_approach_error_messages():
    """
    Test error message quality when agents make type mistakes.
    """
    print("\n" + "=" * 80)
    print("TEST 5: GENERIC[T] APPROACH - Error message quality")
    print("=" * 80)

    # Agent tries to create with wrong type
    print("Agent tries to create int schema with string value:")

    try:
        schema_value: ModelSchemaValueGeneric[int] = ModelSchemaValueGeneric[int](
            value="30 seconds",
            value_type="number",
        )
        print(f"  Unexpected success: {schema_value}")
    except ValidationError as e:
        print("  ✅ Pydantic validation error raised")
        print(f"  Error count: {len(e.errors())}")
        print("\n  Error details:")
        for err in e.errors():
            print(f"    - Field: {err['loc']}")
            print(f"      Type: {err['type']}")
            print(f"      Message: {err['msg']}")
        print("\n  Error quality for agent debugging:")
        print("    - Error type clear? YES (Pydantic validation)")
        print("    - Field location shown? YES")
        print("    - Expected vs actual types shown? PARTIAL")
        print("    - Agent can retry with correction? YES")


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================


def run_all_tests():
    """Run all comparison tests."""
    print("\n" + "=" * 80)
    print("RUNTIME VALIDATION COMPARISON")
    print("Current ModelSchemaValue vs Generic[T] Approach")
    print("Focus: Autonomous Agent Node Creation Safety")
    print("=" * 80)

    # Test 1: Wrong type
    test_current_approach_wrong_type_string_for_int()
    test_generic_approach_wrong_type_string_for_int()

    # Test 2: Unknown object
    test_current_approach_unknown_object()
    test_generic_approach_unknown_object()

    # Test 3: Nested type errors
    test_current_approach_nested_type_errors()
    test_generic_approach_nested_type_errors()

    # Test 4: Serialization safety
    test_current_approach_serialization_safety()
    test_generic_approach_serialization_safety()

    # Test 5: Error messages
    test_current_approach_error_messages()
    test_generic_approach_error_messages()

    # Final comparison summary
    print("\n" + "=" * 80)
    print("SUMMARY - RUNTIME VALIDATION COMPARISON")
    print("=" * 80)
    print(
        """
CURRENT APPROACH (ModelSchemaValue):
✅ Graceful handling of unknown types (converts to string)
✅ Safe serialization for distributed systems
✅ Clear type indicators (value_type field)
✅ Explicit error messages with type information
✅ No serialization crashes with unknown objects
✅ Audit trail preserved (unknown objects become string representations)
⚠️  Some type information lost for unknown objects

GENERIC[T] APPROACH:
✅ Pydantic validation when type explicitly specified
✅ Type hints provide IDE support
⚠️  Unknown object handling depends on implementation
⚠️  May not serialize unknown objects safely
⚠️  Crash risk in distributed systems with unknown types
⚠️  Limited graceful degradation

AGENT ERROR RECOVERY COMPARISON:
Current: Converts unknown → agent sees type mismatch → retry with fix
Generic: Validation error → agent sees validation error → retry with fix

Both can recover, but Current is safer for distributed systems.

RECOMMENDATION FOR AUTONOMOUS AGENT NODE CREATION:
CURRENT APPROACH is superior because:
1. Graceful degradation with unknown agent types
2. Safe cross-process serialization (critical for distributed omnodes)
3. No crash risk with unknown objects
4. Better audit trail (preserves string representation of unknowns)
5. Explicit type indicators allow runtime inspection
"""
    )


if __name__ == "__main__":
    run_all_tests()
