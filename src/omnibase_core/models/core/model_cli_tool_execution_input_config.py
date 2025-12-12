class ModelConfig:
    """Pydantic configuration."""

    # Example for documentation
    json_schema_extra: dict[str, dict[str, object]] = {
        "example": {
            "action": "list_tools",
            "tool_name": None,
            "target_tool": None,
            "include_metadata": True,
            "include_health_info": True,
            "health_filter": True,
            "category_filter": None,
            "timeout_seconds": 30.0,
            "output_format": "default",
            "verbose": False,
            "advanced_params": {},
            "execution_context": "cli_main",
            "request_id": "req_123456",
        },
    }
