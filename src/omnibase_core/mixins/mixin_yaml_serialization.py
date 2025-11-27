# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# created_at: '2025-05-28T12:36:25.646053'
# description: Stamped by ToolPython
# entrypoint: python://mixin_yaml_serialization
# hash: 457b8a45554c3ba96648b4b3c09bb3f8665b5959c64bf3e7ff87d7a59554da9f
# last_modified_at: '2025-05-29T14:13:58.719141+00:00'
# lifecycle: active
# meta_type: tool
# metadata_version: 0.1.0
# name: mixin_yaml_serialization.py
# namespace: python://omnibase.mixin.mixin_yaml_serialization
# owner: OmniNode Team
# protocol_version: 0.1.0
# runtime_language_hint: python>=3.11
# schema_version: 0.1.0
# state_contract: state_contract://default
# tools: null
# uuid: af94dddd-cf94-4d45-9368-2c90c7804ad3
# version: 1.0.0
# === /OmniNode:Metadata ===


from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .protocol_has_model_dump import HasModelDump


class MixinYAMLSerialization:
    """
    Pure mixin for protocol-compliant YAML serialization with comment prefixing.
    - Requires self to implement model_dump(mode="json") (e.g., Pydantic BaseModel).
    - No Protocol, no generics, no metaclass.
    - Compatible with Pydantic BaseModel inheritance.
    """

    def to_yaml_block(self: "HasModelDump", comment_prefix: str) -> str:
        """
        Serialize the model as YAML, prefixing each line with comment_prefix.
        Ensures all Enums are serialized as their .value (mode='json').
        Uses the centralized YAML serialization to maintain security standards.

        Args:
            comment_prefix: String to prefix each line of YAML output.
        Returns:
            YAML string with each line prefixed by comment_prefix.
        """
        # Lazy import to avoid circular dependency
        from omnibase_core.utils.util_safe_yaml_loader import (
            serialize_pydantic_model_to_yaml,
        )

        # Delegate to centralized serialization function
        return serialize_pydantic_model_to_yaml(
            self,
            comment_prefix=comment_prefix,
            sort_keys=False,
            default_flow_style=False,
            allow_unicode=True,
            indent=2,
            width=120,
        )
