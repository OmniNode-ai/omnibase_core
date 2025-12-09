"""
Pydantic models and validators for OmniNode metadata block schema and validation.
"""

import re
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field, field_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_metadata import (
    EnumLifecycle,
    EnumMetaType,
    EnumRuntimeLanguage,
)
from omnibase_core.errors import ModelOnexError
from omnibase_core.models.core.model_node_metadata import Namespace
from omnibase_core.models.primitives.model_semver import (
    ModelSemVer,
    default_model_version,
)

if TYPE_CHECKING:
    from omnibase_core.enums import EnumProtocolVersion
    from omnibase_core.models.configuration.model_metadata_config import (
        ModelMetadataConfig,
    )
    from omnibase_core.models.core.model_tool_collection import ToolCollection


class ModelOnexMetadata(BaseModel):
    """
    Canonical ONEX metadata block for validators/tools.
    - tools: ToolCollection (not dict[str, Any])
    - meta_type: EnumMetaType (not str)
    - lifecycle: EnumLifecycle (not str)
    """

    metadata_version: ModelSemVer = Field(
        default_factory=default_model_version,
        description="Must be a semver string, e.g., '0.1.0'",
    )
    name: str = Field(default=..., description="Validator/tool name")
    namespace: "Namespace"
    version: ModelSemVer = Field(
        default_factory=default_model_version,
        description="Semantic version, e.g., 0.1.0",
    )
    entrypoint: str | None = Field(
        default=None,
        description="Entrypoint URI string (e.g., python://file.py)",
    )
    protocols_supported: list[str] = Field(
        default=...,
        description="List of supported protocols",
    )
    protocol_version: "EnumProtocolVersion" = Field(
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
    config: "ModelMetadataConfig | None" = Field(
        default=None,
        description="Optional config model",
    )
    meta_type: "EnumMetaType" = Field(
        default_factory=lambda: EnumMetaType.UNKNOWN,
        description="Meta type of the node/tool",
    )
    runtime_language_hint: "EnumRuntimeLanguage" = Field(
        default_factory=lambda: EnumRuntimeLanguage.UNKNOWN,
        description="Runtime language hint",
    )
    tools: "ToolCollection | None" = None
    lifecycle: "EnumLifecycle" = Field(default_factory=lambda: EnumLifecycle.ACTIVE)

    @field_validator("metadata_version", mode="before")
    @classmethod
    def check_metadata_version(cls, v: Any) -> ModelSemVer:
        """Validate metadata_version and convert to ModelSemVer.

        Args:
            v: Version as ModelSemVer or string (runtime validation)

        Returns:
            ModelSemVer instance

        Raises:
            ModelOnexError: If version format is invalid (VALIDATION_ERROR)
        """
        # If already ModelSemVer, return as-is
        if isinstance(v, ModelSemVer):
            return v

        # Validate string format
        if not isinstance(v, str):
            msg = "metadata_version must be a semver string or ModelSemVer"
            raise ModelOnexError(
                EnumCoreErrorCode.VALIDATION_ERROR,
                msg,
            )

        if not re.match(r"^\d+\.\d+\.\d+$", v):
            msg = "metadata_version must be a semver string, e.g., '0.1.0'"
            raise ModelOnexError(
                EnumCoreErrorCode.VALIDATION_ERROR,
                msg,
            )

        # Parse and return as ModelSemVer
        parts = v.split(".")
        return ModelSemVer(
            major=int(parts[0]), minor=int(parts[1]), patch=int(parts[2])
        )

    @field_validator("name")
    @classmethod
    def check_name(cls, v: str) -> str:
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", v):
            msg = f"Invalid name: {v}"
            raise ModelOnexError(EnumCoreErrorCode.VALIDATION_ERROR, msg)
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
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=msg,
        )

    @field_validator("version", mode="before")
    @classmethod
    def check_version(cls, v: Any) -> ModelSemVer:
        """Validate version and convert to ModelSemVer.

        Args:
            v: Version as ModelSemVer or string (runtime validation)

        Returns:
            ModelSemVer instance

        Raises:
            ModelOnexError: If version format is invalid (VALIDATION_ERROR)
        """
        # If already ModelSemVer, return as-is
        if isinstance(v, ModelSemVer):
            return v

        # Validate string format
        if not isinstance(v, str):
            msg = f"Invalid version type: {type(v).__name__}; expected semver string or ModelSemVer"
            raise ModelOnexError(EnumCoreErrorCode.VALIDATION_ERROR, msg)

        if not re.match(r"^\d+\.\d+\.\d+$", v):
            msg = f"Invalid version format: {v}; expected semver string, e.g., '0.1.0'"
            raise ModelOnexError(EnumCoreErrorCode.VALIDATION_ERROR, msg)

        # Parse and return as ModelSemVer
        parts = v.split(".")
        return ModelSemVer(
            major=int(parts[0]), minor=int(parts[1]), patch=int(parts[2])
        )

    @field_validator("protocols_supported", mode="before")
    @classmethod
    def check_protocols_supported(cls, v: list[str] | str) -> list[str]:
        if isinstance(v, str):
            # Try to parse as list[Any]from string
            import ast

            try:
                v = ast.literal_eval(v)
            except Exception:
                msg = f"protocols_supported must be a list[Any], got: {v}"
                raise ModelOnexError(
                    EnumCoreErrorCode.VALIDATION_ERROR,
                    msg,
                )
        if not isinstance(v, list):
            msg = f"protocols_supported must be a list[Any], got: {v}"
            raise ModelOnexError(
                EnumCoreErrorCode.VALIDATION_ERROR,
                msg,
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
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=msg,
        )
