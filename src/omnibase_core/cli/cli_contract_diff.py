# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
Contract Diff Helper Module.

Provides semantic diffing functionality for ONEX contracts.
This module is used by the cli_contract.py diff command.

.. versionadded:: 0.6.0
    Added as part of Contract CLI Tooling (OMN-1129)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import click
import yaml

from omnibase_core.models.cli.model_diff_entry import ModelDiffEntry
from omnibase_core.models.cli.model_diff_result import ModelDiffResult
from omnibase_core.types.type_json import JsonType

# ==============================================================================
# Contract Diff Types and Constants
# ==============================================================================


# Behavioral fields that warrant special attention during diff
# Changes to these fields affect runtime behavior
BEHAVIORAL_FIELDS: frozenset[str] = frozenset(
    {
        "descriptor.purity",
        "descriptor.idempotent",
        "descriptor.timeout_ms",
        "descriptor.retry_policy",
        "descriptor.circuit_breaker",
        "descriptor.node_kind",
        "descriptor.node_type",
        "handlers",
        "dependencies",
        "capabilities",
        "state_machine",
        "fsm",
    }
)

# Fields to exclude from comparison by default (metadata section)
DEFAULT_EXCLUDE_PREFIXES: frozenset[str] = frozenset(
    {
        "_metadata",
    }
)

# Type aliases for internal use within this module
DiffEntry = ModelDiffEntry
DiffResult = ModelDiffResult

# Truncation constants for format_diff_value
ELLIPSIS_STR: str = "..."
ELLIPSIS_LENGTH: int = len(ELLIPSIS_STR)


# ==============================================================================
# Contract Diff Helper Functions
# ==============================================================================


def is_behavioral_field(path: str) -> bool:
    """Check if a field path is a behavioral field.

    Args:
        path: Dot-separated field path.

    Returns:
        True if this is a behavioral field that affects runtime behavior.
    """
    if path in BEHAVIORAL_FIELDS:
        return True
    for behavioral in BEHAVIORAL_FIELDS:
        if path.startswith((f"{behavioral}.", f"{behavioral}[")):
            return True
        if behavioral.startswith(f"{path}."):
            return True
    return False


def should_exclude_from_diff(path: str) -> bool:
    """Check if a field path should be excluded from comparison.

    Args:
        path: Dot-separated field path.

    Returns:
        True if this field should be excluded from diff.
    """
    for prefix in DEFAULT_EXCLUDE_PREFIXES:
        if path == prefix or path.startswith(f"{prefix}."):
            return True
    return False


def get_diff_severity(path: str, change_type: str) -> str:
    """Determine severity of a change based on field path.

    Args:
        path: Dot-separated field path.
        change_type: Type of change (added, removed, changed).

    Returns:
        Severity level for this change (high, medium, low).
    """
    if is_behavioral_field(path):
        return "high"
    if "version" in path.lower():
        return "medium"
    if change_type == "removed":
        return "medium"
    return "low"


def format_diff_value(value: JsonType, max_length: int = 60) -> str:
    """Format a value for text display.

    Args:
        value: Value to format.
        max_length: Maximum length before truncation.

    Returns:
        Formatted string representation.
    """
    if value is None:
        return "null"
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, str):
        result = f'"{value}"'
    elif isinstance(value, (list, dict)):
        result = json.dumps(value, default=str)
    else:
        result = str(value)
    if len(result) > max_length:
        return result[: max_length - ELLIPSIS_LENGTH] + ELLIPSIS_STR
    return result


def diff_contract_dicts(
    old: dict[str, JsonType],
    new: dict[str, JsonType],
    path: str = "",
) -> list[DiffEntry]:
    """Recursively diff two contract dictionaries.

    Args:
        old: The old contract dictionary.
        new: The new contract dictionary.
        path: Current path prefix for nested fields.

    Returns:
        List of DiffEntry objects representing all differences.
    """
    diffs: list[DiffEntry] = []
    all_keys = set(old.keys()) | set(new.keys())

    for key in sorted(all_keys):
        current_path = f"{path}.{key}" if path else key
        if should_exclude_from_diff(current_path):
            continue

        if key not in old:
            severity = get_diff_severity(current_path, "added")
            diffs.append(
                DiffEntry(
                    change_type="added",
                    path=current_path,
                    new_value=new[key],
                    severity=severity,
                )
            )
        elif key not in new:
            severity = get_diff_severity(current_path, "removed")
            diffs.append(
                DiffEntry(
                    change_type="removed",
                    path=current_path,
                    old_value=old[key],
                    severity=severity,
                )
            )
        elif old[key] != new[key]:
            old_val, new_val = old[key], new[key]
            if isinstance(old_val, dict) and isinstance(new_val, dict):
                diffs.extend(diff_contract_dicts(old_val, new_val, current_path))
            elif isinstance(old_val, list) and isinstance(new_val, list):
                diffs.extend(diff_contract_lists(old_val, new_val, current_path))
            else:
                severity = get_diff_severity(current_path, "changed")
                diffs.append(
                    DiffEntry(
                        change_type="changed",
                        path=current_path,
                        old_value=old_val,
                        new_value=new_val,
                        severity=severity,
                    )
                )
    return diffs


