"""
Node metadata block model.
"""

import enum
from pathlib import Path
from typing import Annotated, ClassVar, Optional

from pydantic import BaseModel, Field, StringConstraints, field_validator

from omnibase_core.enums import Lifecycle, MetaTypeEnum
from omnibase_core.metadata.metadata_constants import get_namespace_prefix

# Removed mixin imports - these violate ONEX architecture where models should be pure data structures
# Hash computation and YAML serialization are now available as utility functions
from omnibase_core.model.core.model_canonicalization_policy import (
    ModelCanonicalizationPolicy,
)
from omnibase_core.model.core.model_dependency_block import ModelDependencyBlock
from omnibase_core.model.core.model_entrypoint import EntrypointBlock
from omnibase_core.model.core.model_function_tool import ModelFunctionTool
from omnibase_core.model.core.model_generic_yaml import ModelGenericYaml
from omnibase_core.model.core.model_io_block import ModelIOBlock
from omnibase_core.model.core.model_project_metadata import get_canonical_versions
from omnibase_core.model.core.model_serializable_dict import ModelSerializableDict
from omnibase_core.model.core.model_signature_block import ModelSignatureBlock
from omnibase_core.model.core.model_tool_collection import ModelToolCollection
from omnibase_core.utils.safe_yaml_loader import (
    load_and_validate_yaml_model,
    load_yaml_content_as_model,
)

from .model_data_handling_declaration import ModelDataHandlingDeclaration
from .model_extension_value import ModelExtensionValue
from .model_logging_config import ModelLoggingConfig
from .model_namespace import ModelNamespace
from .model_signature_contract import ModelSignatureContract
from .model_source_repository import ModelSourceRepository
from .model_state_contract_block import ModelStateContractBlock
from .model_test_matrix_entry import ModelTestMatrixEntry
from .model_testing_block import ModelTestingBlock

# Type aliases for backward compatibility
DependencyBlock = ModelDependencyBlock
IOBlock = ModelIOBlock
SignatureBlock = ModelSignatureBlock
Namespace = ModelNamespace
SignatureContract = ModelSignatureContract
StateContractBlock = ModelStateContractBlock
LoggingConfig = ModelLoggingConfig
SourceRepository = ModelSourceRepository
TestingBlock = ModelTestingBlock
DataHandlingDeclaration = ModelDataHandlingDeclaration
ExtensionValueModel = ModelExtensionValue
TestMatrixEntry = ModelTestMatrixEntry


