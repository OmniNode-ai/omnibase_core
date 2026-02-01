"""Policy loader for cross-repo validation.

Loads and validates policy contracts from YAML files.
Supports single-level policy inheritance via the `extends` field.

Inheritance Rules (OMN-1774):
- Single-level only: A child policy can extend a parent, but the parent
  cannot extend another policy. Multi-level chaining is explicitly forbidden.
- Child overrides parent: On conflict, child values take precedence.
- Dict fields merge: Child entries override parent entries, but non-conflicting
  parent entries are preserved.
- List/tuple fields concatenate: Parent values first, then child values appended.
- Deterministic merge order: Always parent-first, child-second for predictable results.

Related tickets: OMN-1771, OMN-1774
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.models.validation.model_rule_configs import ModelRuleConfigBase
from omnibase_core.models.validation.model_validation_discovery_config import (
    ModelValidationDiscoveryConfig,
)
from omnibase_core.models.validation.model_validation_policy_contract import (
    ModelValidationPolicyContract,
)
from omnibase_core.validation.cross_repo.rule_registry import RuleRegistry


def load_policy(policy_path: Path) -> ModelValidationPolicyContract:
    """Load a validation policy from a YAML file.

    If the policy has an `extends` field, the parent policy is loaded first
    and merged with the child. Only single-level inheritance is supported.

    Args:
        policy_path: Path to the policy YAML file.

    Returns:
        Validated policy contract (with inheritance resolved if applicable).

    Raises:
        ModelOnexError: If the file cannot be read, parsed, or has invalid inheritance.
    """
    if not policy_path.exists():
        raise ModelOnexError(
            message=f"Policy file not found: {policy_path}",
            error_code=EnumCoreErrorCode.FILE_NOT_FOUND,
        )

    try:
        content = policy_path.read_text(encoding="utf-8")
        # yaml-ok: Parse raw YAML to dict, then validate through _parse_policy_data
        data = yaml.safe_load(content)
    except OSError as e:
        raise ModelOnexError(
            message=f"Failed to read policy file: {e}",
            error_code=EnumCoreErrorCode.FILE_READ_ERROR,
        ) from e
    except yaml.YAMLError as e:
        raise ModelOnexError(
            message=f"Failed to parse policy YAML: {e}",
            error_code=EnumCoreErrorCode.CONFIGURATION_PARSE_ERROR,
        ) from e

    # Check for inheritance
    extends = data.get("extends")
    if extends:
        data = _resolve_inheritance(data, extends, policy_path)

    return _parse_policy_data(data, policy_path)


# ONEX_EXCLUDE: dict_str_any - raw YAML merge utilities need dict[str, Any] for pre-validation data
def _resolve_inheritance(
    child_data: dict[str, Any],
    extends_path: str,
    child_path: Path,
) -> dict[str, Any]:
    """Resolve single-level policy inheritance.

    Loads the parent policy and merges it with the child policy.
    Only single-level inheritance is allowed (parent cannot have extends).

    Args:
        child_data: The child policy raw YAML data.
        extends_path: Relative or absolute path to the parent policy.
        child_path: Path to the child policy (for resolving relative paths).

    Returns:
        Merged policy data with inheritance resolved.

    Raises:
        ModelOnexError: If parent not found or has multi-level inheritance.
    """
    # Resolve the parent path relative to the child policy's directory
    if extends_path.startswith(("./", "../")):
        parent_path = (child_path.parent / extends_path).resolve()
    else:
        parent_path = Path(extends_path)

    if not parent_path.exists():
        raise ModelOnexError(
            message=f"Parent policy not found: {extends_path} (resolved to {parent_path})",
            error_code=EnumCoreErrorCode.FILE_NOT_FOUND,
            context={
                "child_policy": str(child_path),
                "extends": extends_path,
                "resolved_parent": str(parent_path),
            },
        )

    # Load parent policy data
    try:
        parent_content = parent_path.read_text(encoding="utf-8")
        # yaml-ok: Parse raw YAML to dict for inheritance merging
        parent_data = yaml.safe_load(parent_content)
    except OSError as e:
        raise ModelOnexError(
            message=f"Failed to read parent policy file: {e}",
            error_code=EnumCoreErrorCode.FILE_READ_ERROR,
        ) from e
    except yaml.YAMLError as e:
        raise ModelOnexError(
            message=f"Failed to parse parent policy YAML: {e}",
            error_code=EnumCoreErrorCode.CONFIGURATION_PARSE_ERROR,
        ) from e

    # Enforce single-level inheritance: parent cannot have extends
    if parent_data.get("extends"):
        grandparent_extends = parent_data.get("extends")
        raise ModelOnexError(
            message=(
                f"Multi-level policy inheritance is not supported. "
                f"Parent policy '{extends_path}' also has an 'extends' field. "
                f"Only single-level inheritance is allowed."
            ),
            error_code=EnumCoreErrorCode.CONFIGURATION_PARSE_ERROR,
            context={
                "child_policy": str(child_path),
                "parent_policy": str(parent_path),
                "grandparent_extends": grandparent_extends,
                "inheritance_chain": f"{child_path} -> {parent_path} -> {grandparent_extends}",
            },
        )

    # Merge parent and child (child overrides parent)
    return _merge_policy_data(parent_data, child_data)


# ONEX_EXCLUDE: dict_str_any - raw YAML merge utilities need dict[str, Any] for pre-validation data
def _merge_policy_data(
    parent: dict[str, Any],
    child: dict[str, Any],
) -> dict[str, Any]:
    """Merge parent and child policy data with shallow inheritance.

    Merge rules:
    - Scalar fields: child wins
    - Dict fields (like `rules`): merge, child values override parent
    - List/tuple fields: concatenate (parent first, then child)
    - The `extends` field is not propagated to the merged result

    Args:
        parent: Parent policy raw data.
        child: Child policy raw data.

    Returns:
        Merged policy data.
    """
    merged: dict[str, Any] = {}  # ONEX_EXCLUDE: dict_str_any - raw YAML data

    # Get all keys from both parent and child
    all_keys = set(parent.keys()) | set(child.keys())
    # Remove 'extends' from merged result - it's a directive, not data
    all_keys.discard("extends")

    for key in all_keys:
        parent_val = parent.get(key)
        child_val = child.get(key)

        if child_val is None and parent_val is not None:
            # Parent has value, child doesn't - use parent
            merged[key] = parent_val
        elif child_val is not None and parent_val is None:
            # Child has value, parent doesn't - use child
            merged[key] = child_val
        elif child_val is not None and parent_val is not None:
            # Both have values - merge based on type
            merged[key] = _merge_field(key, parent_val, child_val)
        # If both are None, skip (don't add to merged)

    return merged


def _merge_field(key: str, parent_val: Any, child_val: Any) -> Any:
    """Merge a single field from parent and child.

    Performs recursive merging for nested structures.

    Args:
        key: Field name (for potential field-specific logic).
        parent_val: Parent field value.
        child_val: Child field value.

    Returns:
        Merged field value.
    """
    # Dict fields: merge recursively (child overrides on conflict)
    if isinstance(parent_val, dict) and isinstance(child_val, dict):
        return _merge_dict_recursive(parent_val, child_val)

    # List fields: concatenate (parent first, then child)
    if isinstance(parent_val, list) and isinstance(child_val, list):
        return parent_val + child_val

    # Tuple fields: concatenate (parent first, then child)
    if isinstance(parent_val, tuple) and isinstance(child_val, tuple):
        return parent_val + child_val

    # Scalar fields or type mismatch: child wins
    return child_val


# ONEX_EXCLUDE: dict_str_any - raw YAML merge utilities need dict[str, Any] for pre-validation data
def _merge_dict_recursive(
    parent: dict[str, Any],
    child: dict[str, Any],
) -> dict[str, Any]:
    """Recursively merge two dicts with child overriding parent.

    Args:
        parent: Parent dict.
        child: Child dict (values take precedence on conflict).

    Returns:
        Merged dict.
    """
    merged: dict[str, Any] = {}  # ONEX_EXCLUDE: dict_str_any - raw YAML data

    all_keys = set(parent.keys()) | set(child.keys())

    for key in all_keys:
        parent_val = parent.get(key)
        child_val = child.get(key)

        if child_val is None and parent_val is not None:
            merged[key] = parent_val
        elif child_val is not None and parent_val is None:
            merged[key] = child_val
        elif child_val is not None and parent_val is not None:
            # Both have values - merge based on type
            merged[key] = _merge_field(key, parent_val, child_val)
        # If both are None, skip

    return merged


def _parse_policy_data(
    data: dict,  # type: ignore[type-arg]
    source_path: Path,
) -> ModelValidationPolicyContract:
    """Parse policy data into a typed contract.

    Args:
        data: Raw YAML data.
        source_path: Path for error messages.

    Returns:
        Validated policy contract.

    Raises:
        ModelOnexError: If the data is invalid.
    """
    try:
        # Parse version
        version_data = data.get("policy_version", {})
        policy_version = ModelSemVer(
            major=version_data.get("major", 1),
            minor=version_data.get("minor", 0),
            patch=version_data.get("patch", 0),
        )

        # Parse discovery config
        discovery_data = data.get("discovery", {})
        discovery = ModelValidationDiscoveryConfig(
            include_globs=tuple(discovery_data.get("include_globs", ["**/*.py"])),
            exclude_globs=tuple(discovery_data.get("exclude_globs", [])),
            contract_roots=tuple(discovery_data.get("contract_roots", [])),
            language_mode=discovery_data.get("language_mode", "python"),
            skip_generated=discovery_data.get("skip_generated", True),
            generated_markers=tuple(
                discovery_data.get(
                    "generated_markers", ["# AUTO-GENERATED", "# DO NOT EDIT"]
                )
            ),
        )

        # Parse rules with typed configs
        rules_data = data.get("rules", {})
        rules: dict[str, ModelRuleConfigBase] = {}

        for rule_id, rule_config in rules_data.items():
            if not RuleRegistry.is_registered(rule_id):
                # Skip unknown rules (could log a warning here)
                continue

            config_type = RuleRegistry.get_config_type(rule_id)
            rules[rule_id] = config_type.model_validate(rule_config)

        # Build the contract
        return ModelValidationPolicyContract(
            policy_id=data.get("policy_id", "unknown"),
            policy_version=policy_version,
            repo_id=data.get("repo_id", "unknown"),
            extends=data.get("extends"),
            discovery=discovery,
            rules=rules,
            baselines=(),  # TODO(OMN-1774): Parse baselines in Phase 0.5
        )

    except ValidationError as e:
        raise ModelOnexError(
            message=f"Invalid policy format in {source_path}: {e}",
            error_code=EnumCoreErrorCode.CONFIGURATION_PARSE_ERROR,
        ) from e
    except (KeyError, TypeError) as e:
        raise ModelOnexError(
            message=f"Invalid policy structure in {source_path}: {e}",
            error_code=EnumCoreErrorCode.CONFIGURATION_PARSE_ERROR,
        ) from e


__all__ = ["load_policy"]
