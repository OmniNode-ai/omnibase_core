# === OmniNode:Metadata ===
# metadata_version: 0.1.0
# protocol_version: 1.1.0
# owner: OmniNode Team
# copyright: OmniNode Team
# schema_version: 1.1.0
# name: metadata_utils.py
# version: 1.0.0
# uuid: c59268b5-88b9-433f-9df5-7e4dc7037691
# author: OmniNode Team
# created_at: 2025-05-22T14:05:21.449308
# last_modified_at: 2025-05-22T20:50:39.712639
# description: Stamped by ToolPython
# state_contract: state_contract://default
# lifecycle: active
# hash: be4418331d4279b7e59df0688a615ec5e912ad9601cafcf173520381ecc226f4
# entrypoint: python@metadata_utils.py
# runtime_language_hint: python>=3.11
# namespace: onex.stamped.metadata_utils
# meta_type: tool
# === /OmniNode:Metadata ===


import hashlib
import uuid
from collections.abc import Callable
from typing import Protocol, TypedDict

from omnibase_core.model.core.model_entrypoint import ModelEntrypointBlock

# yaml import removed - using centralized YAML operations from safe_yaml_loader


class NodeMetadataDict(TypedDict, total=False):
    """Type definition for node metadata dictionary."""

    name: str
    author: str
    namespace: str
    entrypoint: dict[str, str] | str | ModelEntrypointBlock
    metadata_version: str
    protocol_version: str
    owner: str
    copyright: str
    schema_version: str
    version: str
    uuid: str
    created_at: str
    last_modified_at: str
    description: str
    state_contract: str
    lifecycle: str
    hash: str
    runtime_language_hint: str | None


class HasModelDump(Protocol):
    def model_dump(
        self,
        mode: str = "json",
    ) -> dict[str, str | int | float | bool | None]: ...


def generate_uuid() -> str:
    return str(uuid.uuid4())


def compute_canonical_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def canonicalize_for_hash(
    metadata: NodeMetadataDict,
    body: str,
    volatile_fields: list[str] | None = None,
    metadata_serializer: Callable[[HasModelDump], str] | None = None,
    body_canonicalizer: Callable[[str], str] | None = None,
) -> str:
    """
    Canonicalize metadata and body for hash computation.
    - Constructs a complete NodeMetadataBlock model from metadata dict
    - Masks volatile fields in metadata with a constant placeholder.
    - Canonicalizes the body (if a canonicalizer is provided).
    - Serializes metadata (if a serializer is provided).
    Returns the concatenated canonicalized metadata and body as a string.
    """
    from omnibase_core.model.core.model_node_metadata import NodeMetadataBlock

    # Extract key fields from metadata dict, use model defaults for missing fields
    if volatile_fields is None:
        volatile_fields = ["hash", "last_modified_at"]
    name = metadata.get("name", "unknown")
    author = metadata.get("author", "unknown")
    namespace = metadata.get("namespace", "onex.stamped.unknown")

    # Handle entrypoint - create proper ModelEntrypointBlock
    entrypoint_raw = metadata.get("entrypoint", {})
    if isinstance(entrypoint_raw, dict):
        entrypoint_type = entrypoint_raw.get("type", "python")
        entrypoint_target = entrypoint_raw.get("target", "main.py")
    elif isinstance(entrypoint_raw, str) and "@" in entrypoint_raw:
        # Parse string format like "python@filename.py"
        parts = entrypoint_raw.split("@", 1)
        entrypoint_type = parts[0]
        entrypoint_target = parts[1]
    else:
        entrypoint_type = "python"
        entrypoint_target = "main.py"

    # Create complete model using the canonical constructor
    model = NodeMetadataBlock.create_with_defaults(
        name=name,
        author=author,
        namespace=namespace,
        entrypoint_type=entrypoint_type,
        entrypoint_target=entrypoint_target,
        **{
            k: v
            for k, v in metadata.items()
            if k not in ["name", "author", "namespace", "entrypoint"]
        },
    )

    # Now mask volatile fields for hash computation
    model_dict = model.model_dump()
    for field in volatile_fields:
        if field == "hash":
            model_dict[field] = "0" * 64  # Use valid dummy hash
        elif field == "last_modified_at":
            model_dict[field] = "1970-01-01T00:00:00Z"
        else:
            model_dict[field] = None

    # Reconstruct model with masked fields
    meta_for_hash = NodeMetadataBlock(**model_dict)

    meta_str = (
        metadata_serializer(meta_for_hash)
        if metadata_serializer
        else str(meta_for_hash.model_dump())
    )
    body_str = body_canonicalizer(body) if body_canonicalizer else body
    return meta_str + "\n" + body_str


def to_yaml_block(model: HasModelDump, comment_prefix: str = "") -> str:
    """
    Serialize a Pydantic model as YAML, prefixing each line with comment_prefix.
    This replaces the YAMLSerializationMixin.to_yaml_block() method.

    Args:
        model: Pydantic model instance that implements model_dump()
        comment_prefix: String to prefix each line of YAML output

    Returns:
        YAML string with each line prefixed by comment_prefix
    """
    # Use centralized YAML serialization
    from omnibase_core.utils.safe_yaml_loader import serialize_pydantic_model_to_yaml

    return serialize_pydantic_model_to_yaml(
        model,
        comment_prefix=comment_prefix,
        sort_keys=False,
        default_flow_style=False,
        allow_unicode=True,
        indent=2,
        width=120,
    )


def compute_metadata_hash(
    model: HasModelDump,
    body: str,
    volatile_fields: list[str] | None = None,
    placeholder: str = "<PLACEHOLDER>",
    comment_prefix: str = "",
) -> str:
    """
    Compute hash for a metadata model, replacing HashComputationMixin.compute_hash().
    This is specifically for metadata blocks, not general model hashing.

    Args:
        model: Pydantic model instance
        body: Body content to include in hash
        volatile_fields: Fields to mask during hash computation
        placeholder: Placeholder value for volatile fields
        comment_prefix: Comment prefix for YAML serialization

    Returns:
        SHA256 hash of the canonicalized content
    """
    from omnibase_core.mixin.mixin_canonical_serialization import (
        CanonicalYAMLSerializer,
    )

    if volatile_fields is None:
        volatile_fields = ["hash", "last_modified_at"]
    canonical = CanonicalYAMLSerializer().canonicalize_for_hash(
        model,
        body,
        volatile_fields=volatile_fields,
        placeholder=placeholder,
        comment_prefix=comment_prefix,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
