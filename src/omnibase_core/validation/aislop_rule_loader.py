# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Aislop rule loader: resolves the effective rule set for a repo (OMN-11132).

Resolution order:
  1. Load bundled default rules from contracts/aislop_default_rules.yaml
  2. Load optional per-repo config from <repo_root>/.onex/aislop-rules.yaml
  3. Merge: apply overrides then append custom_rules
"""

from __future__ import annotations

import importlib.resources
from pathlib import Path

import yaml

from omnibase_core.models.validation.model_aislop_config import ModelAislopConfig
from omnibase_core.models.validation.model_aislop_rule import ModelAislopRule
from omnibase_core.models.validation.model_aislop_rule_override import (
    ModelAislopRuleOverride,
)
from omnibase_core.models.validation.model_aislop_rule_set import ModelAislopRuleSet
from omnibase_core.models.validation.model_antipattern_registry import (
    ModelAntipatternRegistry,
)

_CONTRACTS_PKG = "omnibase_core.contracts"
_DEFAULT_YAML = "aislop_default_rules.yaml"

# pattern_type values from ModelAntipatternEntry that map directly to ModelAislopRule
_AISLOP_COMPATIBLE_PATTERN_TYPES = frozenset(
    {"regex_line", "regex_ast_docstring", "grep_code", "ast_check"}
)


def load_default_rules() -> ModelAislopRuleSet:
    """Return the bundled default aislop rule set.

    Reads from omnibase_core/contracts/aislop_default_rules.yaml via
    importlib.resources so it works both in dev and in installed wheels.
    """
    try:
        ref = importlib.resources.files(_CONTRACTS_PKG) / _DEFAULT_YAML
        raw = ref.read_text(encoding="utf-8")
    except (FileNotFoundError, TypeError) as exc:
        # Fallback: resolve relative to this file's package location
        fallback = Path(__file__).parent.parent / "contracts" / _DEFAULT_YAML
        if fallback.exists():
            raw = fallback.read_text(encoding="utf-8")
        else:
            raise FileNotFoundError(  # error-ok: bundled YAML is missing — fatal config error
                f"Cannot locate {_DEFAULT_YAML}; tried importlib.resources and {fallback}"
            ) from exc

    data = yaml.safe_load(raw)
    return ModelAislopRuleSet.model_validate(data)


def load_repo_config(repo_root: Path) -> ModelAislopConfig | None:
    """Load per-repo aislop config from <repo_root>/.onex/aislop-rules.yaml.

    Returns None if the file does not exist (per-repo overrides are optional).
    Raises ValidationError if the file exists but is malformed.
    """
    config_path = repo_root / ".onex" / "aislop-rules.yaml"
    if not config_path.exists():
        return None
    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    return ModelAislopConfig.model_validate(data)


def merge_rules(
    defaults: ModelAislopRuleSet,
    config: ModelAislopConfig | None,
) -> ModelAislopRuleSet:
    """Apply per-repo overrides and custom rules on top of defaults.

    Override semantics:
    - Override fields that are None → keep the default value.
    - Unknown name + allow_new=False → ValidationError (prevents silent typos).
    - Unknown name + allow_new=True → treated as a declaration for a custom_rule entry.
    - custom_rules are appended after merging overrides.
    """
    if config is None:
        return defaults

    default_by_name: dict[str, ModelAislopRule] = {r.name: r for r in defaults.rules}
    override_by_name: dict[str, ModelAislopRuleOverride] = {
        o.name: o for o in config.overrides
    }

    # Validate overrides reference known rules (unless allow_new=True)
    for name, override in override_by_name.items():
        if name not in default_by_name and not override.allow_new:
            known = sorted(default_by_name)
            raise ValueError(  # error-ok: config validation, not runtime error
                f"Unknown aislop rule name '{name}'. "
                f"Set allow_new=True to declare a new rule. "
                f"Known rules: {known}"
            )

    # Apply overrides to existing rules
    merged: list[ModelAislopRule] = []
    for rule in defaults.rules:
        maybe_override: ModelAislopRuleOverride | None = override_by_name.get(rule.name)
        if maybe_override is None:
            merged.append(rule)
            continue
        ov: ModelAislopRuleOverride = maybe_override
        merged.append(
            ModelAislopRule(
                name=rule.name,
                severity=ov.severity if ov.severity is not None else rule.severity,
                enabled=ov.enabled if ov.enabled is not None else rule.enabled,
                pattern_type=rule.pattern_type,
                pattern=rule.pattern,
                file_globs=ov.file_globs
                if ov.file_globs is not None
                else rule.file_globs,
                suppression_annotation=rule.suppression_annotation,
                description=rule.description,
            )
        )

    # Append custom rules
    merged.extend(config.custom_rules)

    return ModelAislopRuleSet(rules=merged)


def resolve_rules(repo_root: Path) -> ModelAislopRuleSet:
    """Full resolution pipeline: defaults → per-repo config → merged result."""
    defaults = load_default_rules()
    config = load_repo_config(repo_root)
    return merge_rules(defaults, config)


def resolve_rules_from_registry(
    registry: ModelAntipatternRegistry,
) -> ModelAislopRuleSet:
    """Convert compatible antipattern registry entries to a ModelAislopRuleSet.

    Filters to entries whose pattern_type is in _AISLOP_COMPATIBLE_PATTERN_TYPES
    (excludes 'semantic' entries which require vector search). Each matching entry
    is converted field-by-field into a ModelAislopRule.
    """
    rules: list[ModelAislopRule] = []
    for entry in registry.entries:
        if entry.pattern_type not in _AISLOP_COMPATIBLE_PATTERN_TYPES:
            continue
        rules.append(
            ModelAislopRule(
                name=entry.name,
                severity=entry.severity,
                enabled=True,
                pattern_type=entry.pattern_type,  # type: ignore[arg-type]  # NOTE(OMN-11921): ModelAntipatternEntry pattern_type is a wider Literal that includes "semantic"; we guard above but mypy cannot narrow frozenset membership to Literal
                pattern=entry.pattern,
                file_globs=list(entry.file_globs),
                suppression_annotation=entry.suppression_annotation,
                description=entry.description,
            )
        )
    return ModelAislopRuleSet(rules=rules)


def resolve_rules_unified(repo_root: Path) -> ModelAislopRuleSet:
    """Merge legacy aislop defaults and antipattern registry into one rule set.

    Resolution order:
      1. Load legacy aislop defaults (aislop_default_rules.yaml)
      2. Load registry rules (antipattern_registry.yaml, filtered to compatible types)
      3. Build merged list: start with registry rules, then append legacy rules whose
         name does not appear in the registry (registry wins on duplicate names).
    """
    from omnibase_core.validation.antipattern_registry_loader import (
        load_default_antipatterns,
    )

    legacy = load_default_rules()
    registry = load_default_antipatterns()
    registry_rules = resolve_rules_from_registry(registry)

    registry_names = {r.name for r in registry_rules.rules}

    # Registry rules first; legacy rules added only when not already covered
    merged: list[ModelAislopRule] = list(registry_rules.rules)
    for rule in legacy.rules:
        if rule.name not in registry_names:
            merged.append(rule)

    return ModelAislopRuleSet(rules=merged)


__all__ = [
    "load_default_rules",
    "load_repo_config",
    "merge_rules",
    "resolve_rules",
    "resolve_rules_from_registry",
    "resolve_rules_unified",
]
