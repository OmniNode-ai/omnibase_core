from __future__ import annotations

# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# created_at: '2025-05-28T12:36:25.636489'
# description: Stamped by ToolPython
# entrypoint: python://mixin_utils
# hash: 754bf02714142d24f696f9c946046f3d0df3785c88c1dff79d5afcc85736fcd4
# last_modified_at: '2025-05-29T14:13:58.712083+00:00'
# lifecycle: active
# meta_type: tool
# metadata_version: 0.1.0
# name: mixin_utils.py
# namespace: python://omnibase.mixin.mixin_utils
# owner: OmniNode Team
# protocol_version: 0.1.0
# runtime_language_hint: python>=3.11
# schema_version: 0.1.0
# state_contract: state_contract://default
# tools: null
# uuid: 1c1a1699-5733-4aff-b383-eb4b5fc2aea1
# version: 1.0.0
# === /OmniNode:Metadata ===
from typing import TYPE_CHECKING

from omnibase_core.enums import EnumNodeMetadataField
from omnibase_core.protocols.base.protocol_context_value import ContextValue

from .mixin_canonical_serialization import MixinCanonicalYAMLSerializer

if TYPE_CHECKING:
    from omnibase_core.models.core.model_node_metadata import NodeMetadataBlock


def canonicalize_metadata_block(
    block: dict[str, object] | NodeMetadataBlock,
    volatile_fields: tuple[EnumNodeMetadataField, ...] = (
        EnumNodeMetadataField.HASH,
        EnumNodeMetadataField.LAST_MODIFIED_AT,
    ),
    placeholder: str = "<PLACEHOLDER>",
    sort_keys: bool = True,
    explicit_start: bool = True,
    explicit_end: bool = True,
    default_flow_style: bool = False,
    allow_unicode: bool = True,
    comment_prefix: str = "",
    **kwargs: ContextValue,
) -> str:
    """
    Utility function to canonicalize a metadata block using MixinCanonicalYAMLSerializer.
    Args:
        block: A dict[str, object] or model instance (must implement model_dump(mode="json")).
        volatile_fields: Fields to replace with protocol placeholder values.
        placeholder: Placeholder value for volatile fields.
        sort_keys: Whether to sort keys in YAML output.
        explicit_start: Whether to include '---' at the start of YAML.
        explicit_end: Whether to include '...' at the end of YAML.
        default_flow_style: Use block style YAML.
        allow_unicode: Allow unicode in YAML output.
        comment_prefix: Prefix to add to each line (for comment blocks).
        **kwargs: Additional keyword arguments for MixinCanonicalYAMLSerializer.canonicalize_metadata_block.
    Returns:
        Canonical YAML string for the metadata block.
    """
    return str(
        MixinCanonicalYAMLSerializer().canonicalize_metadata_block(
            metadata_block=block,
            volatile_fields=volatile_fields,
            placeholder=placeholder,
            sort_keys=sort_keys,
            explicit_start=explicit_start,
            explicit_end=explicit_end,
            default_flow_style=default_flow_style,
            allow_unicode=allow_unicode,
            comment_prefix=comment_prefix,
            **kwargs,
        ),
    )
