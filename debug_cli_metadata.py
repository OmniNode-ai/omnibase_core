#!/usr/bin/env python3
"""Debug CLI result metadata behavior."""

from omnibase_core.models.infrastructure.model_execution_result import (
    ModelExecutionResult,
)

# Test the CLI result conversion pattern
result = ModelExecutionResult.ok("test_output")
result.add_metadata("tool_name", "test_tool")
result.add_metadata("status_code", 0)
result.mark_completed()

cli_result = result.to_cli_result()

print("=== CLI Result Metadata Debug ===")
print(f"cli_result type: {type(cli_result)}")
print(f"cli_result.metadata type: {type(cli_result.metadata)}")
print(f"cli_result: {cli_result}")

# Check output_data
print(f"\ncli_result.output_data: {cli_result.output_data}")
print(f"cli_result.output_data type: {type(cli_result.output_data)}")

# Check tool name
print(
    f"\ncli_result.tool_display_name: {getattr(cli_result, 'tool_display_name', 'Not found')}"
)
print(f"cli_result.tool_name: {getattr(cli_result, 'tool_name', 'Not found')}")

# Check available attributes
print(
    f"\nCLI result attributes: {[attr for attr in dir(cli_result) if not attr.startswith('_')]}"
)

# Test the specific failing line
print(f"\ncli_result.metadata.get_custom_value('tool_name'):")
try:
    tool_name_result = cli_result.metadata.get_custom_value("tool_name")
    print(f"Result: {tool_name_result}")
    print(f"Type: {type(tool_name_result)}")
    print(f"Has unwrap: {hasattr(tool_name_result, 'unwrap')}")

    if hasattr(tool_name_result, "unwrap"):
        try:
            unwrapped = tool_name_result.unwrap()
            print(f"Unwrapped: {unwrapped}")
            print(f"Unwrapped type: {type(unwrapped)}")
            if hasattr(unwrapped, "to_value"):
                final_value = unwrapped.to_value()
                print(f"Final value: {final_value}")
            else:
                print(f"Unwrapped value doesn't have to_value method")
        except Exception as e:
            print(f"Error unwrapping: {e}")
    else:
        print(f"Direct value (no unwrap needed): {tool_name_result}")

except Exception as e:
    print(f"Error: {e}")
