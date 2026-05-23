# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Packaged node contract resolution helpers for ONEX CLI commands."""

from __future__ import annotations

import importlib.util
from importlib.metadata import entry_points
from pathlib import Path

import click


def _resolve_packaged_contract(node_name: str) -> Path:
    """Resolve ``node_name`` via ``onex.nodes`` entry points to ``contract.yaml``."""
    matches = [ep for ep in entry_points(group="onex.nodes") if ep.name == node_name]
    if not matches:
        known = sorted({ep.name for ep in entry_points(group="onex.nodes")})
        raise click.ClickException(
            f"Unknown node '{node_name}'. Known nodes: {', '.join(known) or '(none)'}"
        )
    if len(matches) > 1:
        sources = ", ".join(str(ep.dist) for ep in matches)
        raise click.ClickException(
            f"Duplicate entry-point name '{node_name}' registered by: {sources}. "
            "Disambiguate by uninstalling the conflicting package."
        )

    module_path = _entry_point_module(matches[0].value)
    spec = importlib.util.find_spec(module_path)
    if spec is None:
        raise click.ClickException(
            f"Failed to resolve node module '{module_path}' from installed metadata."
        )

    if spec.submodule_search_locations:
        module_dir = Path(next(iter(spec.submodule_search_locations))).resolve()
    elif spec.origin is not None:
        module_dir = Path(spec.origin).resolve().parent
    else:
        raise click.ClickException(
            f"Node '{node_name}' module '{module_path}' has no origin; "
            "cannot locate packaged contract.yaml under current packaging convention."
        )

    contract = module_dir / "contract.yaml"
    if not contract.exists():
        raise click.ClickException(
            f"Node '{node_name}' resolved to {module_dir} but no contract.yaml found there. "
            "This violates the current packaging convention (colocated contract.yaml). "
            "Use --contract to point at the actual contract location."
        )
    return contract


def _entry_point_module(value: str) -> str:
    """Return the importable module portion of an entry-point value."""
    return value.split(":", 1)[0].strip()
