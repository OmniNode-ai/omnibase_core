"""Policy loader for cross-repo validation.

Loads and validates policy contracts from YAML files.

Related ticket: OMN-1771
"""

from __future__ import annotations

from pathlib import Path

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

    Args:
        policy_path: Path to the policy YAML file.

    Returns:
        Validated policy contract.

    Raises:
        ModelOnexError: If the file cannot be read or parsed.
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

    return _parse_policy_data(data, policy_path)


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
