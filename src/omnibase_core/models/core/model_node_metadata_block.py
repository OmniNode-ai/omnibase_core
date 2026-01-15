"""
Node metadata block model.
"""

import enum
from typing import Annotated, Any, ClassVar
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from omnibase_core.enums import EnumLifecycle, EnumMetaType
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode

# Removed mixin imports - these violate ONEX architecture where models should be pure data structures
# Hash computation and YAML serialization are now available as utility functions
from omnibase_core.models.core.model_canonicalization_policy import (
    ModelCanonicalizationPolicy,
)
from omnibase_core.models.core.model_dependency_block import ModelDependencyBlock
from omnibase_core.models.core.model_entrypoint import EntrypointBlock
from omnibase_core.models.core.model_io_block import ModelIOBlock
from omnibase_core.models.core.model_project_metadata import get_canonical_versions
from omnibase_core.models.core.model_serializable_dict import ModelSerializableDict
from omnibase_core.models.core.model_signature_block import ModelSignatureBlock
from omnibase_core.models.core.model_tool_collection import ModelToolCollection
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.types import SerializedDict

# Default version constants - overridden at serialization time by get_canonical_versions()
# Using ModelSemVer to avoid hardcoded version strings
_DEFAULT_METADATA_SEMVER = ModelSemVer(major=0, minor=1, patch=0)
_DEFAULT_PROTOCOL_SEMVER = ModelSemVer(major=0, minor=1, patch=0)
_DEFAULT_SCHEMA_SEMVER = ModelSemVer(major=0, minor=1, patch=0)

DEFAULT_METADATA_VERSION = str(_DEFAULT_METADATA_SEMVER)
DEFAULT_PROTOCOL_VERSION = str(_DEFAULT_PROTOCOL_SEMVER)
DEFAULT_SCHEMA_VERSION = str(_DEFAULT_SCHEMA_SEMVER)

from omnibase_core.models.examples.model_data_handling_declaration import (
    ModelDataHandlingDeclaration,
)

from .model_extension_value import ModelExtensionValue
from .model_logging_config import ModelLoggingConfig
from .model_namespace import ModelNamespace
from .model_signature_contract import ModelSignatureContract
from .model_source_repository import ModelSourceRepository
from .model_state_contract_block import ModelStateContractBlock
from .model_test_matrix_entry import ModelTestMatrixEntry
from .model_testing_block import ModelTestingBlock

# Type aliases for current standards - using PEP 695 type statement syntax
type DependencyBlock = ModelDependencyBlock
type IOBlock = ModelIOBlock
type SignatureBlock = ModelSignatureBlock
type Namespace = ModelNamespace
type SignatureContract = ModelSignatureContract
type StateContractBlock = ModelStateContractBlock
type LoggingConfig = ModelLoggingConfig
type SourceRepository = ModelSourceRepository
type TestingBlock = ModelTestingBlock
type DataHandlingDeclaration = ModelDataHandlingDeclaration
type ExtensionValueModel = ModelExtensionValue
type TestMatrixEntry = ModelTestMatrixEntry


