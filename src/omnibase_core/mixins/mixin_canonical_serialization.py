from __future__ import annotations

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
import types
from typing import Union, cast

from omnibase_core.enums import EnumNodeMetadataField
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.core.model_node_metadata import NodeMetadataBlock
from omnibase_core.models.core.model_project_metadata import get_canonical_versions
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.protocols import ContextValue, ProtocolCanonicalSerializer


def _strip_comment_prefix(
    block: str,
    comment_prefixes: tuple[str, ...] = ("# ", "#"),
) -> str:
    """
    Remove leading comment prefixes from each line of a block.
    Args:
        block: Multiline string block to process.
        comment_prefixes: Tuple/list of prefix strings to remove from line starts.
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

    NOTE: Field order is always as declared in NodeMetadataBlock.model_fields, never by dict or YAML loader order. This is required for perfect idempotency.

    - All nested collections (lists of dicts, dicts of dicts) are sorted by a stable key (e.g., 'name' or dict key).
    - All booleans are normalized to lowercase YAML ('true'/'false').
    - All numbers are formatted with consistent precision.
    """

    def canonicalize_metadata_block(
        self,
        metadata_block: dict[str, object] | NodeMetadataBlock,
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
        **kwargs: ContextValue,
    ) -> str:
        """
        Canonicalize a metadata block for deterministic YAML serialization and hash computation.
        Args:
            metadata_block: A dict[str, object] or NodeMetadataBlock instance (must implement model_dump(mode="json")).
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

        from omnibase_core.models.core.model_entrypoint import EntrypointBlock

        if isinstance(metadata_block, dict):
            # Preserve original dict for exception handler
            original_dict = metadata_block.copy()

            # Convert dict to NodeMetadataBlock, handling type conversions
            if "entrypoint" in metadata_block and isinstance(
                metadata_block["entrypoint"], str
            ):
                if "://" in metadata_block["entrypoint"]:
                    type_, target = metadata_block["entrypoint"].split("://", 1)
                    metadata_block["entrypoint"] = EntrypointBlock(
                        type=type_, target=target
                    )
            try:
                metadata_block = NodeMetadataBlock(**metadata_block)
            except (pydantic.ValidationError, TypeError):
                # Provide defaults for missing required fields to allow incomplete dicts
                import uuid as uuid_lib

                from omnibase_core.models.primitives.model_semver import ModelSemVer

                # Handle version conversion if it's a string
                version_value = original_dict.get("version")
                if isinstance(version_value, str):
                    # Parse version string like "1.0.0" into ModelSemVer
                    parts = version_value.split(".")
                    if len(parts) >= 3:
                        version_value = ModelSemVer(
                            major=int(parts[0]),
                            minor=int(parts[1]),
                            patch=int(parts[2]),
                        )
                    else:
                        version_value = ModelSemVer(major=0, minor=1, patch=0)
                elif version_value is None:
                    version_value = ModelSemVer(major=0, minor=1, patch=0)

                # Validate hash field format - must be 64 hex characters
                hash_value_raw = original_dict.get("hash", "0" * 64)
                hash_value = str(hash_value_raw) if hash_value_raw else "0" * 64
                if hash_value and (
                    len(hash_value) != 64
                    or not all(c in "0123456789abcdefABCDEF" for c in hash_value)
                ):
                    # Invalid hash format, use default placeholder
                    hash_value = "0" * 64

                # Use deterministic UUID based on name for consistency (or random if no name)
                name_raw = original_dict.get("name", "unknown")
                name = str(name_raw) if name_raw else "unknown"
                default_uuid = str(uuid_lib.uuid5(uuid_lib.NAMESPACE_DNS, name))

                defaults = {
                    "name": name,
                    "uuid": original_dict.get("uuid", default_uuid),
                    "author": original_dict.get("author", "OmniNode Team"),
                    "created_at": original_dict.get(
                        "created_at", "1970-01-01T00:00:00Z"
                    ),
                    "last_modified_at": original_dict.get(
                        "last_modified_at", "1970-01-01T00:00:00Z"
                    ),
                    "hash": hash_value,
                    "entrypoint": original_dict.get("entrypoint", "python://unknown"),
                    "namespace": original_dict.get(
                        "namespace", "python://omnibase.unknown"
                    ),
                    "version": version_value,
                    "description": original_dict.get("description")
                    or "Stamped by ONEX",
                }
                # Merge defaults with provided fields (provided fields override defaults)
                # Filter out None values from original_dict to prevent overriding defaults
                filtered_metadata = {
                    k: v for k, v in original_dict.items() if v is not None
                }
                complete_metadata = {**defaults, **filtered_metadata}
                # Update version in complete_metadata if it was converted
                if isinstance(original_dict.get("version"), str):
                    complete_metadata["version"] = version_value
                # Ensure hash is valid (replace invalid with placeholder)
                complete_metadata["hash"] = hash_value
                try:
                    metadata_block = NodeMetadataBlock(**complete_metadata)
                except (pydantic.ValidationError, TypeError):
                    # If still failing, use model_validate as last resort
                    metadata_block = NodeMetadataBlock.model_validate(complete_metadata)

        # At this point metadata_block is always NodeMetadataBlock
        # (either passed directly or converted from dict above)
        assert isinstance(metadata_block, NodeMetadataBlock)
        block_dict = metadata_block.model_dump(mode="json")
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

            # Check for Union types (both typing.Union and PEP 604 | syntax)
            # Note: PEP 604 unions (str | None) don't have __origin__ via getattr,
            # so we use isinstance(annotation, types.UnionType) to detect them
            is_union = origin is Union or isinstance(  # Handles typing.Union
                annotation, types.UnionType
            )  # Handles PEP 604 (str | None)
            if is_union and hasattr(annotation, "__args__"):
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
            # NOTE: EnumNodeMetadataField check removed - model_dump(mode="json")
            # already converts enums to their values, so v is never an enum instance
            # Normalize string fields
            if k in string_fields and (v is None or v == "null"):
                v = field.default if field.default is not None else ""
                normalized_dict[k] = v
                continue
            # Normalize list fields
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
            # Sort lists of dicts
            if isinstance(v, list) and v and all(isinstance(x, dict) for x in v):
                # Cast for mypy since we've verified all items are dicts with isinstance
                dict_list = cast(list[dict[str, object]], v)
                # Extract name field as string for sorting, with empty string default
                sorted_list: list[dict[str, object]] = sorted(
                    dict_list, key=lambda d: str(d.get("name", ""))
                )
                normalized_dict[k] = sorted_list
                continue
            # Sort dicts
            if isinstance(v, dict):
                normalized_dict[k] = dict(sorted(v.items()))
                continue
            # If still None, use default if available
            if v is None and field.default is not None:
                normalized_dict[k] = field.default
                continue
            normalized_dict[k] = v

        # --- PATCH START: Protocol-compliant entrypoint and null omission ---
        # Remove all None/null/empty fields except protocol-required ones
        protocol_required = {"tools"}
        filtered_dict: dict[str, object] = {}

        # Get canonical versions with fallback to defaults if project file not found
        try:
            canonical_versions = get_canonical_versions()
        except ModelOnexError:
            # Use default versions if project.onex.yaml not found (e.g., in tests)
            from omnibase_core.models.core.model_onex_version import (
                ModelOnexVersionInfo,
            )
            from omnibase_core.models.primitives.model_semver import ModelSemVer

            canonical_versions = ModelOnexVersionInfo(
                metadata_version=ModelSemVer(major=0, minor=1, patch=0),
                protocol_version=ModelSemVer(major=0, minor=1, patch=0),
                schema_version=ModelSemVer(major=0, minor=1, patch=0),
            )
        for key, val in normalized_dict.items():
            # Always emit canonical version fields
            if key == "metadata_version":
                filtered_dict[key] = str(canonical_versions.metadata_version)
                continue
            if key == "protocol_version":
                filtered_dict[key] = str(canonical_versions.protocol_version)
                continue
            if key == "schema_version":
                filtered_dict[key] = str(canonical_versions.schema_version)
                continue
            # PATCH: Flatten entrypoint to URI string
            if key == "entrypoint":
                # NOTE: EntrypointBlock isinstance check removed - model_dump(mode="json")
                # converts Pydantic models to dicts, so val is never an EntrypointBlock instance
                if isinstance(val, dict) and "type" in val and "target" in val:
                    # Access dict keys directly to avoid Any and maintain type safety
                    filtered_dict[key] = EntrypointBlock(
                        type=str(val["type"]),
                        target=str(val["target"]),
                    ).to_uri()
                elif isinstance(val, str):
                    filtered_dict[key] = (
                        EntrypointBlock.from_uri(val).to_uri()
                        if "://" in val or "@" in val
                        else val
                    )
                else:
                    filtered_dict[key] = str(val)
                continue
            # PATCH: Flatten namespace to URI string
            if key == "namespace":
                from omnibase_core.models.core.model_node_metadata import Namespace

                # NOTE: Namespace isinstance check removed - model_dump(mode="json")
                # converts Pydantic models to dicts, so val is never a Namespace instance
                if isinstance(val, dict) and "value" in val:
                    # Access dict key directly to avoid Any and maintain type safety
                    filtered_dict[key] = str(Namespace(value=str(val["value"])))
                elif isinstance(val, str):
                    filtered_dict[key] = str(Namespace(value=val))
                else:
                    filtered_dict[key] = str(val)
                continue
            # PATCH: Omit all None/null/empty fields (except protocol-required)
            if (
                val == "" or val is None or val in ({}, [])
            ) and key not in protocol_required:
                continue
            filtered_dict[key] = val
        # PATCH: Remove all None values before YAML dump
        filtered_dict = {k: v for k, v in filtered_dict.items() if v is not None}

        # Use centralized YAML dumping for security and consistency
        from omnibase_core.utils.util_safe_yaml_loader import _dump_yaml_content

        yaml_str = _dump_yaml_content(
            filtered_dict,
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
        # Normalize line endings
        body = body.replace("\r\n", "\n").replace("\r", "\n")

        # Strip trailing whitespace from each line
        lines = body.split("\n")
        normalized_lines = [line.rstrip() for line in lines]

        # Join back with newlines and ensure single trailing newline
        norm = "\n".join(normalized_lines).rstrip("\n") + "\n"

        assert "\r" not in norm, "Carriage return found after normalization"
        return norm

    def canonicalize_for_hash(
        self,
        block: dict[str, ContextValue],
        body: str,
        volatile_fields: tuple[str, ...] = ("hash", "last_modified_at"),
        placeholder: str | None = None,
        **kwargs: ContextValue,
    ) -> str:
        """
        Canonicalize a metadata block and file body for hash computation.
        Args:
            block: A dict representing a metadata block.
            body: The file body content to normalize and include in hash.
            volatile_fields: Fields to replace with protocol placeholder values.
            placeholder: Placeholder value for volatile fields.
            **kwargs: Additional arguments for canonicalization (e.g., comment_prefix).
        Returns:
            Canonical string for hash computation.
        """
        # Convert to dict if it's a model instance
        if hasattr(block, "model_dump"):
            block_dict = block.model_dump(mode="json")
        else:
            block_dict = block

        # Convert string field names to EnumNodeMetadataField
        enum_volatile_fields = tuple(
            EnumNodeMetadataField(field) if isinstance(field, str) else field
            for field in volatile_fields
        )

        # Use default placeholder if None
        actual_placeholder = placeholder if placeholder is not None else "<PLACEHOLDER>"

        # Extract comment_prefix from kwargs if present
        comment_prefix = str(kwargs.get("comment_prefix", ""))

        meta_yaml = self.canonicalize_metadata_block(
            metadata_block=block_dict,
            volatile_fields=enum_volatile_fields,
            placeholder=actual_placeholder,
            explicit_start=False,
            explicit_end=False,
            comment_prefix=comment_prefix,
        )
        norm_body = self.normalize_body(body)
        return meta_yaml.rstrip("\n") + "\n\n" + norm_body.lstrip("\n")


normalize_body = MixinCanonicalYAMLSerializer().normalize_body


def extract_metadata_block_and_body(
    content: str,
    open_delim: str,
    close_delim: str,
    _event_bus: object = None,
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

    # Fast path: plain YAML file with single '---' at start and no closing delimiters
    # Only applies if there's exactly one '---' (opening only, not closing)
    if (
        open_delim == "---"
        and content.lstrip().startswith("---")
        and "..." not in content
        and content.count("---") == 1  # Only one '---' delimiter
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
