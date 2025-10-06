# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# created_at: '2025-05-28T12:36:25.587635'
# description: Stamped by ToolPython
# entrypoint: python://mixin_canonical_serialization
# hash: 0092cccbb29b2fe0ef19859213b695c793aba401551451509b740774762c8d13
# last_modified_at: '2025-05-29T14:13:58.676277+00:00'
# lifecycle: active
# meta_type: tool
# metadata_version: 0.1.0
# name: mixin_canonical_serialization.py
# namespace: python://omnibase.mixin.mixin_canonical_serialization
# owner: OmniNode Team
# protocol_version: 0.1.0
# runtime_language_hint: python>=3.11
# schema_version: 0.1.0
# state_contract: state_contract://default
# tools: null
# uuid: f1f6dff2-153e-4b8a-9afe-9a64becb146f
# version: 1.0.0
# === /OmniNode:Metadata ===


import json
from typing import TYPE_CHECKING, Any, List, Optional, Union

from omnibase_spi.protocols.core import ProtocolCanonicalSerializer
from pydantic import Field

from omnibase_core.enums import EnumNodeMetadataField
from omnibase_core.errors.error_codes import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.core.model_project_metadata import get_canonical_versions

if TYPE_CHECKING:
    from omnibase_core.models.core.model_node_metadata import NodeMetadataBlock


def _strip_comment_prefix(
    block: str,
    comment_prefixes: tuple[str, ...] = ("# ", "#"),
) -> str:
    """
    Remove leading comment prefixes from each line of a block.
    Args:
        block: Multiline string block to process.
        comment_prefixes: Tuple/list[Any]of prefix strings to remove from line starts.
    Returns:
        Block with comment prefixes removed from each line.
    """
    lines = block.splitlines()

    def _strip_line(line: str) -> str:
        for prefix in comment_prefixes:
            if line.lstrip().startswith(prefix):
                # Remove only one prefix per line, after optional leading whitespace
                i = line.find(prefix)
                return line[:i] + line[i + len(prefix) :]
        return line

    return "\n".join(_strip_line(line) for line in lines)


