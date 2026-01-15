from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper

# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# created_at: '2025-05-28T13:24:07.782697'
# description: Stamped by ToolPython
# entrypoint: python://metadata
# hash: 9715b8bf1ead1c46bd4bd3dfdb9cf4617e59f2058ed3f292f4d714ff8a014d91
# last_modified_at: '2025-05-29T14:13:58.557475+00:00'
# lifecycle: active
# meta_type: tool
# metadata_version: 0.1.0
# name: metadata.py
# namespace: python://omnibase.enums.metadata
# owner: OmniNode Team
# protocol_version: 0.1.0
# runtime_language_hint: python>=3.11
# schema_version: 0.1.0
# state_contract: state_contract://default
# tools: {}
# uuid: 312fbb93-6b14-4329-8465-25611aad8faf
# version: 1.0.0
# === /OmniNode:Metadata ===


@unique
class EnumLifecycle(StrValueHelper, str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


@unique
class EnumEntrypointType(StrValueHelper, str, Enum):
    PYTHON = "python"
    CLI = "cli"
    DOCKER = "docker"
    MARKDOWN = "markdown"
    YAML = "yaml"
    JSON = "json"
    TYPESCRIPT = "typescript"
    JAVASCRIPT = "javascript"
    HTML = "html"


@unique
class EnumMetaType(StrValueHelper, str, Enum):
    TOOL = "tool"
    VALIDATOR = "validator"
    AGENT = "agent"
    MODEL = "model"
    PLUGIN = "plugin"
    SCHEMA = "schema"
    NODE = "node"
    IGNORE_CONFIG = "ignore_config"
    PROJECT = "project"
    UNKNOWN = "unknown"


@unique
class EnumProtocolVersion(StrValueHelper, str, Enum):
    V0_1_0 = "0.1.0"
    V1_0_0 = "1.0.0"
    # Add more as needed


@unique
class EnumRuntimeLanguage(StrValueHelper, str, Enum):
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    RUST = "rust"
    GO = "go"
    UNKNOWN = "unknown"


@unique
class EnumNodeMetadataField(Enum):
    """
    Canonical Enum for all NodeMetadataBlock field names.
    Used for type-safe field references in tests, plugins, and codegen.
    This Enum must be kept in sync with the NodeMetadataBlock model.
    """

    # Core metadata fields
    METADATA_VERSION = "metadata_version"
    PROTOCOL_VERSION = "protocol_version"
    OWNER = "owner"
    COPYRIGHT = "copyright"
    SCHEMA_VERSION = "schema_version"
    NAME = "name"
    VERSION = "version"
    UUID = "uuid"
    AUTHOR = "author"
    CREATED_AT = "created_at"
    LAST_MODIFIED_AT = "last_modified_at"
    DESCRIPTION = "description"
    STATE_CONTRACT = "state_contract"
    LIFECYCLE = "lifecycle"
    HASH = "hash"
    ENTRYPOINT = "entrypoint"
    RUNTIME_LANGUAGE_HINT = "runtime_language_hint"
    NAMESPACE = "namespace"
    META_TYPE = "meta_type"

    # Optional fields
    TRUST_SCORE = "trust_score"
    TAGS = "tags"
    CAPABILITIES = "capabilities"
    PROTOCOLS_SUPPORTED = "protocols_supported"
    BASE_CLASS = "base_class"
    DEPENDENCIES = "dependencies"
    INPUTS = "inputs"
    OUTPUTS = "outputs"
    ENVIRONMENT = "environment"
    LICENSE = "license"
    SIGNATURE_BLOCK = "signature_block"
    X_EXTENSIONS = "x_extensions"
    TESTING = "testing"
    OS_REQUIREMENTS = "os_requirements"
    ARCHITECTURES = "architectures"
    CONTAINER_IMAGE_REFERENCE = "container_image_reference"
    COMPLIANCE_PROFILES = "compliance_profiles"
    DATA_HANDLING_DECLARATION = "data_handling_declaration"
    LOGGING_CONFIG = "logging_config"
    SOURCE_REPOSITORY = "source_repository"
    TOOLS = "tools"

    @classmethod
    def required(cls) -> list["EnumNodeMetadataField"]:
        """Return list[Any]of required fields based on NodeMetadataBlock model."""
        return [
            cls.NAME,
            cls.UUID,
            cls.AUTHOR,
            cls.CREATED_AT,
            cls.LAST_MODIFIED_AT,
            cls.HASH,
            cls.ENTRYPOINT,
            cls.NAMESPACE,
        ]

    @classmethod
    def optional(cls) -> list["EnumNodeMetadataField"]:
        """Return list[Any]of optional fields with defaults."""
        return [
            cls.METADATA_VERSION,
            cls.PROTOCOL_VERSION,
            cls.OWNER,
            cls.COPYRIGHT,
            cls.SCHEMA_VERSION,
            cls.VERSION,
            cls.DESCRIPTION,
            cls.STATE_CONTRACT,
            cls.LIFECYCLE,
            cls.RUNTIME_LANGUAGE_HINT,
            cls.META_TYPE,
            cls.TRUST_SCORE,
            cls.TAGS,
            cls.CAPABILITIES,
            cls.PROTOCOLS_SUPPORTED,
            cls.BASE_CLASS,
            cls.DEPENDENCIES,
            cls.INPUTS,
            cls.OUTPUTS,
            cls.ENVIRONMENT,
            cls.LICENSE,
            cls.SIGNATURE_BLOCK,
            cls.X_EXTENSIONS,
            cls.TESTING,
            cls.OS_REQUIREMENTS,
            cls.ARCHITECTURES,
            cls.CONTAINER_IMAGE_REFERENCE,
            cls.COMPLIANCE_PROFILES,
            cls.DATA_HANDLING_DECLARATION,
            cls.LOGGING_CONFIG,
            cls.SOURCE_REPOSITORY,
            cls.TOOLS,
        ]

    @classmethod
    def volatile(cls) -> tuple["EnumNodeMetadataField", ...]:
        """
        Return all volatile fields (those that may change on stamping).
        This is the canonical protocol for volatile field handling in ONEX.
        """
        return (cls.HASH, cls.LAST_MODIFIED_AT)


@unique
class EnumUriType(StrValueHelper, str, Enum):
    TOOL = "tool"
    VALIDATOR = "validator"
    AGENT = "agent"
    MODEL = "model"
    PLUGIN = "plugin"
    SCHEMA = "schema"
    NODE = "node"
    IGNORE_CONFIG = "ignore_config"
    UNKNOWN = "unknown"


SCHEMA_REF = "schema_ref"

# Add more as needed


@unique
class EnumToolType(StrValueHelper, str, Enum):
    FUNCTION = "function"
    # Add more tool types as needed (e.g., SCRIPT, PIPELINE, etc.)


@unique
class EnumToolRegistryMode(StrValueHelper, str, Enum):
    REAL = "real"
    MOCK = "mock"


__all__ = ["EnumLifecycle"]
