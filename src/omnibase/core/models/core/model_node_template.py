# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# created_at: '2025-05-28T08:55:08.192993'
# description: Stamped by ToolPython
# entrypoint: python://model_node_template
# hash: 7d79e96d4a5e0a67e6ab164f4e1785b4128189c59051d91e405218d4e1de2124
# last_modified_at: '2025-05-29T14:13:58.840604+00:00'
# lifecycle: active
# meta_type: tool
# metadata_version: 0.1.0
# name: model_node_template.py
# namespace: python://omnibase.model.model_node_template
# owner: OmniNode Team
# protocol_version: 0.1.0
# runtime_language_hint: python>=3.11
# schema_version: 0.1.0
# state_contract: state_contract://default
# tools: null
# uuid: 84fe390c-7b09-4155-9833-42e47dd69e0c
# version: 1.0.0
# === /OmniNode:Metadata ===


"""
Pydantic model for node template configuration.

This module provides structured configuration for node template generation,
including template metadata, file mappings, and generation options.
"""

from typing import Dict, List

from pydantic import BaseModel, ConfigDict, Field


class ModelNodeTemplateConfig(BaseModel):
    """
    Configuration model for node template generation.

    This model defines the structure and options for generating new nodes
    from templates, including metadata, file mappings, and customization options.
    """

    template_version: str = Field(
        description="Version of the template system being used"
    )
    node_name: str = Field(description="Name of the node to generate")
    namespace_prefix: str = Field(
        default="omnibase.nodes", description="Namespace prefix for the generated node"
    )
    default_lifecycle: str = Field(
        default="active", description="Default lifecycle state for generated nodes"
    )
    default_author: str = Field(
        default="OmniNode Team", description="Default author for generated nodes"
    )
    template_files: Dict[str, str] = Field(
        description="Mapping of template source files to destination paths"
    )
    generated_files: List[str] = Field(
        description="List of files that will be generated from templates"
    )

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
            }
        },
    )
