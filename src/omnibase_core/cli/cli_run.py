# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""``onex run`` — execute a contract-declared workflow on the local runtime."""

from __future__ import annotations

import sys
from pathlib import Path

import click

from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.runtime.runtime_local import (
    RuntimeLocal,
    parse_backend_overrides,
)


@click.command("run")
@click.argument("workflow_path", type=click.Path(path_type=Path))
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
def run_workflow(
    workflow_path: Path,
    state_root: str,
    backend: tuple[str, ...],
    timeout: int,
) -> None:
    """Run a contract-declared workflow on the local runtime.

    WORKFLOW_PATH is the path to a workflow contract YAML file. The contract
    must declare a ``terminal_event`` topic that signals workflow completion.

    \b
    Exit codes:
        0  COMPLETED — terminal event received, evidence written
        1  FAILED / TIMEOUT — terminal event with failure or timeout exceeded
        2  PARTIAL — evidence written but no terminal event

    \b
    Examples:
        onex run workflow.yaml
        onex run workflow.yaml --timeout 60
        onex run workflow.yaml --backend event_bus=inmemory --state-root ./state
    """
    # Validate workflow path exists
    if not workflow_path.exists():
        click.echo(f"Error: Workflow contract not found: {workflow_path}", err=True)
        sys.exit(1)

    # Validate backend overrides
    try:
        backend_overrides = parse_backend_overrides(backend)
    except ModelOnexError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    runtime = RuntimeLocal(
        workflow_path=workflow_path,
        state_root=Path(state_root),
        backend_overrides=backend_overrides,
        timeout=timeout,
    )

    runtime.run()
    sys.exit(runtime.exit_code)
