from typing import Any, List, Optional

from pydantic import Field, field_validator

from omnibase_core.errors.error_codes import ModelOnexError
from omnibase_core.models.core.model_semver import ModelSemVer

"""
MetadataBlock model.
"""

import re
from typing import TYPE_CHECKING, Any, Optional

from pydantic import BaseModel, Field, field_validator

from omnibase_core.enums import EnumMetaType, EnumProtocolVersion, EnumRuntimeLanguage
from omnibase_core.enums.enum_metadata import EnumLifecycle
from omnibase_core.errors import ModelOnexError
from omnibase_core.errors.error_codes import ModelCoreErrorCode
from omnibase_core.models.configuration.model_metadata_config import ModelMetadataConfig
from omnibase_core.models.core.model_tool_collection import ToolCollection

if TYPE_CHECKING:
    from omnibase_core.models.core.model_node_metadata import Namespace


class ModelMetadataBlock(BaseModel):
    """
    Canonical ONEX metadata block for validators/tools.
    - tools: ToolCollection (not dict[str, Any])
    - meta_type: EnumMetaType (not str)
    - lifecycle: EnumLifecycle (not str)
    """

    metadata_version: str = Field(
        default=...,
        description="Must be a semver string, e.g., '0.1.0'",
    )
    name: str = Field(default=..., description="Validator/tool name")
    namespace: "Namespace"
    version: ModelSemVer = Field(
        default=..., description="Semantic version, e.g., 0.1.0"
    )
    entrypoint: str | None = Field(
        default=None,
        description="Entrypoint URI string (e.g., python://file.py)",
    )
    protocols_supported: list[str] = Field(
        default=...,
        description="List of supported protocols",
    )
    protocol_version: EnumProtocolVersion = Field(
        default=...,
        description="Protocol version, e.g., 0.1.0",
    )
    author: str = Field(...)
    owner: str = Field(...)
    copyright: str = Field(...)
    created_at: str = Field(...)
    last_modified_at: str = Field(...)
    description: str | None = Field(
        default=None,
        description="Optional description of the validator/tool",
    )
    tags: list[str] | None = Field(
        default=None, description="Optional list[Any]of tags"
    )
    dependencies: list[str] | None = Field(
        default=None,
        description="Optional list[Any]of dependencies",
    )
    config: ModelMetadataConfig | None = Field(
        default=None,
        description="Optional config model",
    )
    meta_type: EnumMetaType = Field(
        default=EnumMetaType.UNKNOWN,
        description="Meta type of the node/tool",
    )
    runtime_language_hint: EnumRuntimeLanguage = Field(
        default=EnumRuntimeLanguage.UNKNOWN,
        description="Runtime language hint",
    )
    tools: ToolCollection | None = None
    lifecycle: EnumLifecycle = Field(default=EnumLifecycle.ACTIVE)

    @field_validator("metadata_version")
    @classmethod
    def check_metadata_version(cls, v: str) -> str:
        if not re.match("^\\d+\\.\\d+\\.\\d+$", v):
            msg = "metadata_version must be a semver string, e.g., '0.1.0'"
            raise ModelOnexError(
                msg,
                ModelCoreErrorCode.VALIDATION_ERROR,
            )
        return v

    @field_validator("name")
    @classmethod
    def check_name(cls, v: str) -> str:
        if not re.match("^[a-zA-Z_][a-zA-Z0-9_]*$", v):
            msg = f"Invalid name: {v}"
            raise ModelOnexError(msg, ModelCoreErrorCode.VALIDATION_ERROR)
        return v

    @field_validator("namespace", mode="before")
    @classmethod
    def check_namespace(cls, v: Any) -> Any:

        if isinstance(v, Namespace):
            return v
        if isinstance(v, str):
            return Namespace(value=v)
        if isinstance(v, dict) and "value" in v:
            return Namespace(**v)
        msg = "Namespace must be a Namespace, str, or dict[str, Any]with 'value'"
        raise ModelOnexError(msg, ModelCoreErrorCode.VALIDATION_ERROR)

    @field_validator("version")
    @classmethod
    def check_version(cls, v: str) -> str:
        if not re.match("^\\d+\\.\\d+\\.\\d+$", v):
            msg = f"Invalid version: {v}"
            raise ModelOnexError(msg, ModelCoreErrorCode.VALIDATION_ERROR)
        return v

    @field_validator("protocols_supported", mode="before")
    @classmethod
    def check_protocols_supported(cls, v: list[str] | str) -> list[str]:
        if isinstance(v, str):
            import ast

            try:
                v = ast.literal_eval(v)
            except Exception:
                msg = f"protocols_supported must be a list[Any], got: {v}"
                raise ModelOnexError(
                    msg,
                    ModelCoreErrorCode.VALIDATION_ERROR,
                )
        if not isinstance(v, list):
            msg = f"protocols_supported must be a list[Any], got: {v}"
            raise ModelOnexError(
                msg,
                ModelCoreErrorCode.VALIDATION_ERROR,
            )
        return v

    @field_validator("entrypoint", mode="before")
    @classmethod
    def validate_entrypoint(cls, v: Any) -> Any:
        if v is None or v == "":
            return None
        if isinstance(v, str) and "://" in v:
            return v
        msg = f"Entrypoint must be a URI string (e.g., python://file.py), got: {v}"
        raise ModelOnexError(msg, ModelCoreErrorCode.VALIDATION_ERROR)