def diff_contract_lists(
    old_list: list[JsonType],
    new_list: list[JsonType],
    path: str,
) -> list[DiffEntry]:
    """Diff two lists, detecting additions, removals, and changes.

    For lists of dicts, attempts to match by common identity keys.
    For other lists, uses positional comparison.

    Args:
        old_list: The old list.
        new_list: The new list.
        path: Current path for this list field.

    Returns:
        List of DiffEntry objects for list differences.
    """
    diffs: list[DiffEntry] = []

    # Check if lists contain dicts with identity keys
    if (
        old_list
        and new_list
        and isinstance(old_list[0], dict)
        and isinstance(new_list[0], dict)
    ):
        # Validate all items are dicts (not just first element)
        assert all(isinstance(item, dict) for item in old_list)
        assert all(isinstance(item, dict) for item in new_list)
        old_dicts = cast(list[dict[str, JsonType]], old_list)
        new_dicts = cast(list[dict[str, JsonType]], new_list)
        identity_key = find_list_identity_key(old_dicts, new_dicts)
        if identity_key:
            return diff_lists_by_identity(old_dicts, new_dicts, path, identity_key)

    # Fall back to positional comparison
    max_len = max(len(old_list), len(new_list))
    for i in range(max_len):
        item_path = f"{path}[{i}]"
        if i >= len(old_list):
            severity = get_diff_severity(path, "added")
            diffs.append(
                DiffEntry(
                    change_type="added",
                    path=item_path,
                    new_value=new_list[i],
                    severity=severity,
                )
            )
        elif i >= len(new_list):
            severity = get_diff_severity(path, "removed")
            diffs.append(
                DiffEntry(
                    change_type="removed",
                    path=item_path,
                    old_value=old_list[i],
                    severity=severity,
                )
            )
        elif old_list[i] != new_list[i]:
            old_item, new_item = old_list[i], new_list[i]
            if isinstance(old_item, dict) and isinstance(new_item, dict):
                diffs.extend(diff_contract_dicts(old_item, new_item, item_path))
            else:
                severity = get_diff_severity(path, "changed")
                diffs.append(
                    DiffEntry(
                        change_type="changed",
                        path=item_path,
                        old_value=old_item,
                        new_value=new_item,
                        severity=severity,
                    )
                )
    return diffs


def find_list_identity_key(
    old_list: list[dict[str, JsonType]],
    new_list: list[dict[str, JsonType]],
) -> str | None:
    """Find a common identity key for list element matching.

    Looks for common keys that could serve as unique identifiers.

    Args:
        old_list: List of dicts from old contract.
        new_list: List of dicts from new contract.

    Returns:
        Identity key field name, or None if no suitable key found.
    """
    candidates = ["name", "id", "handler_id", "step_id", "event_type", "state_id"]
    old_keys = set(old_list[0].keys()) if old_list else set()
    new_keys = set(new_list[0].keys()) if new_list else set()
    common_keys = old_keys & new_keys
    for candidate in candidates:
        if candidate in common_keys:
            return candidate
    return None


def diff_lists_by_identity(
    old_list: list[dict[str, JsonType]],
    new_list: list[dict[str, JsonType]],
    path: str,
    identity_key: str,
) -> list[DiffEntry]:
    """Diff lists using identity-based matching.

    Args:
        old_list: List of dicts from old contract.
        new_list: List of dicts from new contract.
        path: Current path for this list field.
        identity_key: Key to use for matching elements.

    Returns:
        List of DiffEntry objects for list differences.
    """
    diffs: list[DiffEntry] = []
    old_by_key: dict[JsonType, dict[str, JsonType]] = {}
    for item in old_list:
        if identity_key in item:
            old_by_key[item[identity_key]] = item
    new_by_key: dict[JsonType, dict[str, JsonType]] = {}
    for item in new_list:
        if identity_key in item:
            new_by_key[item[identity_key]] = item

    all_keys = set(old_by_key.keys()) | set(new_by_key.keys())
    for item_key in sorted(all_keys, key=str):
        item_path = f"{path}[{identity_key}={item_key}]"
        if item_key not in old_by_key:
            severity = get_diff_severity(path, "added")
            diffs.append(
                DiffEntry(
                    change_type="added",
                    path=item_path,
                    new_value=new_by_key[item_key],
                    severity=severity,
                )
            )
        elif item_key not in new_by_key:
            severity = get_diff_severity(path, "removed")
            diffs.append(
                DiffEntry(
                    change_type="removed",
                    path=item_path,
                    old_value=old_by_key[item_key],
                    severity=severity,
                )
            )
        elif old_by_key[item_key] != new_by_key[item_key]:
            diffs.extend(
                diff_contract_dicts(
                    old_by_key[item_key], new_by_key[item_key], item_path
                )
            )
    return diffs


