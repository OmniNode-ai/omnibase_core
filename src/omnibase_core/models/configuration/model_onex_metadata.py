"""
Pydantic models and validators for OmniNode metadata block schema and validation.
"""

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field, field_validator

from omnibase_core.enums.enum_metadata import (
    EnumLifecycle,
    EnumMetaType,
    EnumRuntimeLanguage,
)
from omnibase_core.models.configuration.model_validators_metadata import (
    coerce_protocols_to_list,
    coerce_to_namespace,
    coerce_to_semver,
    validate_entrypoint_uri,
    validate_identifier_name,
)
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
    tags: list[str] | None = Field(default=None, description="Optional list of tags")
    dependencies: list[str] | None = Field(
        default=None,
        description="Optional list of dependencies",
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
    def check_metadata_version(cls, v: object) -> ModelSemVer:
        """Validate and convert metadata_version to ModelSemVer.

        Args:
            v: Input value (ModelSemVer, dict, or semver string).

        Returns:
            Validated ModelSemVer instance.

        Raises:
            ModelOnexError: If value cannot be converted.
        """
        return coerce_to_semver(v, "metadata_version")

    @field_validator("name")
    @classmethod
    def check_name(cls, v: str) -> str:
        """Validate name follows identifier naming rules."""
        return validate_identifier_name(v)

    @field_validator("namespace", mode="before")
    @classmethod
    def check_namespace(cls, v: object) -> Namespace:
        """Validate and convert namespace to Namespace model."""
        return coerce_to_namespace(v)

    @field_validator("version", mode="before")
    @classmethod
    def check_version(cls, v: object) -> ModelSemVer:
        """Validate and convert version to ModelSemVer.

        Args:
            v: Input value (ModelSemVer, dict, or semver string).

        Returns:
            Validated ModelSemVer instance.

        Raises:
            ModelOnexError: If value cannot be converted.
        """
        return coerce_to_semver(v, "version")

    @field_validator("protocols_supported", mode="before")
    @classmethod
    def check_protocols_supported(cls, v: list[str] | str) -> list[str]:
        """Validate and convert protocols_supported to a list."""
        return coerce_protocols_to_list(v)

    @field_validator("entrypoint", mode="before")
    @classmethod
    def validate_entrypoint(cls, v: object) -> str | None:
        """Validate entrypoint is a valid URI string."""
        return validate_entrypoint_uri(v)