class MixinCanonicalYAMLSerializer(ProtocolCanonicalSerializer):
    """
    Canonical YAML serializer implementing ProtocolCanonicalSerializer.
    Provides protocol-compliant, deterministic serialization and normalization for stamping, hashing, and idempotency.
    All field normalization and placeholder logic is schema-driven, using NodeMetadataBlock.model_fields.
    No hardcoded field names or types.

    NOTE: Field order is always as declared in NodeMetadataBlock.model_fields, never by dict[str, Any]or YAML loader order. This is required for perfect idempotency.

    - All nested collections (list[Any]s of dict[str, Any]s, dict[str, Any]s of dict[str, Any]s) are sorted by a stable key (e.g., 'name' or dict[str, Any]key).
    - All booleans are normalized to lowercase YAML ('true'/'false').
    - All numbers are formatted with consistent precision.
    """

    def canonicalize_metadata_block(
        block: Union[dict[str, object], "NodeMetadataBlock"],
        volatile_fields: tuple[EnumNodeMetadataField, ...] = (
            EnumNodeMetadataField.HASH,
            EnumNodeMetadataField.LAST_MODIFIED_AT,
        ),
        placeholder: str = "<PLACEHOLDER>",
        sort_keys: bool = False,
        explicit_start: bool = True,
        explicit_end: bool = True,
        default_flow_style: bool = False,
        allow_unicode: bool = True,
        comment_prefix: str = "",
        **kwargs: object,
    ) -> str:
        """
        Canonicalize a metadata block for deterministic YAML serialization and hash computation.
        Args:
            block: A dict[str, Any]or NodeMetadataBlock instance (must implement model_dump(mode="json")).
            volatile_fields: Fields to replace with protocol placeholder values.
            placeholder: Placeholder value for volatile fields.
            sort_keys: Whether to sort keys in YAML output.
            explicit_start: Whether to include '---' at the start of YAML.
            explicit_end: Whether to include '...' at the end of YAML.
            default_flow_style: Use block style YAML.
            allow_unicode: Allow unicode in YAML output.
            comment_prefix: Prefix to add to each line (for comment blocks).
            **kwargs: Additional arguments for yaml.dump.
        Returns:
            Canonical YAML string (UTF-8, normalized line endings), with optional comment prefix.
        """
        import pydantic

        if isinstance(block, dict):
            # Convert dict[str, Any]to NodeMetadataBlock, handling type conversions
            if "entrypoint" in block and isinstance(block["entrypoint"], str):
                from omnibase_core.models.core.model_entrypoint import EntrypointBlock

                if "://" in block["entrypoint"]:
                    type_, target = block["entrypoint"].split("://", 1)
                    block["entrypoint"] = EntrypointBlock(type=type_, target=target)
            try:
                block = NodeMetadataBlock(**block)  # type: ignore[arg-type]
            except (pydantic.ValidationError, TypeError):
                block = NodeMetadataBlock.model_validate(block)

        block_dict = block.model_dump(mode="json")
        # Protocol-compliant placeholders
        protocol_placeholders = {
            EnumNodeMetadataField.HASH.value: "0" * 64,
            EnumNodeMetadataField.LAST_MODIFIED_AT.value: "1970-01-01T00:00:00Z",
        }
        # Dynamically determine string and list fields from the model
        string_fields = set()
        list_fields = set()

        for name, field in NodeMetadataBlock.model_fields.items():
            annotation = field.annotation
            if annotation is None:
                continue
            origin = getattr(annotation, "__origin__", None)

            # Check for Union types
            if origin is Union and hasattr(annotation, "__args__"):
                args = annotation.__args__
                if str in args:
                    string_fields.add(name)
                if list in args:
                    list_fields.add(name)
            # Check for direct types
            elif annotation is str:
                string_fields.add(name)
            elif annotation is list:
                list_fields.add(name)

        normalized_dict: dict[str, object] = {}
        # Always emit all fields in model_fields order, using value from block_dict or default if missing/None
        for k, field in NodeMetadataBlock.model_fields.items():
            v = block_dict.get(k, None)
            # Replace volatile fields with protocol placeholder ONLY if in volatile_fields
            if (
                volatile_fields
                and k in protocol_placeholders
                and k
                in [f.value if hasattr(f, "value") else f for f in volatile_fields]
            ):
                normalized_dict[k] = protocol_placeholders[k]
                continue
            # Convert EnumNodeMetadataField to .value
            if isinstance(v, EnumNodeMetadataField):
                v = v.value
            # Normalize string fields
            if k in string_fields and (v is None or v == "null"):
                v = field.default if field.default is not None else ""
                normalized_dict[k] = v
                continue
            # Normalize list[Any]fields
            if k in list_fields and (v is None or v == "null"):
                v = field.default if field.default is not None else []
                normalized_dict[k] = v
                continue
            # Normalize booleans
            if isinstance(v, bool):
                v = "true" if v else "false"
            # Normalize numbers
            if isinstance(v, float):
                v = format(v, ".15g")
            # Sort list[Any]s of dict[str, Any]s
            if isinstance(v, list) and v and all(isinstance(x, dict) for x in v):
                v = sorted(v, key=lambda d: d["name"])
            # Sort dict[str, Any]s
            if isinstance(v, dict):
                v = dict(sorted(v.items()))
            # If still None, use default if available
            if v is None and field.default is not None:
                v = field.default
            normalized_dict[k] = v

        # --- PATCH START: Protocol-compliant entrypoint and null omission ---
        # Remove all None/null/empty fields except protocol-required ones
        protocol_required = {"tools"}
        filtered_dict = {}
        canonical_versions = get_canonical_versions()
        for k, v in normalized_dict.items():
            # Always emit canonical version fields
            if k == "metadata_version":
                filtered_dict[k] = canonical_versions.metadata_version
                continue
            if k == "protocol_version":
                filtered_dict[k] = canonical_versions.protocol_version
                continue
            if k == "schema_version":
                filtered_dict[k] = canonical_versions.schema_version
                continue
            # PATCH: Flatten entrypoint to URI string
            if k == "entrypoint":

                if isinstance(v, EntrypointBlock):
                    filtered_dict[k] = v.to_uri()
                elif isinstance(v, dict) and "type" in v and "target" in v:
                    filtered_dict[k] = EntrypointBlock.from_serializable_dict().to_uri()
                elif isinstance(v, str):
                    filtered_dict[k] = (
                        EntrypointBlock.from_uri(v).to_uri()
                        if "://" in v or "@" in v
                        else v
                    )
                else:
                    filtered_dict[k] = str(v)
                continue
            # PATCH: Flatten namespace to URI string
            if k == "namespace":
                from omnibase_core.models.core.model_node_metadata import Namespace

                if isinstance(v, Namespace):
                    filtered_dict[k] = str(v)
                elif isinstance(v, dict) and "value" in v:
                    filtered_dict[k] = str(Namespace(**v))
                elif isinstance(v, str):
                    filtered_dict[k] = str(Namespace(value=v))
                else:
                    filtered_dict[k] = str(v)
                continue
            # PATCH: Omit all None/null/empty fields (except protocol-required)
            if (v == "" or v is None or v in ({}, [])) and k not in protocol_required:
                continue
            filtered_dict[k] = v
        # PATCH: Remove all None values before YAML dump
        filtered_dict = {k: v for k, v in filtered_dict.items() if v is not None}

        # Use centralized YAML dumping for security and consistency
        from omnibase_core.utils.safe_yaml_loader import _dump_yaml_content

        yaml_str = _dump_yaml_content(
            sort_keys=sort_keys,
            default_flow_style=default_flow_style,
            allow_unicode=allow_unicode,
            explicit_start=explicit_start,
            explicit_end=explicit_end,
            indent=2,
            width=120,
        )
        # --- PATCH END ---
        if comment_prefix:
            yaml_str = "\n".join(
                f"{comment_prefix}{line}" if line.strip() else ""
                for line in yaml_str.splitlines()
            )
        return yaml_str

    def normalize_body(self, body: str) -> str:
        """
        Canonical normalization for file body content.
        Args:
            body: The file body content to normalize.
        Returns:
            Normalized file body as a string.
        """
        body = body.replace("\r\n", "\n").replace("\r", "\n")
        norm = body.rstrip(" \t\r\n") + "\n"
        assert "\r" not in norm, "Carriage return found after normalization"
        return norm

    def canonicalize_for_hash(
        block: Union[dict[str, object], "NodeMetadataBlock"],
        body: str,
        volatile_fields: tuple[EnumNodeMetadataField, ...] = (
            EnumNodeMetadataField.HASH,
            EnumNodeMetadataField.LAST_MODIFIED_AT,
        ),
        placeholder: str = "<PLACEHOLDER>",
        comment_prefix: str = "",
        **kwargs: object,
    ) -> str:
        """
        Canonicalize a metadata block and file body for hash computation.
        Args:
            block: A dict[str, Any]or NodeMetadataBlock instance (must implement model_dump(mode="json")).
            body: The file body content to normalize and include in hash.
            volatile_fields: Fields to replace with protocol placeholder values.
            placeholder: Placeholder value for volatile fields.
            comment_prefix: Prefix to add to each line (for comment blocks).
            **kwargs: Additional arguments for canonicalization.
        Returns:
            Canonical string for hash computation.
        """
        meta_yaml = self.canonicalize_metadata_block(
            volatile_fields=volatile_fields,
            placeholder=placeholder,
            explicit_start=False,
            explicit_end=False,
            comment_prefix=comment_prefix,
        )
        norm_body = self.normalize_body(body)
        return meta_yaml.rstrip("\n") + "\n\n" + norm_body.lstrip("\n")


