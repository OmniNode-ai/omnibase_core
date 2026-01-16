"""
Contract Diff Helper Module.

Provides semantic diffing functionality for ONEX contracts.
This module is used by the cli_contract.py diff command.

Diff Algorithm Overview
-----------------------

The diff algorithm performs a **semantic comparison** of two ONEX contract
YAML files, producing categorized change reports:

1. **Recursive Dictionary Traversal**: The ``diff_contract_dicts()`` function
   recursively compares nested dictionaries, building dot-separated paths
   (e.g., ``descriptor.timeout_ms``) for each field.

2. **List Comparison Strategies**:

   - **Identity-based matching**: For lists of dicts with identity keys
     (``name``, ``id``, ``handler_id``, etc.), elements are matched by
     identity rather than position.
   - **Positional comparison**: For simple lists or lists without identity
     keys, elements are compared by index position.

3. **Change Categorization**: Detected changes are categorized into:

   - **Behavioral changes**: Changes to fields that affect runtime behavior
     (purity, idempotency, timeouts, handlers, FSM, etc.)
   - **Added/Removed/Changed**: Standard diff categories for other fields

4. **Severity Assignment**: Each change is assigned a severity level:

   - **high**: Behavioral fields (may affect runtime semantics)
   - **medium**: Version fields or removed fields
   - **low**: Other modifications

5. **Exclusion Filtering**: Metadata fields (``_metadata`` section) are
   excluded by default to focus on functional contract differences.

Example Usage::

    from omnibase_core.cli.cli_contract_diff import (
        diff_contract_dicts,
        categorize_diff_entries,
        format_text_diff_output,
    )

    old_data = {"name": "old", "descriptor": {"timeout_ms": 1000}}
    new_data = {"name": "new", "descriptor": {"timeout_ms": 2000}}

    diffs = diff_contract_dicts(old_data, new_data)
    result = categorize_diff_entries(diffs)
    print(format_text_diff_output(result))

.. versionadded:: 0.6.0
    Added as part of Contract CLI Tooling (OMN-1129)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal, TypeGuard

import click
import yaml

from omnibase_core.enums.enum_log_level import EnumLogLevel
from omnibase_core.logging.logging_structured import emit_log_event_sync
from omnibase_core.models.cli.model_diff_entry import ModelDiffEntry
from omnibase_core.models.cli.model_diff_result import ModelDiffResult
from omnibase_core.types.type_json import JsonType

# ==============================================================================
# Type Guards for Type-Safe List Operations
# ==============================================================================


def _is_list_of_dicts(
    items: list[JsonType],
) -> TypeGuard[list[dict[str, JsonType]]]:
    """Type guard to check if a list contains only dictionaries.

    This provides proper type narrowing for mypy, allowing safe access to
    dict methods on list elements after the guard passes. Using TypeGuard
    is preferred over cast() because it provides both runtime verification
    and compile-time type narrowing.

    Args:
        items: A list of JsonType values to check.

    Returns:
        True if all items are dicts, False otherwise. When True is returned,
        mypy narrows the type to list[dict[str, JsonType]].

    Examples:
        >>> items: list[JsonType] = [{"a": 1}, {"b": 2}]
        >>> if _is_list_of_dicts(items):
        ...     # items is now typed as list[dict[str, JsonType]]
        ...     keys = items[0].keys()  # Type-safe access
    """
    return bool(items) and all(isinstance(item, dict) for item in items)


# ==============================================================================
# Contract Diff Types and Constants
# ==============================================================================

# Behavioral fields that warrant special attention during diff.
#
# These fields directly affect runtime behavior of ONEX nodes. Changes to these
# fields may alter execution semantics, timing, error handling, or state transitions.
# The diff algorithm highlights changes to these fields in a separate "BEHAVIORAL
# CHANGES" section with high severity ratings.
#
# Field categories:
# - descriptor.*: Node execution semantics (purity, idempotency, timeouts, retries)
# - handlers: Event/intent handling registration (changes affect event routing)
# - dependencies: External contract dependencies (changes may break execution)
# - capabilities: Advertised node capabilities (changes affect discovery)
# - state_machine/fsm: FSM configuration for reducers (changes affect state flow)
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

# Fields to exclude from comparison by default.
#
# The _metadata section contains build-time information (profile, version, hash,
# timestamps) that is not part of the functional contract specification. These
# fields are excluded to focus diff output on semantically meaningful changes.
#
# Excluded fields include:
# - _metadata.profile: Base profile name
# - _metadata.profile_version: Profile version
# - _metadata.runtime_version: Build-time runtime version
# - _metadata.merge_hash: Deterministic hash of merge inputs
# - _metadata.generated_at: Build timestamp
# - _metadata.source_patch: Source patch file path
DEFAULT_EXCLUDE_PREFIXES: frozenset[str] = frozenset(
    {
        "_metadata",
    }
)

# Type aliases for internal use within this module
DiffEntry = ModelDiffEntry
DiffResult = ModelDiffResult

# Maximum file size for contract files (10 MB).
# This limit prevents denial-of-service attacks via extremely large input files
# that could exhaust memory. 10 MB is generous for contract YAML files which
# typically range from 1-50 KB. Files larger than this are almost certainly
# not valid contracts and should be rejected early.
MAX_CONTRACT_FILE_SIZE: int = 10 * 1024 * 1024  # 10 MB

# Dangerous path prefixes that should never be read by CLI tools.
# These system directories contain sensitive configuration and should
# not be accessed by contract tools.
_DANGEROUS_PATH_PREFIXES: tuple[str, ...] = (
    "/etc",
    "/usr",
    "/bin",
    "/sbin",
    "/lib",
    "/var/log",
    "/boot",
    "/root",
    "/sys",
    "/proc",
    "/dev",
)

# Truncation constants for format_diff_value
ELLIPSIS_STR: str = "..."
ELLIPSIS_LENGTH: int = len(ELLIPSIS_STR)

# Default maximum length for formatted diff values before truncation.
# 60 characters provides enough context for most field values while keeping
# output readable in terminal displays (typical terminal width is 80-120 chars).
DEFAULT_MAX_VALUE_LENGTH: int = 60

# Width of the separator line in diff summary output.
# 40 characters provides a clear visual break between the diff content and the
# summary statistics while keeping the output compact for terminal displays.
DIFF_SUMMARY_SEPARATOR_WIDTH: int = 40


# ==============================================================================
# Security Validation Functions
# ==============================================================================


def _validate_input_path_security(path: Path) -> Path:
    """Validate and resolve an input file path for security.

    Performs security checks to prevent path traversal attacks and
    accidental access to sensitive system directories.

    Args:
        path: The input file path to validate.

    Returns:
        The resolved (absolute) path if valid.

    Raises:
        click.ClickException: If the path is invalid or potentially dangerous.

    Security Checks:
        1. Resolves the path to an absolute path (follows symlinks)
        2. Detects path traversal patterns (.. in resolved path)
        3. Blocks access to sensitive system directories
    """
    resolved = path.resolve()
    resolved_str = str(resolved)

    # Check for path traversal patterns in the resolved path.
    # After resolve(), ".." should not appear in the path. If it does,
    # it indicates a suspicious symlink chain or filesystem manipulation.
    if ".." in resolved_str:
        raise click.ClickException(
            f"Path traversal detected: cannot read from '{resolved_str}'"
        )

    # Block access to sensitive system directories
    for prefix in _DANGEROUS_PATH_PREFIXES:
        if resolved_str.startswith(prefix + "/") or resolved_str == prefix:
            raise click.ClickException(
                f"Cannot read from system directory '{prefix}'. "
                f"Resolved path: {resolved_str}"
            )

    return resolved


def _validate_file_size(path: Path) -> None:
    """Validate file size to prevent DoS attacks.

    Args:
        path: The resolved file path to check.

    Raises:
        click.ClickException: If the file is too large or cannot be accessed.
    """
    try:
        file_size = path.stat().st_size
    except FileNotFoundError:
        raise click.ClickException(f"File not found: '{path}'") from None
    except PermissionError:
        raise click.ClickException(
            f"Permission denied: cannot access '{path}'"
        ) from None
    except OSError as e:
        raise click.ClickException(f"Cannot access file '{path}': {e}") from e

    if file_size > MAX_CONTRACT_FILE_SIZE:
        size_mb = file_size / (1024 * 1024)
        limit_mb = MAX_CONTRACT_FILE_SIZE / (1024 * 1024)
        raise click.ClickException(
            f"File too large: '{path}' is {size_mb:.2f} MB. "
            f"Maximum allowed size is {limit_mb:.0f} MB. "
            f"Contract files should be small YAML documents."
        )


# ==============================================================================
# Contract Diff Helper Functions
# ==============================================================================


def is_behavioral_field(path: str) -> bool:
    """Check if a field path is a behavioral field.

    Behavioral fields are those that affect runtime behavior of ONEX nodes.
    This includes execution semantics, handlers, dependencies, and state machines.

    The check handles nested paths by matching:
    - Exact matches (e.g., "handlers")
    - Child paths (e.g., "handlers.my_handler")
    - Array access (e.g., "handlers[0]")
    - Parent paths (e.g., "descriptor" matches "descriptor.purity")

    Args:
        path: Dot-separated field path (e.g., "descriptor.timeout_ms").

    Returns:
        True if this is a behavioral field that affects runtime behavior.

    Examples:
        >>> is_behavioral_field("descriptor.timeout_ms")
        True
        >>> is_behavioral_field("handlers[0].name")
        True
        >>> is_behavioral_field("description")
        False
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

    Excluded paths are filtered out during diff to focus on semantically
    meaningful changes. By default, the _metadata section is excluded.

    Args:
        path: Dot-separated field path (e.g., "_metadata.generated_at").

    Returns:
        True if this field should be excluded from diff output.

    Examples:
        >>> should_exclude_from_diff("_metadata.merge_hash")
        True
        >>> should_exclude_from_diff("descriptor.timeout_ms")
        False
    """
    for prefix in DEFAULT_EXCLUDE_PREFIXES:
        if path == prefix or path.startswith(f"{prefix}."):
            return True
    return False


def get_diff_severity(path: str, change_type: str) -> Literal["high", "medium", "low"]:
    """Determine severity of a change based on field path and change type.

    Severity levels help users prioritize review of contract changes:

    - **high**: Behavioral fields that may change runtime semantics
    - **medium**: Version fields or removed fields (potential breaking changes)
    - **low**: Other modifications (documentation, metadata, etc.)

    Args:
        path: Dot-separated field path.
        change_type: Type of change ("added", "removed", "changed").

    Returns:
        Severity level: "high", "medium", or "low".

    Examples:
        >>> get_diff_severity("descriptor.timeout_ms", "changed")
        'high'
        >>> get_diff_severity("node_version.major", "changed")
        'medium'
        >>> get_diff_severity("description", "changed")
        'low'
    """
    if is_behavioral_field(path):
        return "high"
    if "version" in path.lower():
        return "medium"
    if change_type == "removed":
        return "medium"
    return "low"


def format_diff_value(
    value: JsonType, max_length: int = DEFAULT_MAX_VALUE_LENGTH
) -> str:
    """Format a value for human-readable text display.

    Converts JSON-compatible values to string representations suitable for
    diff output. Long values are truncated with ellipsis to maintain readability.

    Args:
        value: Value to format (None, bool, str, int, float, list, or dict).
        max_length: Maximum length before truncation. Defaults to
            DEFAULT_MAX_VALUE_LENGTH (60 chars).

    Returns:
        Formatted string representation of the value.

    Examples:
        >>> format_diff_value(None)
        'null'
        >>> format_diff_value(True)
        'true'
        >>> format_diff_value("hello")
        '"hello"'
        >>> format_diff_value({"key": "value"})
        '{"key": "value"}'
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

    Performs a deep comparison of two dictionaries, generating DiffEntry
    objects for each difference found. Nested dicts and lists are compared
    recursively.

    Args:
        old: The old contract dictionary.
        new: The new contract dictionary.
        path: Current path prefix for nested fields (used internally).

    Returns:
        List of DiffEntry objects representing all differences found.

    Examples:
        >>> old = {"name": "old", "version": 1}
        >>> new = {"name": "new", "version": 1}
        >>> diffs = diff_contract_dicts(old, new)
        >>> len(diffs)
        1
        >>> diffs[0].path
        'name'
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

    Uses two strategies for list comparison:

    1. **Identity-based matching**: For lists of dicts that all contain a
       common identity key (name, id, handler_id, etc.), elements are matched
       by identity value rather than position. This produces more meaningful
       diffs when list order changes.

    2. **Positional comparison**: For simple lists or lists without identity
       keys, elements are compared by index position.

    Args:
        old_list: The old list.
        new_list: The new list.
        path: Current path for this list field.

    Returns:
        List of DiffEntry objects for list differences.

    Examples:
        >>> old = [{"name": "a", "value": 1}]
        >>> new = [{"name": "a", "value": 2}]
        >>> diffs = diff_contract_lists(old, new, "items")
        >>> diffs[0].path
        'items[name=a].value'
    """
    diffs: list[DiffEntry] = []

    # Check if lists contain dicts with identity keys.
    # We require ALL elements to be dicts (not just the first) for identity-based
    # comparison to work correctly. Mixed-type lists fall back to positional comparison.
    # Using TypeGuard provides proper type narrowing for mypy without unsafe cast().
    if _is_list_of_dicts(old_list) and _is_list_of_dicts(new_list):
        # After TypeGuard check, both lists are typed as list[dict[str, JsonType]]
        identity_key = find_list_identity_key(old_list, new_list)
        if identity_key:
            return diff_lists_by_identity(old_list, new_list, path, identity_key)

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

    Searches for common keys in both lists' first elements that could serve
    as unique identifiers. Candidate keys are checked in priority order:
    name, id, handler_id, step_id, event_type, state_id.

    Args:
        old_list: List of dicts from old contract.
        new_list: List of dicts from new contract.

    Returns:
        Identity key field name if found, None otherwise.

    Examples:
        >>> old = [{"handler_id": "h1", "name": "Handler 1"}]
        >>> new = [{"handler_id": "h1", "name": "Handler One"}]
        >>> find_list_identity_key(old, new)
        'name'
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

    Matches list elements by their identity key value rather than position.
    This produces more meaningful diffs when list order changes or elements
    are inserted/removed.

    Args:
        old_list: List of dicts from old contract.
        new_list: List of dicts from new contract.
        path: Current path for this list field.
        identity_key: Key to use for matching elements (e.g., "name").

    Returns:
        List of DiffEntry objects for list differences.

    Examples:
        >>> old = [{"name": "a", "v": 1}, {"name": "b", "v": 2}]
        >>> new = [{"name": "b", "v": 2}, {"name": "a", "v": 9}]
        >>> diffs = diff_lists_by_identity(old, new, "items", "name")
        >>> diffs[0].path
        'items[name=a].v'
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

    Organizes diff entries into semantic categories for display:

    - **behavioral_changes**: High-priority changes to runtime behavior fields
    - **added**: Fields present in new but not old
    - **removed**: Fields present in old but not new
    - **changed**: Fields with different values

    Args:
        diffs: List of all diff entries from comparison.

    Returns:
        DiffResult with categorized entries.

    Examples:
        >>> entry = DiffEntry(change_type="added", path="name", new_value="x")
        >>> result = categorize_diff_entries([entry])
        >>> len(result.added)
        1
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


# ==============================================================================
# Text Formatting Helpers
# ==============================================================================


def _format_diff_entry_line(entry: DiffEntry, prefix: str) -> str:
    """Format a single diff entry as a text line.

    Handles the three change types with appropriate formatting:
    - changed: "path: old_value -> new_value"
    - added: "path: (added) new_value" or just "path: new_value"
    - removed: "path: (removed) old_value" or just "path: old_value"

    Args:
        entry: The diff entry to format.
        prefix: Line prefix character ("!", "+", "-", "~").

    Returns:
        Formatted line string without newline.
    """
    if entry.change_type == "changed":
        old_str = format_diff_value(entry.old_value)
        new_str = format_diff_value(entry.new_value)
        return f"  {prefix} {entry.path}: {old_str} -> {new_str}"
    elif entry.change_type == "added":
        new_str = format_diff_value(entry.new_value)
        # For behavioral section, show "(added)" label; for ADDED section, just value
        if prefix == "!":
            return f"  {prefix} {entry.path}: (added) {new_str}"
        return f"  {prefix} {entry.path}: {new_str}"
    else:  # removed
        old_str = format_diff_value(entry.old_value)
        # For behavioral section, show "(removed)" label; for REMOVED section, just value
        if prefix == "!":
            return f"  {prefix} {entry.path}: (removed) {old_str}"
        return f"  {prefix} {entry.path}: {old_str}"


def _format_diff_section(
    entries: list[DiffEntry],
    section_name: str,
    prefix: str,
) -> list[str]:
    """Format a section of diff entries with header.

    Creates a formatted section with a header and indented entries.
    Returns empty list if no entries.

    Args:
        entries: List of diff entries for this section.
        section_name: Section header text (e.g., "ADDED:", "REMOVED:").
        prefix: Line prefix character for entries.

    Returns:
        List of formatted lines including header and trailing blank line.
    """
    if not entries:
        return []

    lines: list[str] = [section_name]
    for entry in entries:
        lines.append(_format_diff_entry_line(entry, prefix))
    lines.append("")  # Trailing blank line after section
    return lines


def format_text_diff_output(result: DiffResult) -> str:
    """Format diff result as human-readable text.

    Produces a formatted text report with sections for each change category:
    - BEHAVIORAL CHANGES (if any)
    - ADDED
    - REMOVED
    - CHANGED

    Each section shows the field path and values with appropriate symbols:
    - ! for behavioral changes
    - + for additions
    - - for removals
    - ~ for modifications

    Args:
        result: The diff result to format.

    Returns:
        Formatted text output suitable for terminal display.

    Examples:
        >>> result = DiffResult(old_path="a.yaml", new_path="b.yaml")
        >>> result.added.append(DiffEntry(
        ...     change_type="added", path="name", new_value="test"))
        >>> output = format_text_diff_output(result)
        >>> "ADDED:" in output
        True
    """
    lines: list[str] = []
    lines.append(f"Contract Diff: {result.old_path} -> {result.new_path}")
    lines.append("")

    if not result.has_changes:
        lines.append("No differences found.")
        return "\n".join(lines)

    # Format each section using the helper function
    lines.extend(
        _format_diff_section(result.behavioral_changes, "BEHAVIORAL CHANGES:", "!")
    )
    lines.extend(_format_diff_section(result.added, "ADDED:", "+"))
    lines.extend(_format_diff_section(result.removed, "REMOVED:", "-"))
    lines.extend(_format_diff_section(result.changed, "CHANGED:", "~"))

    # Summary footer
    lines.append("-" * DIFF_SUMMARY_SEPARATOR_WIDTH)
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

    Produces a JSON representation of the diff result suitable for
    programmatic consumption or storage.

    Args:
        result: The diff result to format.

    Returns:
        Pretty-printed JSON string with 2-space indentation.

    Examples:
        >>> result = DiffResult()
        >>> output = format_json_diff_output(result)
        >>> '"has_changes": false' in output
        True
    """
    return json.dumps(result.to_dict(), indent=2, default=str)