def categorize_diff_entries(diffs: list[DiffEntry]) -> DiffResult:
    """Categorize diff entries into result categories.

    Args:
        diffs: List of all diff entries.

    Returns:
        DiffResult with categorized entries.
    """
    result = DiffResult()
    for diff_entry in diffs:
        if is_behavioral_field(diff_entry.path):
            result.behavioral_changes.append(diff_entry)
        elif diff_entry.change_type == "added":
            result.added.append(diff_entry)
        elif diff_entry.change_type == "removed":
            result.removed.append(diff_entry)
        else:
            result.changed.append(diff_entry)
    return result


def format_text_diff_output(result: DiffResult) -> str:
    """Format diff result as human-readable text.

    Args:
        result: The diff result to format.

    Returns:
        Formatted text output.
    """
    lines: list[str] = []
    lines.append(f"Contract Diff: {result.old_path} -> {result.new_path}")
    lines.append("")

    if not result.has_changes:
        lines.append("No differences found.")
        return "\n".join(lines)

    if result.behavioral_changes:
        lines.append("BEHAVIORAL CHANGES:")
        for diff_entry in result.behavioral_changes:
            if diff_entry.change_type == "changed":
                old_str = format_diff_value(diff_entry.old_value)
                new_str = format_diff_value(diff_entry.new_value)
                lines.append(f"  ! {diff_entry.path}: {old_str} -> {new_str}")
            elif diff_entry.change_type == "added":
                new_str = format_diff_value(diff_entry.new_value)
                lines.append(f"  ! {diff_entry.path}: (added) {new_str}")
            else:
                old_str = format_diff_value(diff_entry.old_value)
                lines.append(f"  ! {diff_entry.path}: (removed) {old_str}")
        lines.append("")

    if result.added:
        lines.append("ADDED:")
        for diff_entry in result.added:
            val_str = format_diff_value(diff_entry.new_value)
            lines.append(f"  + {diff_entry.path}: {val_str}")
        lines.append("")

    if result.removed:
        lines.append("REMOVED:")
        for diff_entry in result.removed:
            val_str = format_diff_value(diff_entry.old_value)
            lines.append(f"  - {diff_entry.path}: {val_str}")
        lines.append("")

    if result.changed:
        lines.append("CHANGED:")
        for diff_entry in result.changed:
            old_str = format_diff_value(diff_entry.old_value)
            new_str = format_diff_value(diff_entry.new_value)
            lines.append(f"  ~ {diff_entry.path}: {old_str} -> {new_str}")
        lines.append("")

    lines.append("-" * 40)
    lines.append(f"Total changes: {result.total_changes}")
    if result.behavioral_changes:
        lines.append(
            f"  Behavioral: {len(result.behavioral_changes)} "
            "(may affect runtime behavior)"
        )
    lines.append(f"  Added: {len(result.added)}")
    lines.append(f"  Removed: {len(result.removed)}")
    lines.append(f"  Changed: {len(result.changed)}")

    return "\n".join(lines)


def format_json_diff_output(result: DiffResult) -> str:
    """Format diff result as JSON.

    Args:
        result: The diff result to format.

    Returns:
        JSON string output.
    """
    return json.dumps(result.to_dict(), indent=2, default=str)


def format_yaml_diff_output(result: DiffResult) -> str:
    """Format diff result as YAML.

    Args:
        result: The diff result to format.

    Returns:
        YAML string output.
    """
    return yaml.dump(result.to_dict(), default_flow_style=False, sort_keys=False)


def load_contract_yaml_file(path: Path) -> dict[str, JsonType]:
    """Load a YAML file and return its contents as a dictionary.

    Args:
        path: Path to the YAML file.

    Returns:
        Dictionary containing the YAML contents.

    Raises:
        click.ClickException: If file cannot be read or parsed.
    """
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as e:
        raise click.ClickException(f"Cannot read file '{path}': {e}") from e

    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError as e:
        raise click.ClickException(f"Cannot parse YAML in '{path}': {e}") from e

    if not isinstance(data, dict):
        raise click.ClickException(
            f"Expected YAML object/dict in '{path}', got {type(data).__name__}"
        )
    return data


__all__ = [
    "BEHAVIORAL_FIELDS",
    "DEFAULT_EXCLUDE_PREFIXES",
    # Type aliases
    "DiffEntry",
    "DiffResult",
    # Model classes
    "ModelDiffEntry",
    "ModelDiffResult",
    "categorize_diff_entries",
    "diff_contract_dicts",
    "diff_contract_lists",
    "diff_lists_by_identity",
    "find_list_identity_key",
    "format_diff_value",
    "format_json_diff_output",
    "format_text_diff_output",
    "format_yaml_diff_output",
    "get_diff_severity",
    "is_behavioral_field",
    "load_contract_yaml_file",
    "should_exclude_from_diff",
]
