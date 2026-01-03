"""
Node metadata models.

This module now imports from separated model files for better organization
and compliance with one-model-per-file naming conventions.

The `metadata_version` field is the single source of versioning for both schema and canonicalization logic.
Any change to the schema (fields, types, required/optional status) OR to the canonicalization logic (how the body or metadata is normalized for hashing/idempotency)
MUST increment `metadata_version`. This ensures hashes and idempotency logic remain valid and comparable across versions.

If you change how the hash is computed, how fields are normalized, or the structure of the metadata block, bump `metadata_version`.

This policy is enforced for all ONEX metadata blocks.
"""

from pathlib import Path

from pydantic import BaseModel

from omnibase_core.enums.enum_data_classification import EnumDataClassification
from omnibase_core.enums.enum_metadata import (
    EnumEntrypointType,
    EnumLifecycle,
    EnumMetaType,
)
from omnibase_core.models.core.model_dependency_block import ModelDependencyBlock
from omnibase_core.models.core.model_io_block import ModelIOBlock
from omnibase_core.models.core.model_io_contract import ModelIOContract
from omnibase_core.models.core.model_signature_block import ModelSignatureBlock
from omnibase_core.models.core.model_trust_score_stub import ModelTrustScoreStub
from omnibase_core.models.examples.model_data_handling_declaration import (
    ModelDataHandlingDeclaration,
)

from .model_extension_value import ModelExtensionValue
from .model_logging_config import EnumLogFormat, ModelLoggingConfig
from .model_namespace import ModelNamespace
from .model_node_metadata_block import ModelNodeMetadataBlock

# Import separated models
from .model_signature_contract import ModelSignatureContract
from .model_source_repository import ModelSourceRepository
from .model_state_contract_block import ModelStateContractBlock
from .model_test_matrix_entry import ModelTestMatrixEntry
from .model_testing_block import ModelTestingBlock

# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# created_at: '2025-05-28T08:19:40.214329'
# description: Stamped by ToolPython
# entrypoint: python://model_node_metadata
# hash: c3b5781a99c5e5c292687d7d048e46ec8bf0c5f699a664327a33bb6f39867612
# last_modified_at: '2025-05-29T14:13:58.833046+00:00'
# lifecycle: active
# meta_type: tool
# metadata_version: 0.1.0
# name: model_node_metadata.py
# namespace: python://omnibase.model.model_node_metadata
# owner: OmniNode Team
# protocol_version: 0.1.0
# runtime_language_hint: python>=3.11
# schema_version: 0.1.0
# state_contract: state_contract://default
# tools: null
# uuid: e2fc1037-9f90-45d2-a14b-be759abddd39
# version: 1.0.0
# === /OmniNode:Metadata ===


# Component identifier for logging
_COMPONENT_NAME = Path(__file__).stem

# Import extracted enums
from omnibase_core.enums.enum_architecture import EnumArchitecture

# DataClassification moved to omnibase.enums.enum_data_classification
DataClassification = EnumDataClassification

# Compatibility aliases for enums
Architecture = EnumArchitecture
LogFormat = EnumLogFormat

# Compatibility aliases - existing models
IOBlock = ModelIOBlock
IOContract = ModelIOContract
TrustScoreStub = ModelTrustScoreStub
DependencyBlock = ModelDependencyBlock
SignatureBlock = ModelSignatureBlock

# Compatibility aliases - separated models
SignatureContract = ModelSignatureContract
StateContractBlock = ModelStateContractBlock
LoggingConfig = ModelLoggingConfig
SourceRepository = ModelSourceRepository
TestingBlock = ModelTestingBlock
Namespace = ModelNamespace
DataHandlingDeclaration = ModelDataHandlingDeclaration
ExtensionValueModel = ModelExtensionValue
TestMatrixEntry = ModelTestMatrixEntry
NodeMetadataBlock = ModelNodeMetadataBlock

# NOTE: The only difference between model_dump() and __dict__ is that model_dump() serializes entrypoint as a dict[str, Any], while __dict__ keeps it as an EntrypointBlock object. This is expected and not a source of non-determinism for YAML serialization, which uses model_dump or to_serializable_dict.


def debug_compare_model_dump_vs_dict(model: BaseModel) -> list[str]:
    import difflib
    import pprint

    dump = model.model_dump()
    dct = {k: v for k, v in model.__dict__.items() if not k.startswith("_")}
    dump_str = pprint.pformat(dump, width=120, sort_dicts=True)
    dict_str = pprint.pformat(dct, width=120, sort_dicts=True)
    return list(
        difflib.unified_diff(
            dump_str.splitlines(),
            dict_str.splitlines(),
            fromfile="model_dump()",
            tofile="__dict__",
            lineterm="",
        ),
    )


# --- Pydantic forward reference for ModelExtractedBlock ---
# Removed runtime import to break circular dependency.
# ModelExtractedBlock properly uses TYPE_CHECKING for forward references.

# Import the core ModelNodeMetadata that other systems expect
from .model_node_metadata_core import ModelNodeMetadata

# Re-export for current standards
__all__ = [
    "EnumEntrypointType",
    "EnumLifecycle",
    "EnumMetaType",
    "ModelDataHandlingDeclaration",
    "ModelExtensionValue",
    "ModelLoggingConfig",
    "ModelNamespace",
    "ModelNodeMetadata",
    "ModelNodeMetadataBlock",
    "ModelSourceRepository",
    "ModelStateContractBlock",
    "ModelTestMatrixEntry",
    "ModelTestingBlock",
]