def format_yaml_diff_output(result: DiffResult) -> str:
    """Format diff result as YAML.

    Produces a YAML representation of the diff result suitable for
    storage or integration with other YAML-based tools.

    Args:
        result: The diff result to format.

    Returns:
        YAML string with block style formatting.

    Examples:
        >>> result = DiffResult()
        >>> output = format_yaml_diff_output(result)
        >>> "has_changes: false" in output
        True
    """
    return yaml.dump(result.to_dict(), default_flow_style=False, sort_keys=False)


def _format_yaml_error_context(error: yaml.YAMLError, content: str) -> str:
    """Extract and format error context from a YAML error.

    Args:
        error: The YAML error to extract context from.
        content: The original file content for context.

    Returns:
        Formatted error context string with line information.
    """
    lines: list[str] = []

    # Try to extract line/column from error mark
    if hasattr(error, "problem_mark") and error.problem_mark is not None:
        mark = error.problem_mark
        lines.append(f"  Line {mark.line + 1}, Column {mark.column + 1}")

        # Show the problematic line if possible
        content_lines = content.splitlines()
        if 0 <= mark.line < len(content_lines):
            problem_line = content_lines[mark.line]
            lines.append(f"  >>> {problem_line}")
            if mark.column > 0:
                lines.append(f"      {' ' * mark.column}^")

    # Include the error problem description
    if hasattr(error, "problem") and error.problem:
        lines.append(f"  Problem: {error.problem}")

    if not lines:
        lines.append(f"  {error}")

    return "\n".join(lines)


