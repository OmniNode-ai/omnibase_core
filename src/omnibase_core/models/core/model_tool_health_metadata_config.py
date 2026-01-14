"""
Tool Health Metadata Model Config.

Pydantic configuration for tool health metadata.
"""


class ModelConfig:
    """Pydantic configuration."""

    # Example for documentation
    json_schema_extra = {
        "example": {
            "tool_version": "1.0.0",
            "tool_class": "ToolFileGenerator",
            "module_path": "protocol.tools.example.tool_example",
            "health_check_method": "introspection",
            "health_check_endpoint": None,
            "error_level_count": 0,
            "warning_count": 1,
            "last_error_message": None,
            "average_response_time_ms": 125.5,
            "success_rate_percentage": 99.2,
            "uptime_seconds": 3600.0,
            "restart_count": 0,
            "health_tags": ["stable", "production"],
        },
    }
