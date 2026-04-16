# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""``onex node <name>`` — execute a packaged ONEX node on the local runtime.

Resolves ``<name>`` via the ``onex.nodes`` entry-point group and loads the
packaged ``contract.yaml`` by default. An optional ``--contract`` override
points at an ad-hoc contract file instead. An optional ``--input`` flag
passes a JSON payload into the contract's input model.

This replaces the former ``onex run <contract_path>`` command (OMN-7068).
See ``docs/plans/2026-04-16-prove-core-runtime-standalone.md`` § Task 3.
"""

from __future__ import annotations

import importlib
import logging
import sys
from importlib.metadata import entry_points
from pathlib import Path

import click

from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.runtime.runtime_local import RuntimeLocal, parse_backend_overrides


def _resolve_packaged_contract(node_name: str) -> Path:
    """Resolve ``node_name`` via the ``onex.nodes`` entry-point group → packaged ``contract.yaml``.

    Convention (current, not eternal): packaged nodes registered under ``onex.nodes``
    colocate their contract at ``<module_dir>/contract.yaml``. This holds for every
    omnimarket node as of 2026-04-16. If a future node splits contract location or
    uses a wrapper module, extend this resolver — do not silently fall through.

    Raises:
        click.ClickException: If the name is unknown, duplicated, the module cannot
            be imported, the module has no ``__file__``, or the packaged contract
            is missing.
    """
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
    module_path = matches[0].value
    try:
        mod = importlib.import_module(module_path)
    except ImportError as exc:
        raise click.ClickException(
            f"Failed to import node module '{module_path}': {exc}"
        ) from exc

    if mod.__file__ is None:
        raise click.ClickException(
            f"Node '{node_name}' module '{module_path}' has no __file__; "
            "cannot locate packaged contract.yaml under current packaging convention."
        )
    module_dir = Path(mod.__file__).resolve().parent
    contract = module_dir / "contract.yaml"
    if not contract.exists():
        raise click.ClickException(
            f"Node '{node_name}' resolved to {module_dir} but no contract.yaml found there. "
            "This violates the current packaging convention (colocated contract.yaml). "
            "Use --contract to point at the actual contract location."
        )
    return contract


@click.command("node")
@click.argument("node_name")
@click.option(
    "--contract",
    "contract_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="Override the packaged contract with a path to a custom contract.yaml.",
)
@click.option(
    "--input",
    "input_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="JSON file containing the initial payload (validated against the contract's input model).",
)
@click.option(
    "--state-root",
    type=click.Path(path_type=Path),
    default=".onex_state",
    show_default=True,
    help="Root directory for disk state.",
)
@click.option(
    "--backend",
    multiple=True,
    help="Override backend: --backend event_bus=inmemory",
)
@click.option(
    "--timeout",
    type=int,
    default=300,
    show_default=True,
    help="Max execution time in seconds.",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    default=False,
    help="Enable DEBUG-level logging (default is INFO).",
)
def run_node_by_name(
    node_name: str,
    contract_path: Path | None,
    input_path: Path | None,
    state_root: Path,
    backend: tuple[str, ...],
    timeout: int,
    verbose: bool,
) -> None:
    """Run a packaged ONEX node on the local runtime, resolved by NAME.

    By default the packaged contract.yaml that ships with the node is used —
    no flags required for the common case. Use --contract to override.

    \b
    Exit codes:
        0  COMPLETED — terminal event received, evidence written
        1  FAILED / TIMEOUT — terminal event with failure or timeout exceeded
        2  PARTIAL — evidence written but no terminal event

    \b
    Examples:
        onex node merge_sweep
        onex node merge_sweep --input fixtures/real_prs.json
        onex node merge_sweep --contract ./custom_contract.yaml --state-root ./state
    """
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
        datefmt="%H:%M:%S",
    )

    resolved_contract = contract_path or _resolve_packaged_contract(node_name)

    try:
        backend_overrides = parse_backend_overrides(backend)
    except ModelOnexError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    runtime = RuntimeLocal(
        workflow_path=resolved_contract,
        state_root=state_root,
        backend_overrides=backend_overrides,
        input_path=input_path,
        timeout=timeout,
    )
    runtime.run()
    sys.exit(runtime.exit_code)
