# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# created_at: '2025-05-28T12:36:25.598180'
# description: Stamped by ToolPython
# entrypoint: python://mixin_hash_computation
# hash: 55956312613feafc74c009df65dd054cd0e672c5ad22816af7e4b16eb0a1b0c1
# last_modified_at: '2025-05-29T14:13:58.683349+00:00'
# lifecycle: active
# meta_type: tool
# metadata_version: 0.1.0
# name: mixin_hash_computation.py
# namespace: python://omnibase.mixin.mixin_hash_computation
# owner: OmniNode Team
# protocol_version: 0.1.0
# runtime_language_hint: python>=3.11
# schema_version: 0.1.0
# state_contract: state_contract://default
# tools: null
# uuid: 71d2759f-d20a-438e-89f2-f45cdd20af79
# version: 1.0.0
# === /OmniNode:Metadata ===


import hashlib

from pydantic import BaseModel, Field

from omnibase_core.enums import EnumNodeMetadataField
from omnibase_core.mixins.mixin_canonical_serialization import MixinCanonicalYAMLSerializer


class MixinHashComputation:
    """
    Pure mixin for protocol-compliant hash computation for node metadata blocks.
    - Requires self to be a NodeMetadataBlock (Pydantic model).
    - All field access and normalization is schema-driven using NodeMetadataBlock.model_fields and EnumNodeMetadataField enum.
    - No hardcoded field names or types.
    - Compatible with Pydantic BaseModel inheritance.
    """

    def compute_hash(
        body: str,
        volatile_fields: tuple[EnumNodeMetadataField, ...] = (
            EnumNodeMetadataField.HASH,
            EnumNodeMetadataField.LAST_MODIFIED_AT,
        ),
        placeholder: str = "<PLACEHOLDER>",
        comment_prefix: str = "",
    ) -> str:
        canonical = MixinCanonicalYAMLSerializer().canonicalize_for_hash(
            self,  # type: ignore[arg-type]
            volatile_fields=volatile_fields,
            placeholder=placeholder,
            comment_prefix=comment_prefix,
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
