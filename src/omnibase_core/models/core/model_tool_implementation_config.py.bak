"""
Tool Implementation Model Config.

Pydantic configuration for tool implementation model.
"""


class ModelConfig:
    """Pydantic configuration."""

    # Allow serialization even with complex types
    arbitrary_types_allowed = True

    # Example for documentation
    json_schema_extra = {
        "example": {
            "tool_name": "tool_file_generator",
            "implementation_class": "ToolFileGenerator",
            "module_path": "protocol.tools.example.tool_example",
            "version": "1.0.0",
            "registry_source": "RegistryFileGenerator",
            "has_process_method": True,
            "accepts_input_state": True,
            "returns_output_state": True,
            "is_healthy": True,
            "health_message": None,
            "instance_available": True,
        },
    }
