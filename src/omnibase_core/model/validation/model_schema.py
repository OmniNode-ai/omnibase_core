"""
Schema validation models.
"""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field, RootModel

from .model_schema_property import ModelSchemaProperty

# Backward compatibility alias
SchemaPropertyModel = ModelSchemaProperty


class ModelSchemaPropertiesModel(RootModel):
    """
    Strongly typed model for the properties field in a JSON schema.
    Wraps a dict of property names to SchemaPropertyModel.
    """

    root: Dict[str, ModelSchemaProperty]


class ModelRequiredFieldsModel(RootModel):
    """
    Strongly typed model for the required fields in a JSON schema.
    Wraps a list of required property names.
    """

    root: List[str]


class ModelSchema(BaseModel):
    """
    Strongly typed Pydantic model for ONEX JSON schema files.
    Includes canonical fields and is extensible for M1+.
    """

    schema_uri: Optional[str] = Field(None)
    title: Optional[str] = None
    type: Optional[str] = None
    properties: Optional[ModelSchemaPropertiesModel] = None
    required: Optional[ModelRequiredFieldsModel] = None
    # TODO: Add more fields and validation logic in M1+


# Rebuild model for forward references
ModelSchemaProperty.model_rebuild()

# Backward compatibility aliases
SchemaPropertiesModel = ModelSchemaPropertiesModel
RequiredFieldsModel = ModelRequiredFieldsModel
SchemaModel = ModelSchema

# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# created_at: '2025-05-28T13:24:08.068968'
# description: Stamped by ToolPython
# entrypoint: python://model_schema
# hash: 21464ac854e592e214a074cb4c66afb52d6f573e9be594aa2cb038d362589ea3
# last_modified_at: '2025-05-29T14:13:58.933955+00:00'
# lifecycle: active
# meta_type: tool
# metadata_version: 0.1.0
# name: model_schema.py
# namespace: python://omnibase.model.model_schema
# owner: OmniNode Team
# protocol_version: 0.1.0
# runtime_language_hint: python>=3.11
# schema_version: 0.1.0
# state_contract: state_contract://default
# tools: {}
# uuid: bfe429b0-f04f-48dc-9001-655fb19f442f
# version: 1.0.0
# === /OmniNode:Metadata ===
