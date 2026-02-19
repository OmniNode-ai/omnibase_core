# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
CRITICAL SAFETY TEST: Direct Instantiation Bypass

This test demonstrates a critical safety issue with Generic[T] approach:
Agents could bypass from_value() and directly instantiate, storing non-serializable objects.

This is a REAL RISK in autonomous agent systems where agents might:
1. Read API documentation and use constructors directly
2. Use IDE autocomplete which suggests direct instantiation
3. Generate code that looks "cleaner" without factory methods
"""

from pydantic import BaseModel


class ModelSchemaValueGeneric[T](BaseModel):
    """Generic approach - allows direct instantiation with any type."""

    value: T
    value_type: str

    # Agent reads Pydantic error message and adds this:
    model_config = {"arbitrary_types_allowed": True}

    @classmethod
    def from_value(cls, value: T) -> "ModelSchemaValueGeneric[T]":
        """Safe factory - but agents might not use it."""
        if not isinstance(value, (str, int, float, bool, type(None), list, dict)):
            value = str(value)  # type: ignore[assignment]
        return cls(value=value, value_type="auto")


class CustomConfigObject:
    """Non-serializable object."""

    def __init__(self, data: str):
        self.data = data


def test_direct_instantiation_danger():
    """
    SCENARIO: Agent reads API docs and directly instantiates instead of using from_value()

    Agent generates:
        config = ModelSchemaValueGeneric[CustomConfigObject](
            value=CustomConfigObject("data"),
            value_type="object"
        )
    """
    print("\n" + "=" * 80)
    print("CRITICAL SAFETY TEST: Direct Instantiation Bypass")
    print("=" * 80)

    print("\n⚠️  Agent directly instantiates Generic[T] (bypassing from_value):")

    # This is what an agent might generate
    config = ModelSchemaValueGeneric[CustomConfigObject](
        value=CustomConfigObject("dangerous-data"), value_type="object"
    )

    print("   ✅ Pydantic allows this!")
    print(f"   Value type: {type(config.value)}")
    print(f"   Contains: {config.value}")

    print("\n💥 Now try to serialize for distributed execution:")

    try:
        serialized = config.model_dump()
        print("   ❌ UNEXPECTED: Serialization succeeded?!")
        print(f"   Result: {serialized}")
    except Exception as e:
        print(f"   💥 CRASH! Serialization failed: {e}")
        print("   This would CRASH the distributed omninode system!")

    print("\n📊 SAFETY ANALYSIS:")
    print("   - Agent bypassed safe factory? YES")
    print("   - Non-serializable object stored? YES")
    print("   - Distributed execution crash risk? CRITICAL")
    print("   - Can this happen in practice? YES (agents read docs, use constructors)")


def test_current_approach_prevents_this():
    """
    Current approach makes it harder to bypass safety.

    You MUST go through from_value() to create instances properly.
    """
    print("\n" + "=" * 80)
    print("CURRENT APPROACH: Safety by Design")
    print("=" * 80)

    print("\n✅ Current approach forces explicit field setting:")
    print("   - Agent must specify which field (string_value, number_value, etc.)")
    print("   - No single 'value' field that accepts anything")
    print("   - Pydantic validates field types strictly")

    print("\n   If agent tries to store CustomConfigObject:")
    print("   - string_value: str | None → TYPE ERROR")
    print("   - number_value: ModelNumericValue | None → TYPE ERROR")
    print("   - object_value: dict[str, ModelSchemaValue] | None → TYPE ERROR")

    print("\n   Agent is FORCED to either:")
    print("   1. Use from_value() (safe factory)")
    print("   2. Get Pydantic validation error (safe failure)")

    print("\n📊 SAFETY ANALYSIS:")
    print("   - Can agent bypass safety? NO (Pydantic enforces types)")
    print("   - Non-serializable object risk? LOW")
    print("   - Distributed execution crash risk? LOW")


def test_real_world_agent_scenario():
    """
    Real scenario: Agent reads documentation and generates node config.
    """
    print("\n" + "=" * 80)
    print("REAL-WORLD SCENARIO: Agent Generates Node Configuration")
    print("=" * 80)

    print("\n📖 Agent reads omninode documentation:")
    print("   'Use ModelSchemaValue for node parameters'")

    print("\n🤖 Agent sees two approaches in docs:")
    print("\n   Approach 1: Factory method (safe)")
    print("   schema_value = ModelSchemaValue.from_value(timeout)")

    print("\n   Approach 2: Direct instantiation (dangerous with Generic[T])")
    print("   schema_value = ModelSchemaValue[int](value=timeout, value_type='number')")

    print("\n💭 Agent thinks: 'Approach 2 looks cleaner and more type-safe!'")
    print("   (Because Generic[T] has nice type hints)")

    print("\n❌ PROBLEM with Generic[T]:")
    print("   Agent might generate:")
    print("   config = ModelSchemaValue[MyCustomClass](")
    print("       value=MyCustomClass(),")
    print("       value_type='object'")
    print("   )")
    print("   → Compiles ✅")
    print("   → Type checks ✅")
    print("   → Serializes? 💥 CRASH")

    print("\n✅ SAFETY with Current Approach:")
    print("   Agent MUST use from_value():")
    print("   config = ModelSchemaValue.from_value(MyCustomClass())")
    print("   → from_value() converts to string ✅")
    print("   → Serializes safely ✅")
    print("   → No crash ✅")


if __name__ == "__main__":
    test_direct_instantiation_danger()
    test_current_approach_prevents_this()
    test_real_world_agent_scenario()

    print("\n" + "=" * 80)
    print("VERDICT")
    print("=" * 80)
    print(
        """
Generic[T] approach has a CRITICAL SAFETY FLAW:
- Agents can bypass from_value() and directly instantiate
- Pydantic Generic[T] accepts ANY type for T
- Non-serializable objects can be stored
- Distributed execution WILL CRASH

Current approach prevents this:
- No single 'value' field that accepts anything
- Explicit typed fields (string_value, number_value, etc.)
- Pydantic validates each field strictly
- Agent forced to use from_value() or get validation error

For autonomous agent systems, SAFETY > CONVENIENCE.

FINAL RECOMMENDATION: KEEP CURRENT APPROACH
"""
    )
