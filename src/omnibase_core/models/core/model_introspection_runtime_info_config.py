"""
ModelIntrospectionRuntimeInfo configuration.
"""


class ModelIntrospectionRuntimeInfoConfig:
    json_schema_extra = {
        "example": {
            "python_path": "/path/to/module",
            "module_path": "omnibase/tools/example",
            "command_pattern": "python -m protocol.example",
            "supports_hub": True,
            "available_modes": ["direct", "workflow"],
            "memory_usage_mb": 128.5,
        },
    }
