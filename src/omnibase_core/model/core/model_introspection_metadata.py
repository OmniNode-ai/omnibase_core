"""
Model for complete introspection metadata.
"""

from pydantic import BaseModel, Field

from omnibase_core.model.core.model_introspection_contract_info import (
    ModelIntrospectionContractInfo,
)
from omnibase_core.model.core.model_introspection_node_info import (
    ModelIntrospectionNodeInfo,
)
from omnibase_core.model.core.model_introspection_runtime_info import (
    ModelIntrospectionRuntimeInfo,
)
from omnibase_core.model.core.model_introspection_validation import (
    ModelIntrospectionValidation,
)


class ModelIntrospectionMetadata(BaseModel):
    """Complete introspection metadata for a tool."""

    node_info: ModelIntrospectionNodeInfo = Field(description="Node information")
    capabilities: dict[str, bool] = Field(description="Tool capabilities")
    contract_info: ModelIntrospectionContractInfo = Field(
        description="Contract information",
    )
    runtime_info: ModelIntrospectionRuntimeInfo = Field(
        description="Runtime information",
    )
    dependencies: dict[str, list[str]] = Field(description="Tool dependencies")
    validation: ModelIntrospectionValidation = Field(
        description="Validation information",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "node_info": {
                    "node_name": "tool_example",
                    "node_version": {"major": 1, "minor": 0, "patch": 0},
                    "description": "Example tool",
                    "author": "ONEX System",
                    "tool_type": "generation",
                    "created_at": "2024-01-01T00:00:00",
                },
                "capabilities": {
                    "introspection": True,
                    "cli_discovery": True,
                    "modern_patterns": True,
                },
                "contract_info": {
                    "contract_version": {"major": 1, "minor": 0, "patch": 0},
                    "has_definitions": True,
                    "definition_count": 5,
                    "contract_path": "/path/to/contract.yaml",
                },
                "runtime_info": {
                    "python_path": "/path/to/module",
                    "module_path": "protocol/example",
                    "command_pattern": "python -m protocol.example",
                    "supports_hub": True,
                    "available_modes": ["direct", "workflow"],
                    "memory_usage_mb": 128.5,
                },
                "dependencies": {
                    "imports": ["omnibase.core", "pydantic"],
                    "tools": ["tool_validator", "tool_generator"],
                },
                "validation": {
                    "is_modern": True,
                    "has_modern_patterns": True,
                    "cli_discoverable": True,
                    "passes_standards": True,
                },
            },
        }
