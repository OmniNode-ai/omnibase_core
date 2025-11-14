# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# created_at: '2025-05-28T12:36:25.626805'
# description: Stamped by ToolPython
# entrypoint: python://mixin_serializable
# hash: ddef0b544b2580e2cc69c22f978ee2fc7be30307b3cfbf54add9ce862b3ee56e
# last_modified_at: '2025-05-29T14:13:58.705165+00:00'
# lifecycle: active
# meta_type: tool
# metadata_version: 0.1.0
# name: mixin_serializable.py
# namespace: python://omnibase.mixin.mixin_serializable
# owner: OmniNode Team
# protocol_version: 0.1.0
# runtime_language_hint: python>=3.11
# schema_version: 0.1.0
# state_contract: state_contract://default
# tools: null
# uuid: d32ee1eb-7b18-4898-af1d-f92ab0d70206
# version: 1.0.0
# === /OmniNode:Metadata ===


from typing import Any, Protocol, TypeVar

T = TypeVar("T", bound="MixinSerializable")


class MixinSerializable(Protocol):
    """
    Protocol for models that support recursive, protocol-driven serialization for ONEX/OmniNode file/block I/O.
    Implementations must provide:
      - to_serializable_dict(self) -> dict[str, Any]: Recursively serialize self and all sub-models, list[Any]s, dict[str, Any]s, and enums.
      - from_serializable_dict(cls, data: dict[str, Any]) -> Self: Recursively reconstruct the model and all sub-models from dict[str, Any]s.
    This protocol is foundational and should be implemented by any model intended for canonical serialization or deserialization.
    """

    def to_serializable_dict(self: T) -> dict[str, Any]: ...

    @classmethod
    def from_serializable_dict(cls: type[T], data: dict[str, Any]) -> T: ...
