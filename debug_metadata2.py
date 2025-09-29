#!/usr/bin/env python3
"""Debug the specific failing line from the test."""

from omnibase_core.models.core import ModelCustomProperties
from omnibase_core.models.infrastructure.model_execution_result import (
    ModelExecutionResult,
)

# Test the exact same pattern from the failing test
metadata = ModelCustomProperties()
metadata.set_custom_string("tool", "test_tool")
metadata.set_custom_string("version", "1.0")
result = ModelExecutionResult.ok("value", metadata=metadata)

print("=== Debugging the exact failing pattern ===")
tool_result = result.get_metadata("tool", None)
print(f"Tool result: {tool_result}")
print(f"Tool result type: {type(tool_result)}")
print(f"Tool result == 'test_tool': {tool_result == 'test_tool'}")

# Try calling unwrap just like the test was trying to do
print(f"\nAttempting to call unwrap on tool_result:")
try:
    unwrapped = tool_result.unwrap()
    print(f"Unwrapped successfully: {unwrapped}")
except AttributeError as e:
    print(f"AttributeError: {e}")
    print(f"This means tool_result is a raw string, not a ModelResult object")

# Test if there's any difference between different ways of creating metadata
print("\n=== Testing different metadata creation patterns ===")

result2 = ModelExecutionResult.ok("value")
result2.add_metadata("tool", "test_tool")
tool_result2 = result2.get_metadata("tool", None)
print(f"add_metadata result: {tool_result2} (type: {type(tool_result2)})")

# Let's also test what the original error was showing
print("\n=== Testing to see if some methods return ModelResult ===")
# Maybe custom_values vs direct metadata access behaves differently?
print(f"result.metadata type: {type(result.metadata)}")
print(
    f"dir(result.metadata): {[attr for attr in dir(result.metadata) if not attr.startswith('_')]}"
)
