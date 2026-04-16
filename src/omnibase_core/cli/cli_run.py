# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""``onex run`` — execute a workflow or dispatch a deterministic node."""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path

import click

from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.runtime.runtime_local import (
    RuntimeLocal,
    parse_backend_overrides,
)

_OMNIMARKET_PATH_DEFAULT = "/Volumes/PRO-G40/Code/omni_home/omnimarket"


def _is_yaml_path(value: str) -> bool:
    """Return True if value looks like a file path to a YAML workflow."""
    return value.endswith((".yaml", ".yml")) or Path(value).exists()


def _resolve_omnimarket_path() -> Path:
    raw = os.environ.get("OMNIMARKET_PATH", _OMNIMARKET_PATH_DEFAULT)
    return Path(raw)


@click.command(
    "run", context_settings={"allow_extra_args": True, "ignore_unknown_options": True}
)
@click.argument("target")
@click.option(
    "--state-root",
    type=click.Path(path_type=Path),
    default=".onex_state",
    show_default=True,
    help="Root directory for disk state (workflow mode only).",
)
@click.option(
    "--backend",
    multiple=True,
    help="Override backend: --backend event_bus=inmemory (workflow mode only).",
)
@click.option(
    "--timeout",
    type=int,
    default=300,
    show_default=True,
    help="Max execution time in seconds (workflow mode only).",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    default=False,
    help="Enable DEBUG-level logging (default is INFO).",
)
@click.argument("extra_args", nargs=-1, type=click.UNPROCESSED)
def run_workflow(
    target: str,
    state_root: Path,
    backend: tuple[str, ...],
    timeout: int,
    verbose: bool,
    extra_args: tuple[str, ...],
) -> None:
    """Run a workflow YAML or dispatch a deterministic node by name.

    TARGET is either:

    \b
      - A path to a workflow contract YAML file, OR
      - A node name (e.g. merge_sweep, coderabbit_triage)

    \b
    Node invocation (passes extra args directly to the node):
        onex run merge_sweep --repos OmniNode-ai/omni_home --dry-run
        onex run coderabbit_triage --repo OmniNode-ai/omniclaude --pr 1332

    \b
    Workflow invocation (existing behaviour):
        onex run workflow.yaml
        onex run workflow.yaml --timeout 60 --backend event_bus=inmemory

    \b
    Exit codes (node mode):
        Forwarded from the node process.

    \b
    Exit codes (workflow mode):
        0  COMPLETED — terminal event received, evidence written
        1  FAILED / TIMEOUT — terminal event with failure or timeout exceeded
        2  PARTIAL — evidence written but no terminal event
    """
    if _is_yaml_path(target):
        _run_workflow_yaml(
            workflow_path=Path(target),
            state_root=state_root,
            backend=backend,
            timeout=timeout,
            verbose=verbose,
        )
    else:
        _run_node(node_name=target, extra_args=extra_args, verbose=verbose)


def _run_workflow_yaml(
    workflow_path: Path,
    state_root: Path,
    backend: tuple[str, ...],
    timeout: int,
    verbose: bool,
) -> None:
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
        datefmt="%H:%M:%S",
    )

    if not workflow_path.exists():
        click.echo(f"Error: Workflow contract not found: {workflow_path}", err=True)
        sys.exit(1)

    try:
        backend_overrides = parse_backend_overrides(backend)
    except ModelOnexError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    runtime = RuntimeLocal(
        workflow_path=workflow_path,
        state_root=state_root,
        backend_overrides=backend_overrides,
        timeout=timeout,
    )
    runtime.run()
    sys.exit(runtime.exit_code)


def _run_node(node_name: str, extra_args: tuple[str, ...], verbose: bool) -> None:
    omnimarket = _resolve_omnimarket_path()
    if not omnimarket.exists():
        click.echo(
            f"Error: omnimarket not found at {omnimarket}. "
            "Set OMNIMARKET_PATH to override.",
            err=True,
        )
        sys.exit(1)

    # Normalise: strip leading node_ prefix if user accidentally included it
    if node_name.startswith("node_"):
        module_name = f"omnimarket.nodes.{node_name}"
    else:
        module_name = f"omnimarket.nodes.node_{node_name}"

    if verbose:
        click.echo(f"Dispatching node: {module_name}", err=True)

    cmd = [sys.executable, "-m", module_name, *extra_args]
    result = subprocess.run(cmd, cwd=str(omnimarket), check=False)
    sys.exit(result.returncode)
