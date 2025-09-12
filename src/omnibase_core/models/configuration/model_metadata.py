"""
Pydantic models and validators for OmniNode metadata block schema and validation.
"""

from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field, field_validator

from .model_metadata_block import ModelMetadataBlock

if TYPE_CHECKING:
    from omnibase_core.enums.enum_lifecycle import Lifecycle
    from omnibase_core.enums.enum_meta_type import MetaTypeEnum
    from omnibase_core.enums.enum_runtime_language import RuntimeLanguageEnum
else:
    from omnibase_core.enums.enum_lifecycle import Lifecycle
    from omnibase_core.enums.enum_meta_type import MetaTypeEnum
    from omnibase_core.enums.enum_runtime_language import RuntimeLanguageEnum

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
    import re

    from omnibase_core.core.core_error_codes import CoreErrorCode
    from omnibase_core.enums import (
        MetaTypeEnum,
        ProtocolVersionEnum,
        RuntimeLanguageEnum,
    )
    from omnibase_core.enums.enum_metadata import Lifecycle
    from omnibase_core.exceptions import OnexError
    from omnibase_core.models.configuration.model_metadata_config import (
        ModelMetadataConfig,
    )
    from omnibase_core.models.core.model_node_metadata import Namespace
    from omnibase_core.models.core.model_tool_collection import ToolCollection


class ModelOnexMetadata(BaseModel):
    """
    Canonical ONEX metadata block for validators/tools.
    - tools: ToolCollection (not dict[str, Any])
    - meta_type: MetaTypeEnum (not str)
    - lifecycle: Lifecycle (not str)
    """

    metadata_version: str = Field(
        ...,
        description="Must be a semver string, e.g., '0.1.0'",
    )
    name: str = Field(..., description="Validator/tool name")
    namespace: "Namespace"
    version: str = Field(..., description="Semantic version, e.g., 0.1.0")
    entrypoint: str | None = Field(
        None,
        description="Entrypoint URI string (e.g., python://file.py)",
    )
    protocols_supported: list[str] = Field(
        ...,
        description="List of supported protocols",
    )
    protocol_version: "ProtocolVersionEnum" = Field(
        ...,
        description="Protocol version, e.g., 0.1.0",
    )
    author: str = Field(...)
    owner: str = Field(...)
    copyright: str = Field(...)
    created_at: str = Field(...)
    last_modified_at: str = Field(...)
    description: str | None = Field(
        None,
        description="Optional description of the validator/tool",
    )
    tags: list[str] | None = Field(None, description="Optional list of tags")
    dependencies: list[str] | None = Field(
        None,
        description="Optional list of dependencies",
    )
    config: "ModelMetadataConfig" | None = Field(
        None,
        description="Optional config model",
    )
    meta_type: "MetaTypeEnum" = Field(
        default_factory=lambda: MetaTypeEnum.UNKNOWN,
        description="Meta type of the node/tool",
    )
    runtime_language_hint: "RuntimeLanguageEnum" = Field(
        default_factory=lambda: RuntimeLanguageEnum.UNKNOWN,
        description="Runtime language hint",
    )
    tools: "ToolCollection" | None = None
    lifecycle: "Lifecycle" = Field(default_factory=lambda: Lifecycle.ACTIVE)

    @field_validator("metadata_version")
    @classmethod
    def check_metadata_version(cls, v: str) -> str:
        import re

        from omnibase_core.core.core_error_codes import CoreErrorCode
        from omnibase_core.exceptions import OnexError

        if not re.match(r"^\d+\.\d+\.\d+$", v):
            msg = "metadata_version must be a semver string, e.g., '0.1.0'"
            raise OnexError(
                CoreErrorCode.VALIDATION_ERROR,
                msg,
            )
        return v

    @field_validator("name")
    @classmethod
    def check_name(cls, v: str) -> str:
        import re

        from omnibase_core.core.core_error_codes import CoreErrorCode
        from omnibase_core.exceptions import OnexError

        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", v):
            msg = f"Invalid name: {v}"
            raise OnexError(CoreErrorCode.VALIDATION_ERROR, msg)
        return v

    @field_validator("namespace", mode="before")
    @classmethod
    def check_namespace(cls, v):
        from omnibase_core.models.core.model_node_metadata import Namespace

        if isinstance(v, Namespace):
            return v
        if isinstance(v, str):
            return Namespace(value=v)
        if isinstance(v, dict) and "value" in v:
            return Namespace(**v)
        msg = "Namespace must be a Namespace, str, or dict with 'value'"
        raise ValueError(msg)

    @field_validator("version")
    @classmethod
    def check_version(cls, v: str) -> str:
        import re

        from omnibase_core.core.core_error_codes import CoreErrorCode
        from omnibase_core.exceptions import OnexError

        if not re.match(r"^\d+\.\d+\.\d+$", v):
            msg = f"Invalid version: {v}"
            raise OnexError(CoreErrorCode.VALIDATION_ERROR, msg)
        return v

    @field_validator("protocols_supported", mode="before")
    @classmethod
    def check_protocols_supported(cls, v: list[str] | str) -> list[str]:
        from omnibase_core.core.core_error_codes import CoreErrorCode
        from omnibase_core.exceptions import OnexError

        if isinstance(v, str):
            # Try to parse as list from string
            import ast

            try:
                v = ast.literal_eval(v)
            except Exception:
                msg = f"protocols_supported must be a list, got: {v}"
                raise OnexError(
                    CoreErrorCode.VALIDATION_ERROR,
                    msg,
                )
        if not isinstance(v, list):
            msg = f"protocols_supported must be a list, got: {v}"
            raise OnexError(
                CoreErrorCode.VALIDATION_ERROR,
                msg,
            )
        return v

    @field_validator("entrypoint", mode="before")
    @classmethod
    def validate_entrypoint(cls, v):
        if v is None or v == "":
            return None
        if isinstance(v, str) and "://" in v:
            return v
        msg = f"Entrypoint must be a URI string (e.g., python://file.py), got: {v}"
        raise ValueError(
            msg,
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
    description: str | None = Field(None, description="Description of the file")
    state_contract: str | None = Field(None, description="State contract reference")
    lifecycle: str | None = Field(None, description="Lifecycle state")
    hash: str = Field(..., description="Canonical content hash")
    entrypoint: str | None = Field(None, description="Entrypoint information")
    namespace: str | None = Field(None, description="Namespace for the file")
