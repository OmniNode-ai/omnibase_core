from enum import Enum
from typing import List


class NodeMetadataField(str, Enum):
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
    TOOLS = "tools"

    @classmethod
    def required(cls) -> List["NodeMetadataField"]:
        return [
            cls.METADATA_VERSION,
            cls.PROTOCOL_VERSION,
            cls.OWNER,
            cls.COPYRIGHT,
            cls.SCHEMA_VERSION,
            cls.NAME,
            cls.VERSION,
            cls.UUID,
            cls.AUTHOR,
            cls.CREATED_AT,
            cls.LAST_MODIFIED_AT,
            cls.HASH,
            cls.ENTRYPOINT,
            cls.NAMESPACE,
            cls.META_TYPE,
        ]

    @classmethod
    def optional(cls) -> List["NodeMetadataField"]:
        return [
            cls.DESCRIPTION,
            cls.STATE_CONTRACT,
            cls.LIFECYCLE,
            cls.RUNTIME_LANGUAGE_HINT,
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