class ModelNodeMetadataBlock(BaseModel):
    """
    Canonical ONEX node metadata block (see onex_node.yaml and node_contracts.md).
    Entrypoint must be a URI: <type>://<target>
    Example: 'python://main.py', 'cli://script.sh', 'docker://image', 'markdown://log.md'
    """

    metadata_version: Annotated[
        str,
        StringConstraints(min_length=1, pattern=r"^\d+\.\d+\.\d+$"),
    ] = Field(default="0.1.0")
    protocol_version: Annotated[
        str,
        StringConstraints(min_length=1, pattern=r"^\d+\.\d+\.\d+$"),
    ] = Field(default="0.1.0")
    owner: Annotated[str, StringConstraints(min_length=1)] = Field(
        default="OmniNode Team",
    )
    copyright: Annotated[str, StringConstraints(min_length=1)] = Field(
        default="OmniNode Team",
    )
    schema_version: Annotated[
        str,
        StringConstraints(min_length=1, pattern=r"^\d+\.\d+\.\d+$"),
    ] = Field(default="0.1.0")
    name: Annotated[str, StringConstraints(min_length=1)]
    version: Annotated[
        str,
        StringConstraints(min_length=1, pattern=r"^\d+\.\d+\.\d+$"),
    ] = Field(default="0.1.0")
    uuid: Annotated[
        str,
        StringConstraints(
            pattern=r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$",
        ),
    ]
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
    lifecycle: Lifecycle = Field(default=Lifecycle.ACTIVE)
    hash: Annotated[
        str,
        StringConstraints(min_length=1, pattern=r"^[a-fA-F0-9]{64}$"),
    ] = Field(json_schema_extra={"volatile": True})
    entrypoint: EntrypointBlock
    runtime_language_hint: str | None = None
    namespace: Namespace = Field(
        ...,
        description="Namespace, e.g., <prefix>.tools.<name>",
    )
    meta_type: MetaTypeEnum = Field(default=MetaTypeEnum.TOOL)
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
        description="Function tools within this file (unified tools approach). This is a ModelToolCollection, not a dict.",
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

    model_config = {"arbitrary_types_allowed": True}

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

    def __init__(self, **data):
        super().__init__(**data)

    @classmethod
    def from_file_or_content(
        cls,
        content: str,
        already_extracted_block: str | None = None,
        event_bus=None,
    ) -> "ModelNodeMetadataBlock":
        block_yaml = already_extracted_block or content
        # Load and validate YAML using Pydantic model

        yaml_model = load_yaml_content_as_model(block_yaml, ModelGenericYaml)

        data = yaml_model.model_dump()
        return cls(**data)

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
        policy = cls.canonicalization_policy
        if isinstance(policy, ModelCanonicalizationPolicy):
            return policy.get_canonicalizer()
        return None

    def some_function(self) -> None:
        # implementation
        pass

    def another_function(self) -> None:
        # implementation
        pass

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
                d[k] = canonical_versions.metadata_version
                continue
            if k == "protocol_version":
                d[k] = canonical_versions.protocol_version
                continue
            if k == "schema_version":
                d[k] = canonical_versions.schema_version
                continue
            v = getattr(self, k)
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
            if k == "namespace" and isinstance(v, Namespace):
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

    @classmethod
    def from_serializable_dict(
        cls: type["ModelNodeMetadataBlock"],
        data: ModelSerializableDict,
    ) -> "ModelNodeMetadataBlock":
        # Convert ModelSerializableDict to regular dict for processing
        data_dict = data.data if isinstance(data, ModelSerializableDict) else data

        # Handle entrypoint deserialization
        if "entrypoint" in data_dict:
            if isinstance(data_dict["entrypoint"], str):
                data_dict["entrypoint"] = EntrypointBlock(
                    type=data_dict["entrypoint"].split("://")[0],
                    target=data_dict["entrypoint"].split("://")[1],
                )
            elif isinstance(data_dict["entrypoint"], dict):
                data_dict["entrypoint"] = EntrypointBlock(**data_dict["entrypoint"])
        # Handle tools deserialization
        if "tools" in data_dict and isinstance(data_dict["tools"], dict):
            tools_dict = {}
            for tool_name, tool_data in data_dict["tools"].items():
                if isinstance(tool_data, dict):
                    tools_dict[tool_name] = ModelFunctionTool.from_serializable_dict(
                        tool_data,
                    )
                else:
                    tools_dict[tool_name] = tool_data
            data_dict["tools"] = ModelToolCollection.from_dict(tools_dict)
        return cls(**data_dict)

    @classmethod
    def create_with_defaults(
        cls,
        name: str | None = None,
        author: str | None = None,
        namespace: Namespace | None = None,
        entrypoint_type: str | None = None,
        entrypoint_target: str | None = None,
        file_path: Optional["Path"] = None,
        runtime_language_hint: str | None = None,
        **additional_fields: str,
    ) -> "ModelNodeMetadataBlock":
        """
        Create a complete NodeMetadataBlock with sensible defaults for all required fields.
        PROTOCOL: entrypoint_type and entrypoint_target must be used as provided, for all file types. entrypoint_target must always be the filename stem (no extension).

        # === CRITICAL INVARIANT: UUID and CREATED_AT IDEMPOTENCY ===
        # These fields MUST be preserved if present (not None) in additional_fields.
        # Regression (May 2025): Logic previously always generated new values, breaking protocol idempotency.
        # See test_stamp_idempotency in test_node.py and standards doc for rationale.
        # DO NOT REMOVE THIS CHECK: All changes here must be justified in PR and reviewed by maintainers.
        """
        from datetime import datetime
        from uuid import uuid4

        now = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
        canonical_versions = get_canonical_versions()
        canonical_namespace = None
        ep_type = entrypoint_type or None
        ep_target = entrypoint_target
        # Infer entrypoint_type from file extension if not provided
        if file_path is not None and not ep_type:
            ext = file_path.suffix.lower().lstrip(".")
            ep_type = Namespace.CANONICAL_SCHEME_MAP.get(ext, ext)
        # Always use the filename stem (no extension) for entrypoint_target
        if file_path is not None and not ep_target:
            ep_target = file_path.stem
        elif ep_target:
            ep_target = Path(ep_target).stem
        else:
            ep_target = "main"
        # Set runtime_language_hint only for code files
        if runtime_language_hint is None:
            code_types = {"python", "typescript", "javascript", "html"}
            if ep_type in code_types:
                runtime_language_hint = (
                    cls.RUNTIME_LANGUAGE_HINT_MAP.get_value(ep_type) or None
                )
            else:
                runtime_language_hint = None
        if file_path is not None:
            canonical_namespace = Namespace.from_path(file_path)
        # Entrypoint construction: always use provided type/target (target is stem)
        entrypoint = EntrypointBlock(type=ep_type, target=ep_target)
        data: dict[str, str] = {
            "name": name or (file_path.stem if file_path is not None else "unknown"),
            "uuid": (
                additional_fields.get("uuid")
                if "uuid" in additional_fields
                and additional_fields.get("uuid") is not None
                else str(uuid4())
            ),
            "author": author or "unknown",
            "created_at": (
                additional_fields.get("created_at")
                if "created_at" in additional_fields
                and additional_fields.get("created_at") is not None
                else now
            ),
            "last_modified_at": now,
            "hash": "0" * 64,
            "entrypoint": entrypoint,
            "namespace": namespace
            or canonical_namespace
            or Namespace(value=f"{get_namespace_prefix()}.unknown"),
            "metadata_version": canonical_versions.metadata_version,
            "protocol_version": canonical_versions.protocol_version,
            "schema_version": canonical_versions.schema_version,
        }
        if runtime_language_hint is not None:
            data["runtime_language_hint"] = runtime_language_hint
        # Convert additional_fields to a mutable dict if needed
        additional_fields_dict = (
            dict(additional_fields)
            if not isinstance(additional_fields, dict)
            else additional_fields
        )

        for vfield in ("metadata_version", "protocol_version", "schema_version"):
            if vfield in additional_fields_dict:
                del additional_fields_dict[vfield]
        # PATCH: Always pass tools if present in additional_fields
        tools = additional_fields_dict.pop("tools", None)
        if tools is not None:
            # Omit tools if empty dict or empty ToolCollection
            if (isinstance(tools, dict) and not tools) or (
                hasattr(tools, "root") and not tools.root
            ):
                tools = None
            else:
                pass
            if tools is not None:
                data["tools"] = tools
        data.update(additional_fields_dict)
        return cls(**data)  # type: ignore[arg-type]

    @field_validator("entrypoint", mode="before")
    @classmethod
    def validate_entrypoint(cls, value):
        if isinstance(value, EntrypointBlock):
            return value
        if isinstance(value, str):
            # Accept URI string and convert to EntrypointBlock
            return EntrypointBlock.from_uri(value)
        msg = "entrypoint must be an EntrypointBlock instance or URI string"
        raise ValueError(msg)

    @field_validator("namespace", mode="before")
    @classmethod
    def validate_namespace_field(cls, value):
        # Recursively flatten any dict or Namespace to a plain string
        def flatten_namespace(val):
            if isinstance(val, Namespace):
                return val.value
            if isinstance(val, str):
                # Normalize scheme if present
                if "://" in val:
                    scheme, rest = val.split("://", 1)
                    scheme = Namespace.normalize_scheme(scheme)
                    return f"{scheme}://{rest}"
                return val
            if isinstance(val, dict) and "value" in val:
                return flatten_namespace(val["value"])
            return str(val)

        return Namespace(value=flatten_namespace(value))

    @field_validator("x_extensions", mode="before")
    @classmethod
    def coerce_x_extensions(cls, v):
        if not isinstance(v, dict):
            return v
        out = {}
        for k, val in v.items():
            if isinstance(val, ExtensionValueModel):
                out[k] = val
            elif isinstance(val, dict):
                out[k] = ExtensionValueModel(**val)
            else:
                out[k] = ExtensionValueModel(value=val)
        return out

    def model_dump(self, *args, **kwargs):
        d = super().model_dump(*args, **kwargs)
        d["entrypoint"] = self.entrypoint.to_uri()
        return d


# Utility: Remove all volatile fields from a dict using NodeMetadataField.volatile()
def strip_volatile_fields_from_dict(d: dict) -> dict:
    from omnibase_core.enums.enum_metadata import NodeMetadataField

    volatile_keys = {f.value for f in NodeMetadataField.volatile()}
    return {k: v for k, v in d.items() if k not in volatile_keys}


# --- EntrypointBlock YAML representer registration ---
# Note: YAML serialization now handled by Pydantic models and safe_yaml_loader
# Direct yaml.add_representer usage violates ONEX security patterns
