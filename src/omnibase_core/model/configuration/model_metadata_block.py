"""
MetadataBlock model.
"""

import re
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field, field_validator

from omnibase_core.core.core_error_codes import CoreErrorCode
from omnibase_core.enums import MetaTypeEnum, ProtocolVersionEnum, RuntimeLanguageEnum
from omnibase_core.enums.enum_metadata import Lifecycle
from omnibase_core.exceptions import OnexError
from omnibase_core.model.configuration.model_metadata_config import ModelMetadataConfig
from omnibase_core.model.core.model_tool_collection import ToolCollection

if TYPE_CHECKING:
    from omnibase_core.model.core.model_node_metadata import Namespace


class ModelMetadataBlock(BaseModel):
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
    protocol_version: ProtocolVersionEnum = Field(
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
    config: ModelMetadataConfig | None = Field(
        None,
        description="Optional config model",
    )
    meta_type: MetaTypeEnum = Field(
        default=MetaTypeEnum.UNKNOWN,
        description="Meta type of the node/tool",
    )
    runtime_language_hint: RuntimeLanguageEnum = Field(
        RuntimeLanguageEnum.UNKNOWN,
        description="Runtime language hint",
    )
    tools: ToolCollection | None = None
    lifecycle: Lifecycle = Field(default=Lifecycle.ACTIVE)

    @field_validator("metadata_version")
    @classmethod
    def check_metadata_version(cls, v: str) -> str:
        if not re.match("^\\d+\\.\\d+\\.\\d+$", v):
            msg = "metadata_version must be a semver string, e.g., '0.1.0'"
            raise OnexError(
                msg,
                CoreErrorCode.VALIDATION_ERROR,
            )
        return v

    @field_validator("name")
    @classmethod
    def check_name(cls, v: str) -> str:
        if not re.match("^[a-zA-Z_][a-zA-Z0-9_]*$", v):
            msg = f"Invalid name: {v}"
            raise OnexError(msg, CoreErrorCode.VALIDATION_ERROR)
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
        msg = "Namespace must be a Namespace, str, or dict with 'value'"
        raise ValueError(msg)

    @field_validator("version")
    @classmethod
    def check_version(cls, v: str) -> str:
        if not re.match("^\\d+\\.\\d+\\.\\d+$", v):
            msg = f"Invalid version: {v}"
            raise OnexError(msg, CoreErrorCode.VALIDATION_ERROR)
        return v

    @field_validator("protocols_supported", mode="before")
    @classmethod
    def check_protocols_supported(cls, v: list[str] | str) -> list[str]:
        if isinstance(v, str):
            import ast

            try:
                v = ast.literal_eval(v)
            except Exception:
                msg = f"protocols_supported must be a list, got: {v}"
                raise OnexError(
                    msg,
                    CoreErrorCode.VALIDATION_ERROR,
                )
        if not isinstance(v, list):
            msg = f"protocols_supported must be a list, got: {v}"
            raise OnexError(
                msg,
                CoreErrorCode.VALIDATION_ERROR,
            )
        return v

    @field_validator("entrypoint", mode="before")
    def validate_entrypoint(self, v):
        if v is None or v == "":
            return None
        if isinstance(v, str) and "://" in v:
            return v
        msg = f"Entrypoint must be a URI string (e.g., python://file.py), got: {v}"
        raise ValueError(
            msg,
        )
