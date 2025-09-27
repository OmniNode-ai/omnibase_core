#!/usr/bin/env python3
"""Debug script to understand get_metadata return values."""

from omnibase_core.models.core import ModelCustomProperties
from omnibase_core.models.infrastructure.model_execution_result import (
    ModelExecutionResult,
    execution_err,
    execution_ok,
    try_execution,
)

# Test different ways of creating results to see which ones return ModelResult vs raw values

print("=== Testing with ModelExecutionResult.ok() and add_metadata ===")
result = ModelExecutionResult.ok("test_value")
result.add_metadata("tool", "test_tool")
tool_value = result.get_metadata("tool", None)
print(f"Tool value: {tool_value}")
print(f"Tool value type: {type(tool_value)}")
print(f"Tool value has unwrap: {hasattr(tool_value, 'unwrap')}")

print("\n=== Testing with ModelExecutionResult.ok() and initial metadata ===")
metadata = ModelCustomProperties()
metadata.set_custom_string("tool", "test_tool")
result2 = ModelExecutionResult.ok("value", metadata=metadata)
tool_value2 = result2.get_metadata("tool", None)
print(f"Tool value: {tool_value2}")
print(f"Tool value type: {type(tool_value2)}")
print(f"Tool value has unwrap: {hasattr(tool_value2, 'unwrap')}")

print("\n=== Testing with execution_ok() ===")
result3 = execution_ok("success", tool_name="test_tool")
tool_value3 = result3.get_metadata("tool_name", None)
print(f"Tool value: {tool_value3}")
print(f"Tool value type: {type(tool_value3)}")
print(f"Tool value has unwrap: {hasattr(tool_value3, 'unwrap')}")


def test_func():
    return "test_result"


print("\n=== Testing with try_execution() ===")
result4 = try_execution(test_func, tool_name="test_tool")
tool_value4 = result4.get_metadata("tool_name", None)
print(f"Tool value: {tool_value4}")
print(f"Tool value type: {type(tool_value4)}")
print(f"Tool value has unwrap: {hasattr(tool_value4, 'unwrap')}")

print("\n=== Testing with create_cli_success() ===")
result5 = ModelExecutionResult.create_cli_success({"output": "data"}, tool_name="tool1")
tool_value5 = result5.get_metadata("tool_name", None)
print(f"Tool value: {tool_value5}")
print(f"Tool value type: {type(tool_value5)}")
print(f"Tool value has unwrap: {hasattr(tool_value5, 'unwrap')}")
