"""
Pydantic models and validators for OmniNode metadata block schema and validation.
"""

import re
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from pydantic import BaseModel, Field, field_validator

from omnibase_core.core.core_error_codes import CoreErrorCode
from omnibase_core.enums import (MetaTypeEnum, ProtocolVersionEnum,
                                 RuntimeLanguageEnum)
from omnibase_core.enums.enum_metadata import Lifecycle
from omnibase_core.exceptions import OnexError
from omnibase_core.model.configuration.model_metadata_config import \
    ModelMetadataConfig
from omnibase_core.model.core.model_tool_collection import ToolCollection

from .model_metadata_block import ModelMetadataBlock

MetadataBlockModel = ModelMetadataBlock

# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# created_at: '2025-05-28T13:24:07.953697'
# description: Stamped by ToolPython
# entrypoint: python://model_metadata
# hash: 0c97040ceeb19c084a87b56c21caa638de869140dea9213ba94377c18c2211bc
# last_modified_at: '2025-05-29T14:13:58.812156+00:00'
# lifecycle: active
# meta_type: tool
# metadata_version: 0.1.0
# name: model_metadata.py
# namespace: python://omnibase.model.model_metadata
# owner: OmniNode Team
# protocol_version: 0.1.0
# runtime_language_hint: python>=3.11
# schema_version: 0.1.0
# state_contract: state_contract://default
# tools: {}
# uuid: e6643a2d-cc06-4e80-8363-e98081c99afc
# version: 1.0.0
# === /OmniNode:Metadata ===

if TYPE_CHECKING:
    from omnibase_core.model.core.model_node_metadata import Namespace

    """
    Canonical ONEX metadata block for validators/tools.
    - tools: ToolCollection (not dict[str, Any])
    - meta_type: MetaTypeEnum (not str)
    - lifecycle: Lifecycle (not str)
    """

    metadata_version: str = Field(
        ..., description="Must be a semver string, e.g., '0.1.0'"
    )
    name: str = Field(..., description="Validator/tool name")
    namespace: "Namespace"
    version: str = Field(..., description="Semantic version, e.g., 0.1.0")
    entrypoint: Optional[str] = Field(
        None, description="Entrypoint URI string (e.g., python://file.py)"
    )
    protocols_supported: List[str] = Field(
        ..., description="List of supported protocols"
    )
    protocol_version: ProtocolVersionEnum = Field(
        ..., description="Protocol version, e.g., 0.1.0"
    )
    author: str = Field(...)
    owner: str = Field(...)
    copyright: str = Field(...)
    created_at: str = Field(...)
    last_modified_at: str = Field(...)
    description: Optional[str] = Field(
        None, description="Optional description of the validator/tool"
    )
    tags: Optional[List[str]] = Field(None, description="Optional list of tags")
    dependencies: Optional[List[str]] = Field(
        None, description="Optional list of dependencies"
    )
    config: Optional[ModelMetadataConfig] = Field(
        None, description="Optional config model"
    )
    meta_type: MetaTypeEnum = Field(
        default=MetaTypeEnum.UNKNOWN, description="Meta type of the node/tool"
    )
    runtime_language_hint: RuntimeLanguageEnum = Field(
        RuntimeLanguageEnum.UNKNOWN, description="Runtime language hint"
    )
    tools: Optional[ToolCollection] = None
    lifecycle: Lifecycle = Field(default=Lifecycle.ACTIVE)

    @field_validator("metadata_version")
    @classmethod
    def check_metadata_version(cls, v: str) -> str:
        if not re.match(r"^\d+\.\d+\.\d+$", v):
            raise OnexError(
                "metadata_version must be a semver string, e.g., '0.1.0'",
                CoreErrorCode.VALIDATION_ERROR,
            )
        return v

    @field_validator("name")
    @classmethod
    def check_name(cls, v: str) -> str:
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", v):
            raise OnexError(f"Invalid name: {v}", CoreErrorCode.VALIDATION_ERROR)
        return v

    @field_validator("namespace", mode="before")
    @classmethod
    def check_namespace(cls, v):
        from omnibase_core.model.core.model_node_metadata import Namespace

        if isinstance(v, Namespace):
            return v
        if isinstance(v, str):
            return Namespace(value=v)
        if isinstance(v, dict) and "value" in v:
            return Namespace(**v)
        raise ValueError("Namespace must be a Namespace, str, or dict with 'value'")

    @field_validator("version")
    @classmethod
    def check_version(cls, v: str) -> str:
        if not re.match(r"^\d+\.\d+\.\d+$", v):
            raise OnexError(f"Invalid version: {v}", CoreErrorCode.VALIDATION_ERROR)
        return v

    @field_validator("protocols_supported", mode="before")
    @classmethod
    def check_protocols_supported(cls, v: list[str] | str) -> list[str]:
        if isinstance(v, str):
            # Try to parse as list from string
            import ast

            try:
                v = ast.literal_eval(v)
            except Exception:
                raise OnexError(
                    f"protocols_supported must be a list, got: {v}",
                    CoreErrorCode.VALIDATION_ERROR,
                )
        if not isinstance(v, list):
            raise OnexError(
                f"protocols_supported must be a list, got: {v}",
                CoreErrorCode.VALIDATION_ERROR,
            )
        return v

    @field_validator("entrypoint", mode="before")
    def validate_entrypoint(cls, v):
        if v is None or v == "":
            return None
        if isinstance(v, str) and "://" in v:
            return v
        raise ValueError(
            f"Entrypoint must be a URI string (e.g., python://file.py), got: {v}"
        )


class ModelMetadata(BaseModel):
    meta_type: str = Field(..., description="Type of metadata block")
    metadata_version: str = Field(..., description="Version of the metadata schema")
    schema_version: str = Field(..., description="Version of the content schema")
    uuid: str = Field(..., description="Unique identifier for this file")
    name: str = Field(..., description="File name")
    version: str = Field(..., description="File version")
    author: str = Field(..., description="Author of the file")
    created_at: datetime = Field(..., description="Creation timestamp")
    last_modified_at: datetime = Field(..., description="Last modification timestamp")
    description: Optional[str] = Field(None, description="Description of the file")
    state_contract: Optional[str] = Field(None, description="State contract reference")
    lifecycle: Optional[str] = Field(None, description="Lifecycle state")
    hash: str = Field(..., description="Canonical content hash")
    entrypoint: Optional[str] = Field(None, description="Entrypoint information")
    namespace: Optional[str] = Field(None, description="Namespace for the file")
