"""
ModelIntrospectionResult configuration.
"""


class ModelIntrospectionResultConfig:
    json_schema_extra = {
        "example": {
            "metadata": {
                "node_info": {
                    "node_name": "example_tool",
                    "node_version": {"major": 1, "minor": 0, "patch": 0},
                    "description": "Example tool",
                    "author": "ONEX System",
                    "tool_type": "generation",
                    "created_at": "2024-01-01T00:00:00",
                },
                "capabilities": {"introspection": True},
                "contract_info": {
                    "contract_version": {"major": 1, "minor": 0, "patch": 0},
                    "has_definitions": True,
                    "definition_count": 5,
                    "contract_path": "/path/to/contract.yaml",
                },
                "runtime_info": {
                    "python_path": "/path/to/module",
                    "module_path": "omnibase/tools/example",
                    "command_pattern": "python -m protocol.example",
                    "supports_hub": True,
                    "available_modes": ["direct", "workflow"],
                    "memory_usage_mb": 128.5,
                },
                "dependencies": {
                    "imports": ["omnibase.core"],
                    "tools": ["tool_validator"],
                },
                "validation": {
                    "is_modern": True,
                    "has_modern_patterns": True,
                    "cli_discoverable": True,
                    "passes_standards": True,
                },
            },
            "health": {
                "status": "healthy",
                "timestamp": "2024-01-01T00:00:00",
                "tool_name": "example_tool",
                "version": {"major": 1, "minor": 0, "patch": 0},
                "checks": {"contract_exists": True, "models_importable": True},
            },
            "examples": [
                {
                    "description": "Basic Example",
                    "command": "python -m protocol.example",
                    "input_example": {"test": "data"},
                    "expected_output": {"status": "success"},
                },
            ],
        },
    }
