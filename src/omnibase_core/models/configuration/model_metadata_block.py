"""ONEX metadata block model for validators and tools.

This module defines ModelMetadataBlock, the canonical metadata structure
embedded in ONEX node YAML files. It provides standardized fields for
versioning, authorship, dependencies, and protocol compliance.

The metadata block appears at the top of .onex.yaml files and is used by
the runtime for discovery, validation, and documentation generation.

Example:
    Metadata block in YAML::

        metadata:
          name: my_validator
          namespace: omnibase.validators
          version: 1.0.0
          author: ONEX Team
          protocols_supported: ["validator/v1"]

See Also:
    - ModelSemVer: Semantic version model
    - EnumMetaType: Node/tool type enumeration
    - EnumLifecycle: Active/deprecated status
"""

import re

from pydantic import BaseModel, Field, field_validator

from omnibase_core.enums import EnumMetaType, EnumProtocolVersion, EnumRuntimeLanguage
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_metadata import EnumLifecycle
from omnibase_core.models.configuration.model_metadata_config import ModelMetadataConfig
from omnibase_core.models.core.model_node_metadata import Namespace
from omnibase_core.models.core.model_tool_collection import ToolCollection
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import (
    ModelSemVer,
    default_model_version,
    parse_semver_from_string,
)


def _coerce_to_semver(value: object, field_name: str) -> ModelSemVer:
    """
    Common helper to coerce various input types to ModelSemVer.

    Args:
        value: Input value (ModelSemVer, dict, or str)
        field_name: Name of the field for error messages

    Returns:
        ModelSemVer instance

    Raises:
        ModelOnexError: If value cannot be converted to ModelSemVer
    """
    if isinstance(value, ModelSemVer):
        return value
    if isinstance(value, dict):
        return ModelSemVer(**value)
    if isinstance(value, str):
        return parse_semver_from_string(value)
    raise ModelOnexError(
        f"{field_name} must be ModelSemVer, dict, or str, got {type(value).__name__}",
        EnumCoreErrorCode.VALIDATION_ERROR,
    )