def load_contract_yaml_file(path: Path) -> dict[str, JsonType]:
    """Load a YAML file and return its contents as a dictionary.

    Reads and parses a YAML file, validating that the root element is
    a dictionary (as required for ONEX contracts). Provides detailed
    error messages with context for common issues.

    Security Checks:
        - Path traversal prevention (blocks ".." after resolution)
        - System directory access prevention
        - File size validation (max 10 MB to prevent DoS)

    Args:
        path: Path to the YAML file to load.

    Returns:
        Dictionary containing the parsed YAML contents.

    Raises:
        click.ClickException: If file cannot be read, parsed, or is not a dict.
            Error messages include context such as line numbers and hints.

    Examples:
        >>> from pathlib import Path
        >>> # load_contract_yaml_file(Path("contract.yaml"))  # doctest: +SKIP
    """
    # Security: Validate path before any file operations
    resolved_path = _validate_input_path_security(path)

    # Security: Check file size to prevent DoS attacks
    _validate_file_size(resolved_path)

    try:
        content = resolved_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        emit_log_event_sync(
            EnumLogLevel.ERROR,
            "Contract file not found",
            {"file_path": str(resolved_path)},
        )
        raise click.ClickException(
            f"File not found: '{resolved_path}'\n"
            f"  Hint: Check that the file path is correct and the file exists."
        ) from None
    except PermissionError:
        emit_log_event_sync(
            EnumLogLevel.ERROR,
            "Permission denied reading contract file",
            {"file_path": str(resolved_path)},
        )
        raise click.ClickException(
            f"Permission denied reading file: '{resolved_path}'\n"
            f"  Hint: Check file permissions with 'ls -la {resolved_path}'"
        ) from None
    except OSError as e:
        emit_log_event_sync(
            EnumLogLevel.ERROR,
            "OS error reading contract file",
            {"file_path": str(resolved_path), "error": str(e)},
        )
        raise click.ClickException(
            f"Cannot read file '{resolved_path}': {e}\n  Error type: {type(e).__name__}"
        ) from e

    # Check for empty file
    if not content.strip():
        emit_log_event_sync(
            EnumLogLevel.ERROR,
            "Contract file is empty",
            {"file_path": str(resolved_path)},
        )
        raise click.ClickException(
            f"File is empty: '{resolved_path}'\n"
            f"  Hint: Contract files must contain valid YAML content."
        )

    try:
        data = yaml.safe_load(content)
    except yaml.scanner.ScannerError as e:
        # Extract line/column info from YAML error if available
        error_context = _format_yaml_error_context(e, content)
        emit_log_event_sync(
            EnumLogLevel.ERROR,
            "YAML syntax error in contract file",
            {"file_path": str(resolved_path), "error": str(e)},
        )
        raise click.ClickException(
            f"YAML syntax error in '{resolved_path}':\n{error_context}\n"
            f"  Hint: Check for incorrect indentation, missing colons, "
            f"or invalid characters."
        ) from e
    except yaml.parser.ParserError as e:
        error_context = _format_yaml_error_context(e, content)
        emit_log_event_sync(
            EnumLogLevel.ERROR,
            "YAML structure error in contract file",
            {"file_path": str(resolved_path), "error": str(e)},
        )
        raise click.ClickException(
            f"YAML structure error in '{resolved_path}':\n{error_context}\n"
            f"  Hint: Check for mismatched brackets, quotes, "
            f"or invalid YAML structure."
        ) from e
    except yaml.YAMLError as e:
        emit_log_event_sync(
            EnumLogLevel.ERROR,
            "YAML error in contract file",
            {"file_path": str(resolved_path), "error": str(e)},
        )
        raise click.ClickException(
            f"Cannot parse YAML in '{resolved_path}': {e}\n"
            f"  Error type: {type(e).__name__}"
        ) from e

    if data is None:
        emit_log_event_sync(
            EnumLogLevel.ERROR,
            "Contract file contains only comments or whitespace",
            {"file_path": str(resolved_path)},
        )
        raise click.ClickException(
            f"File contains only comments or whitespace: '{resolved_path}'\n"
            f"  Hint: Contract files must contain a YAML object/dictionary."
        )

    if not isinstance(data, dict):
        emit_log_event_sync(
            EnumLogLevel.ERROR,
            "Contract file root element is not a dictionary",
            {"file_path": str(resolved_path), "actual_type": type(data).__name__},
        )
        raise click.ClickException(
            f"Expected YAML object/dict in '{resolved_path}', "
            f"got {type(data).__name__}\n"
            f"  Hint: Contract files must start with key-value pairs, "
            f"not a list or scalar."
        )
    return data


__all__ = [
    "BEHAVIORAL_FIELDS",
    "DEFAULT_EXCLUDE_PREFIXES",
    "DEFAULT_MAX_VALUE_LENGTH",
    "DIFF_SUMMARY_SEPARATOR_WIDTH",
    "MAX_CONTRACT_FILE_SIZE",
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
