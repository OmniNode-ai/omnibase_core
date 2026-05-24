# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Antipattern registry loader: resolves effective registry for a repo (OMN-11911).

Resolution order:
  1. Load bundled defaults from contracts/antipattern_registry.yaml
  2. Load optional per-repo overrides from <repo_root>/.onex/antipattern-overrides.yaml
  3. Merge: apply field overrides then append custom_entries
"""

from __future__ import annotations

import importlib.resources
from pathlib import Path
from typing import Any

import yaml

from omnibase_core.models.validation.model_antipattern_entry import (
    ModelAntipatternEntry,
)
from omnibase_core.models.validation.model_antipattern_registry import (
    ModelAntipatternRegistry,
)

_CONTRACTS_PKG = "omnibase_core.contracts"
_DEFAULT_YAML = "antipattern_registry.yaml"
_OVERRIDES_PATH = ".onex/antipattern-overrides.yaml"


def load_default_registry() -> ModelAntipatternRegistry:
    """Return the bundled default antipattern registry.

    Reads from omnibase_core/contracts/antipattern_registry.yaml via
    importlib.resources so it works both in dev and in installed wheels.
    """
    try:
        ref = importlib.resources.files(_CONTRACTS_PKG) / _DEFAULT_YAML
        raw = ref.read_text(encoding="utf-8")
    except (FileNotFoundError, TypeError) as exc:
        fallback = Path(__file__).parent.parent / "contracts" / _DEFAULT_YAML
        if fallback.exists():
            raw = fallback.read_text(encoding="utf-8")
        else:
            raise FileNotFoundError(  # error-ok: bundled YAML missing — fatal config error
                f"Cannot locate {_DEFAULT_YAML}; tried importlib.resources and {fallback}"
            ) from exc

    data = yaml.safe_load(raw)
    return ModelAntipatternRegistry.model_validate(data)


def _load_overrides(repo_root: Path) -> dict[str, Any] | None:
    """Load per-repo overrides from <repo_root>/.onex/antipattern-overrides.yaml.

    Returns None if the file does not exist.
    """
    config_path = repo_root / _OVERRIDES_PATH
    if not config_path.exists():
        return None
    return yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}


def _merge_registry(
    defaults: ModelAntipatternRegistry,
    overrides_data: dict[str, Any] | None,
) -> ModelAntipatternRegistry:
    """Apply per-repo overrides and custom entries on top of defaults.

    Override semantics (mirrors aislop_rule_loader.merge_rules):
    - Override fields that are None → keep the default value.
    - Unknown name → ValueError (prevents silent typos).
    - custom_entries are appended after merging overrides.
    """
    if overrides_data is None:
        return defaults

    override_list: list[dict[str, Any]] = overrides_data.get("overrides", [])
    custom_list: list[dict[str, Any]] = overrides_data.get("custom_entries", [])

    default_by_name: dict[str, ModelAntipatternEntry] = {
        e.name: e for e in defaults.entries
    }
    override_by_name: dict[str, dict[str, Any]] = {o["name"]: o for o in override_list}

    # Validate all override names reference known entries
    for name in override_by_name:
        if name not in default_by_name:
            known = sorted(default_by_name)
            raise ValueError(
                f"Unknown antipattern name '{name}' in overrides. Known: {known}"
            )

    # Apply field overrides
    merged: list[ModelAntipatternEntry] = []
    for entry in defaults.entries:
        ov = override_by_name.get(entry.name)
        if ov is None:
            merged.append(entry)
            continue
        # Rebuild entry with overridden fields; None values keep the default
        base = entry.model_dump()
        for field in ("severity", "enforcement", "file_globs"):
            if ov.get(field) is not None:
                base[field] = ov[field]
        merged.append(ModelAntipatternEntry.model_validate(base))

    # Append custom entries
    for raw in custom_list:
        merged.append(ModelAntipatternEntry.model_validate(raw))

    return ModelAntipatternRegistry(
        version=defaults.version,
        last_updated=defaults.last_updated,
        entries=tuple(merged),
    )


def resolve_antipatterns(repo_root: Path) -> ModelAntipatternRegistry:
    """Full resolution pipeline: defaults → per-repo overrides → merged result."""
    defaults = load_default_registry()
    overrides_data = _load_overrides(repo_root)
    return _merge_registry(defaults, overrides_data)


__all__ = [
    "load_default_registry",
    "resolve_antipatterns",
]
