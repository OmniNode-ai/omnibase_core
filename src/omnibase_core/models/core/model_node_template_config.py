"""
Model configuration for ModelNodeTemplateConfig.
"""

from pydantic import ConfigDict


class ModelNodeTemplateConfigConfig:
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "template_version": "1.0.0",
                "node_name": "my_awesome_node",
                "namespace_prefix": "omnibase.nodes",
                "default_lifecycle": "active",
                "default_author": "OmniNode Team",
                "template_files": {
                    "node_template.py": "node.py",
                    "template_contract.yaml": "contract.yaml",
                },
                "generated_files": [
                    "node.py",
                    "contract.yaml",
                    "node.onex.yaml",
                    ".onexignore",
                ],
            },
        },
    )
