# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""``onex run`` — execute a contract-declared workflow or a named ONEX node."""

from __future__ import annotations

import importlib
import logging
import subprocess
import sys
from pathlib import Path

import click

from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.runtime.runtime_local import (
    RuntimeLocal,
    parse_backend_overrides,
)

_NODE_CANDIDATES = (
    "omnimarket.nodes.{name}",
    "omnimarket.nodes.node_{name}",
)


def _resolve_node_module(name: str) -> str | None:
    """Try to import the node module and return the resolved module path.

    Tries ``omnimarket.nodes.<name>`` first, then ``omnimarket.nodes.node_<name>``.
    Returns the first importable module path, or None if neither resolves.
    """
    for template in _NODE_CANDIDATES:
        module_path = template.format(name=name)
        try:
            importlib.import_module(module_path)
            return module_path
        except ImportError:
            continue
    return None


@click.command(
    "run", context_settings={"ignore_unknown_options": True, "allow_extra_args": True}
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
@click.pass_context
def run_workflow(
    ctx: click.Context,
    target: str,
    state_root: Path,
    backend: tuple[str, ...],
    timeout: int,
    verbose: bool,
) -> None:
    """Run a workflow YAML or a named ONEX node.

    TARGET is either:

    \b
      - A path to a workflow contract YAML file (existing behavior), or
      - A node name such as ``merge_sweep`` or ``node_merge_sweep``

    \b
    When TARGET is a node name, any extra arguments are passed through to the
    node's own argument parser.  The --state-root, --backend, and --timeout
    flags apply only in workflow mode.

    \b
    Node name resolution order:
        1. omnimarket.nodes.<target>
        2. omnimarket.nodes.node_<target>

    \b
    Exit codes:
        0  COMPLETED — terminal event received, evidence written
        1  FAILED / TIMEOUT — terminal event with failure or timeout exceeded
        2  PARTIAL — evidence written but no terminal event

    \b
    Examples:
        onex run workflow.yaml
        onex run workflow.yaml --timeout 60
        onex run merge_sweep --dry-run
        onex run node_merge_sweep --repo omnibase_core
    """
    # Configure logging so runtime diagnostics are visible
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s %(levelname)-8s %(name)s \u2014 %(message)s",
        datefmt="%H:%M:%S",
    )

    target_path = Path(target)

    # Workflow YAML mode: path exists and has a YAML extension
    if target_path.suffix.lower() in {".yaml", ".yml"} and target_path.exists():
        try:
            backend_overrides = parse_backend_overrides(backend)
        except ModelOnexError as exc:
            click.echo(f"Error: {exc}", err=True)
            sys.exit(1)

        runtime = RuntimeLocal(
            workflow_path=target_path,
            state_root=state_root,
            backend_overrides=backend_overrides,
            timeout=timeout,
        )
        runtime.run()
        sys.exit(runtime.exit_code)

    # Workflow mode: path exists as a file (no YAML extension — preserve original
    # behaviour for edge cases like bare filenames)
    if target_path.exists() and target_path.is_file():
        try:
            backend_overrides = parse_backend_overrides(backend)
        except ModelOnexError as exc:
            click.echo(f"Error: {exc}", err=True)
            sys.exit(1)

        runtime = RuntimeLocal(
            workflow_path=target_path,
            state_root=state_root,
            backend_overrides=backend_overrides,
            timeout=timeout,
        )
        runtime.run()
        sys.exit(runtime.exit_code)

    # If the target looks like a YAML path but the file is missing, surface the
    # original "not found" error — preserves existing error message for that case.
    if target_path.suffix.lower() in {".yaml", ".yml"}:
        click.echo(f"Error: Workflow contract not found: {target_path}", err=True)
        sys.exit(1)

    # Node name mode: attempt to resolve as an omnimarket node module
    resolved = _resolve_node_module(target)
    if resolved is None:
        click.echo(
            f"Error: '{target}' is not a workflow YAML path or a known node name.\n"
            f"Expected a workflow YAML path or a node name "
            f"(e.g. `merge_sweep`, `node_coderabbit_triage`).",
            err=True,
        )
        sys.exit(1)

    # Invoke the node module via subprocess so its own argparse / click runs
    # cleanly with full sys.argv semantics. Pass through any extra args that
    # click collected beyond the named options.
    extra_args: list[str] = list(ctx.args)
    cmd = [sys.executable, "-m", resolved, *extra_args]
    result = subprocess.run(cmd, check=False)
    sys.exit(result.returncode)