normalize_body = CanonicalYAMLSerializer().normalize_body


def extract_metadata_block_and_body(
    content: str,
    open_delim: str,
    close_delim: str,
    event_bus=None,
) -> tuple[str | None, str]:
    """
    Canonical utility: Extract the metadata block (if present) and the rest of the file content.
    Returns (block_str or None, rest_of_content).
    - For Markdown: If open/close delimiters are the Markdown constants, extract the block between them, then extract the YAML block (--- ... ...) from within that.
    - For other types: Use the existing logic.

    Args:
        content: File content to extract metadata from
        open_delim: Opening delimiter for metadata block
        close_delim: Closing delimiter for metadata block
        event_bus: Event bus for protocol-pure logging
    """
    import re
    from pathlib import Path

    from omnibase_core.models.metadata.model_metadata_constants import (
        MD_META_CLOSE,
        MD_META_OPEN,
    )

    _component_name = Path(__file__).stem

    # Fast path: plain YAML file with '---' at start and no closing '...'
    if (
        open_delim == "---"
        and content.lstrip().startswith("---")
        and "..." not in content
    ):
        return content, ""
    # Special case: Markdown HTML comment delimiters
    if open_delim == MD_META_OPEN and close_delim == MD_META_CLOSE:
        # Find the HTML comment block
        pattern = (
            rf"(?ms)"  # multiline, dotall
            rf"^[ \t\r\f\v]*{re.escape(MD_META_OPEN)}\n"  # open delimiter
            rf"([\s\S]+?)"  # block content
            rf"{re.escape(MD_META_CLOSE)}[ \t\r\f\v]*\n?"  # close delimiter
        )
        match = re.search(pattern, content)
        if match:
            block_str = match.group(1)
            rest = content[match.end() :]
            # Now extract the YAML block (--- ... ...) from within block_str
            yaml_pattern = r"---\n([\s\S]+?)\n\.\.\."
            yaml_match = re.search(yaml_pattern, block_str)
            if yaml_match:
                yaml_block = f"---\n{yaml_match.group(1)}\n..."
                return yaml_block, rest
            return None, rest
        return None, content
    # Default: Accept both commented and non-commented delimiter forms
    pattern = (
        rf"(?ms)"  # multiline, dotall
        rf"^(?:[ \t\r\f\v]*\n)*"  # any number of leading blank lines/whitespace
        rf"[ \t\r\f\v]*(?:#\s*)?{re.escape(open_delim)}[ \t]*\n"  # open delimiter
        rf"((?:[ \t\r\f\v]*(?:#\s*)?.*\n)*?)"  # block content: any number of lines, each optionally commented
        rf"[ \t\r\f\v]*(?:#\s*)?{re.escape(close_delim)}[ \t]*\n?"  # close delimiter
    )
    match = re.search(pattern, content)
    if match:
        block_start = match.start()
        block_end = match.end()
        block_str = content[block_start:block_end]
        rest = content[block_end:]
        block_lines = block_str.splitlines()
        block_str_stripped = "\n".join(
            _strip_comment_prefix(line) for line in block_lines
        )
        return block_str_stripped, rest
    # Fallback: treat the whole content as the block (plain YAML file)
    return content, ""


def strip_block_delimiters_and_assert(
    lines: list[str],
    delimiters: set[str],
    context: str = "",
) -> str:
    """
    Canonical utility: Remove all lines that exactly match any delimiter. Assert none remain after filtering.
    Args:
        lines: List of lines (after comment prefix stripping)
        delimiters: Set of delimiter strings (imported from canonical constants)
        context: Optional context string for error messages
    Returns:
        Cleaned YAML string (no delimiters)
    Raises:
        AssertionError if any delimiter lines remain after filtering.
    """
    cleaned = [line for line in lines if line.strip() not in delimiters]
    remaining = [line for line in cleaned if line.strip() in delimiters]
    if remaining:
        msg = f"Delimiter(s) still present after filtering in {context}: {remaining}"
        raise ModelOnexError(msg, EnumCoreErrorCode.INTERNAL_ERROR)
    return "\n".join(cleaned).strip()