class ModelNodeMetadataBlock(BaseModel):
    """
    Canonical ONEX node metadata block (see onex_node.yaml and node_contracts.md).
    Entrypoint must be a URI: <type>://<target>
    Example: 'python://main.py', 'cli://script.sh', 'docker://image', 'markdown://log.md'

    ONEX COMPLIANCE: All factory methods removed. Use direct Pydantic instantiation only.
    """

    uuid: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for this node metadata block",
    )
    metadata_version: Annotated[
        str,
        StringConstraints(min_length=1, pattern=r"^\d+\.\d+\.\d+$"),
    ] = Field(default=DEFAULT_METADATA_VERSION)
    protocol_version: Annotated[
        str,
        StringConstraints(min_length=1, pattern=r"^\d+\.\d+\.\d+$"),
    ] = Field(default=DEFAULT_PROTOCOL_VERSION)
    owner: Annotated[str, StringConstraints(min_length=1)] = Field(
        default="OmniNode Team",
    )
    copyright: Annotated[str, StringConstraints(min_length=1)] = Field(
        default="OmniNode Team",
    )
    schema_version: Annotated[
        str,
        StringConstraints(min_length=1, pattern=r"^\d+\.\d+\.\d+$"),
    ] = Field(default=DEFAULT_SCHEMA_VERSION)
    name: Annotated[str, StringConstraints(min_length=1)]
    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Model version",
    )
    author: Annotated[str, StringConstraints(min_length=1)]
    created_at: Annotated[str, StringConstraints(min_length=1)]
    last_modified_at: Annotated[str, StringConstraints(min_length=1)] = Field(
        json_schema_extra={"volatile": True},
    )
    description: Annotated[str, StringConstraints(min_length=1)] = Field(
        default="Stamped by ONEX",
    )
    state_contract: Annotated[str, StringConstraints(min_length=1)] = Field(
        default="state_contract://default",
    )
    lifecycle: EnumLifecycle = Field(default=EnumLifecycle.ACTIVE)
    hash: Annotated[
        str,
        StringConstraints(min_length=1, pattern=r"^[a-fA-F0-9]{64}$"),
    ] = Field(json_schema_extra={"volatile": True})
    entrypoint: EntrypointBlock
    runtime_language_hint: str | None = None
    namespace: Namespace = Field(
        default=...,
        description="Namespace, e.g., <prefix>.tools.<name>",
    )
    meta_type: EnumMetaType = Field(default=EnumMetaType.TOOL)
    trust_score: float | None = None
    tags: list[str] | None = None
    capabilities: list[str] | None = None
    protocols_supported: list[str] | None = None
    base_class: list[str] | None = None
    dependencies: list[DependencyBlock] | None = None
    inputs: list[IOBlock] | None = None
    outputs: list[IOBlock] | None = None
    environment: list[str] | None = None
    license: str | None = None
    signature_block: SignatureBlock | None = None
    x_extensions: dict[str, ExtensionValueModel] = Field(default_factory=dict)
    testing: TestingBlock | None = None
    os_requirements: list[str] | None = None
    architectures: list[str] | None = None
    container_image_reference: str | None = None
    compliance_profiles: list[str] = Field(default_factory=list)
    data_handling_declaration: DataHandlingDeclaration | None = None
    logging_config: LoggingConfig | None = None
    source_repository: SourceRepository | None = None
    contracts: ModelSerializableDict | None = None
    scenarios: list[str] | None = None
    scenario_test_entrypoint: str | None = Field(
        default=None,
        description="Entrypoint for scenario-based test harness; e.g., 'python -m ...' or CLI command.",
    )
    test_matrix: list[TestMatrixEntry] | None = None
    test_coverage: float | None = None  # Percentage, 0-100

    # Function tools support - unified tools approach
    tools: ModelToolCollection | None = Field(
        default=None,
        description="Function tools within this file (unified tools approach). This is a ModelToolCollection, not a dict[str, Any].",
    )

    RUNTIME_LANGUAGE_HINT_MAP: ClassVar[ModelSerializableDict] = ModelSerializableDict(
        data={
            "python": "python>=3.11",
            "typescript": "typescript>=4.0",
            "javascript": "javascript>=ES2020",
            "html": "html5",
            # Add more as needed
        },
    )

    model_config = ConfigDict(arbitrary_types_allowed=True)

    # Canonicalization/canonicalizer policy (not Pydantic config)
    canonicalization_policy: ClassVar[ModelCanonicalizationPolicy] = (
        ModelCanonicalizationPolicy(
            canonicalize_body=staticmethod(
                lambda body: (
                    __import__(
                        "omnibase.mixin.mixin_canonical_serialization",
                        fromlist=["CanonicalYAMLSerializer"],
                    )
                    .CanonicalYAMLSerializer()
                    .normalize_body(body)
                ),
            ),
        )
    )

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)

    @classmethod
    def get_volatile_fields(cls) -> list[str]:
        model_fields = getattr(cls, "model_fields", {})
        if isinstance(model_fields, dict):
            return [
                name
                for name, field in model_fields.items()
                if getattr(field, "json_schema_extra", None)
                and field.json_schema_extra.get("volatile")
            ]
        return []

    @classmethod
    def get_canonicalizer(cls) -> object | None:
        # canonicalization_policy is always ModelCanonicalizationPolicy from ClassVar
        return cls.canonicalization_policy.get_canonicalizer()

    def to_serializable_dict(
        self,
        use_compact_entrypoint: bool = True,
    ) -> ModelSerializableDict:
        """
        Canonical serialization for ONEX metadata block:
        - Omit all optional fields if their value is '', None, { }, or [] (except protocol-required fields).
        - Always emit canonical values for protocol_version, schema_version, and metadata_version.
        - Never emit empty string or null for any field unless protocol requires it.
        - Entrypoint and namespace are always emitted as single-line URI strings.
        """

        def serialize_value(val: object) -> str:
            if hasattr(val, "to_serializable_dict"):
                return str(val.to_serializable_dict())
            if isinstance(val, enum.Enum):
                return str(val.value)
            if isinstance(val, list):
                return str([serialize_value(v) for v in val])
            if isinstance(val, dict):
                return str({k: serialize_value(v) for k, v in val.items()})
            return str(val)

        canonical_versions = get_canonical_versions()
        PROTOCOL_REQUIRED_FIELDS = {"tools"}

        d = {}
        for k in self.__class__.model_fields:
            if k == "metadata_version":
                d[k] = str(canonical_versions.metadata_version)
                continue
            if k == "protocol_version":
                d[k] = str(canonical_versions.protocol_version)
                continue
            if k == "schema_version":
                d[k] = str(canonical_versions.schema_version)
                continue
            v: object = getattr(self, k)
            # Omit if optional and value is '', None, {}, or [] (unless protocol-required)
            if (
                v == "" or v is None or v in ({}, [])
            ) and k not in PROTOCOL_REQUIRED_FIELDS:
                continue
            # Entrypoint as URI string (always)
            if k == "entrypoint" and isinstance(v, EntrypointBlock):
                d[k] = v.to_uri()
                continue
            # Namespace as URI string (always)
            if k == "namespace" and isinstance(v, ModelNamespace):
                d[k] = str(v)
                continue
            # PATCH: Omit tools if None, empty dict, or empty ToolCollection (protocol rule)
            if k == "tools":
                if v is None:
                    continue
                if isinstance(v, dict) and not v:
                    continue
                if hasattr(v, "root") and not v.root:
                    continue
            d[k] = serialize_value(v)
        # PATCH: Remove all None/null/empty fields after dict construction
        d = {k: v for k, v in d.items() if v not in (None, "", [], {})}
        return ModelSerializableDict(data=d)

    @field_validator("entrypoint", mode="before")
    @classmethod
    def validate_entrypoint(cls, value: Any) -> EntrypointBlock:
        if isinstance(value, EntrypointBlock):
            return value
        if isinstance(value, str):
            # Accept URI string and convert to EntrypointBlock
            return EntrypointBlock.from_uri(value)
        msg = "entrypoint must be an EntrypointBlock instance or URI string"
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=msg,
        )

    @field_validator("namespace", mode="before")
    @classmethod
    def validate_namespace_field(cls, value: Any) -> ModelNamespace:
        # Recursively flatten any dict or Namespace to a plain string
        def flatten_namespace(val: object) -> str:
            if isinstance(val, ModelNamespace):
                return val.value
            if isinstance(val, str):
                # Normalize scheme if present
                if "://" in val:
                    scheme, rest = val.split("://", 1)
                    scheme = ModelNamespace.normalize_scheme(scheme)
                    return f"{scheme}://{rest}"
                return val
            if isinstance(val, dict) and "value" in val:
                return flatten_namespace(val["value"])
            return str(val)

        return ModelNamespace(value=flatten_namespace(value))

    @field_validator("x_extensions", mode="before")
    @classmethod
    def coerce_x_extensions(cls, v: Any) -> dict[str, ModelExtensionValue] | Any:
        if not isinstance(v, dict):
            return v
        out = {}
        for k, val in v.items():
            if isinstance(val, ModelExtensionValue):
                out[k] = val
            elif isinstance(val, dict):
                out[k] = ModelExtensionValue(**val)
            else:
                out[k] = ModelExtensionValue(value=val)
        return out

    def model_dump(self, *args: Any, **kwargs: Any) -> SerializedDict:
        d = super().model_dump(*args, **kwargs)
        d["entrypoint"] = self.entrypoint.to_uri()
        return d


# Utility: Remove all volatile fields from a serialized dict using EnumNodeMetadataField.volatile()
def strip_volatile_fields_from_dict(d: SerializedDict) -> SerializedDict:
    from omnibase_core.enums.enum_metadata import EnumNodeMetadataField

    volatile_keys = {f.value for f in EnumNodeMetadataField.volatile()}
    return {k: v for k, v in d.items() if k not in volatile_keys}


# --- EntrypointBlock YAML representer registration ---
# Note: YAML serialization now handled by Pydantic models and safe_yaml_loader
# Direct yaml.add_representer usage violates ONEX security patterns
