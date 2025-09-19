"""
Metadata enumeration definitions for ONEX architecture.

Defines core metadata enums used throughout the ONEX system.
"""

from enum import Enum


class Lifecycle(str, Enum):
    """Lifecycle stages for ONEX components."""

    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


class EnumEntrypointType(str, Enum):
    """Supported entrypoint types for ONEX components."""

    PYTHON = "python"
    CLI = "cli"
    DOCKER = "docker"
    MARKDOWN = "markdown"
    YAML = "yaml"
    JSON = "json"
    TYPESCRIPT = "typescript"
    JAVASCRIPT = "javascript"
    HTML = "html"


class EnumMetaType(str, Enum):
    """Component meta types in ONEX architecture."""

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


class EnumProtocolVersion(str, Enum):
    """Supported protocol versions."""

    V0_1_0 = "0.1.0"
    V1_0_0 = "1.0.0"


class EnumRuntimeLanguage(str, Enum):
    """Supported runtime languages."""

    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    RUST = "rust"
    GO = "go"
    UNKNOWN = "unknown"


class EnumFunctionLanguage(str, Enum):
    """Enum for supported function discovery languages."""

    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    BASH = "bash"
    SHELL = "shell"
    YAML = "yaml"
    JSON = "json"


class NodeMetadataField(Enum):
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
    CONTRACTS = "contracts"
    SCENARIOS = "scenarios"
    SCENARIO_TEST_ENTRYPOINT = "scenario_test_entrypoint"
    TEST_MATRIX = "test_matrix"
    TEST_COVERAGE = "test_coverage"
    NODES = "nodes"

    @classmethod
    def volatile(cls) -> list["NodeMetadataField"]:
        """Return list of volatile fields that change frequently."""
        return [
            cls.LAST_MODIFIED_AT,
            cls.HASH,
            cls.TEST_COVERAGE,
        ]

    @classmethod
    def required(cls) -> list["NodeMetadataField"]:
        """Return list of fields required by ONEX protocol."""
        return [
            cls.METADATA_VERSION,
            cls.PROTOCOL_VERSION,
            cls.SCHEMA_VERSION,
            cls.NAME,
            cls.UUID,
            cls.AUTHOR,
            cls.CREATED_AT,
            cls.ENTRYPOINT,
            cls.NAMESPACE,
            cls.HASH,
        ]