class ModelMetadataBlock(BaseModel):
    """Canonical ONEX metadata block for validators and tools.

    This model represents the metadata section of ONEX node definitions.
    All validators, tools, and nodes must include this metadata block
    for proper discovery and protocol compliance.

    Key features:
        - Semantic versioning via ModelSemVer
        - Namespace-based organization
        - Protocol version tracking
        - Lifecycle status (active/deprecated)
        - Tool collection for sub-tools

    Attributes:
        metadata_version: Schema version for the metadata format.
        name: Unique identifier (must match [a-zA-Z_][a-zA-Z0-9_]*).
        namespace: Hierarchical namespace (e.g., "omnibase.validators").
        version: Semantic version of this node/tool.
        entrypoint: URI to the implementation (e.g., "python://file.py").
        protocols_supported: List of protocol identifiers supported.
        protocol_version: Version of the ONEX protocol used.
        author: Creator attribution.
        owner: Current maintainer.
        copyright: Copyright notice.
        created_at: ISO timestamp of creation.
        last_modified_at: ISO timestamp of last modification.
        description: Human-readable description.
        tags: Searchable tags for discovery.
        dependencies: Required dependencies.
        config: Optional configuration model.
        meta_type: Type classification (validator, tool, etc.).
        runtime_language_hint: Suggested runtime language.
        tools: Collection of sub-tools (ToolCollection, not dict).
        lifecycle: Active or deprecated status (EnumLifecycle, not str).

    Example:
        Creating metadata::

            metadata = ModelMetadataBlock(
                name="yaml_validator",
                namespace=Namespace(value="omnibase.validators"),
                version=ModelSemVer(major=1, minor=0, patch=0),
                protocols_supported=["validator/v1"],
                protocol_version=EnumProtocolVersion.V1,
                author="ONEX Team",
                owner="ONEX Team",
                copyright="2024 ONEX",
                created_at="2024-01-01T00:00:00Z",
                last_modified_at="2024-01-01T00:00:00Z"
            )
    """

    metadata_version: ModelSemVer = Field(
        default_factory=default_model_version,
        description="Semantic version, e.g., 0.1.0",
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
    tags: list[str] | None = Field(default=None, description="Optional list of tags")
    dependencies: list[str] | None = Field(
        default=None,
        description="Optional list of dependencies",
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
        return _coerce_to_semver(v, "metadata_version")

    @field_validator("name")
    @classmethod
    def check_name(cls, v: str) -> str:
        """Validate name follows identifier naming rules.

        Names must start with a letter or underscore, followed by
        letters, numbers, or underscores (Python identifier rules).

        Args:
            v: Name string to validate.

        Returns:
            Validated name string.

        Raises:
            ModelOnexError: If name contains invalid characters.
        """
        if not re.match("^[a-zA-Z_][a-zA-Z0-9_]*$", v):
            msg = f"Invalid name: {v}"
            raise ModelOnexError(msg, EnumCoreErrorCode.VALIDATION_ERROR)
        return v

    @field_validator("namespace", mode="before")
    @classmethod
    def check_namespace(cls, v: object) -> Namespace:
        """Validate and convert namespace to Namespace model.

        Accepts Namespace instances, strings (converted to Namespace),
        or dicts with a 'value' key.

        Args:
            v: Input value to validate and convert.

        Returns:
            Validated Namespace instance.

        Raises:
            ModelOnexError: If value cannot be converted to Namespace.
        """
        if isinstance(v, Namespace):
            return v
        if isinstance(v, str):
            return Namespace(value=v)
        if isinstance(v, dict) and "value" in v:
            return Namespace(**v)
        msg = "Namespace must be a Namespace, str, or dict with 'value'"
        raise ModelOnexError(msg, EnumCoreErrorCode.VALIDATION_ERROR)

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
        return _coerce_to_semver(v, "version")

    @field_validator("protocols_supported", mode="before")
    @classmethod
    def check_protocols_supported(cls, v: list[str] | str) -> list[str]:
        """Validate and convert protocols_supported to a list.

        Accepts a list of strings directly, or a string representation
        of a list (parsed via ast.literal_eval).

        Args:
            v: List of protocol strings or string representation.

        Returns:
            List of protocol identifier strings.

        Raises:
            ModelOnexError: If value cannot be converted to a list.
        """
        if isinstance(v, str):
            import ast

            try:
                v = ast.literal_eval(v)
            except (ValueError, SyntaxError):
                # ast.literal_eval raises ValueError for malformed expressions
                # and SyntaxError for invalid Python syntax
                msg = f"protocols_supported must be a list, got: {v}"
                raise ModelOnexError(
                    msg,
                    EnumCoreErrorCode.VALIDATION_ERROR,
                )
        if not isinstance(v, list):
            msg = f"protocols_supported must be a list, got: {v}"
            raise ModelOnexError(
                msg,
                EnumCoreErrorCode.VALIDATION_ERROR,
            )
        return v

    @field_validator("entrypoint", mode="before")
    @classmethod
    def validate_entrypoint(cls, v: object) -> str | None:
        """Validate entrypoint is a valid URI string.

        Entrypoints must contain "://" to be valid (e.g., "python://file.py",
        "shell://script.sh"). Empty strings and None are allowed.

        Args:
            v: Entrypoint URI string or None.

        Returns:
            Validated entrypoint string or None.

        Raises:
            ModelOnexError: If string is not a valid URI format.
        """
        if v is None or v == "":
            return None
        if isinstance(v, str) and "://" in v:
            return v
        msg = f"Entrypoint must be a URI string (e.g., python://file.py), got: {v}"
        raise ModelOnexError(msg, EnumCoreErrorCode.VALIDATION_ERROR)
