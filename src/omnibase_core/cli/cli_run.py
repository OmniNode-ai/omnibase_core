# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""``onex run`` — execute an ONEX workflow locally, in-process (OMN-16677).

The packaged surface over the tier-0 local runtime harness (OMN-13420). Everything
here is flag parsing: the run itself is
:func:`omnibase_core.runtime.harness.harness_cli.run_harness_workflow`, which the
``python -m ...harness_cli`` shim also calls, so the two entry points cannot drift.

Not to be confused with ``onex run-node``, which dispatches a packaged node to a
remote runtime over Kafka. ``onex run`` needs no infrastructure at all.
"""

from __future__ import annotations

import click

from omnibase_core.runtime.harness.harness_cli import (
    WORKFLOW_DEFAULT_PROMPTS,
    run_harness_workflow,
)


@click.command("run")
@click.pass_context
@click.argument(
    "workflow",
    type=click.Choice(list(WORKFLOW_DEFAULT_PROMPTS), case_sensitive=False),
)
@click.option(
    "--prompt",
    default=None,
    help="Prompt to send. Defaults to the workflow's standard prompt.",
)
@click.option(
    "--correlation-id",
    default=None,
    help="Correlation UUID for this run. Defaults to a freshly generated one.",
)
@click.option(
    "--task-type",
    default="harness",
    show_default=True,
    help="Task-type tag recorded on the command.",
)
@click.option(
    "--max-tokens",
    type=int,
    default=512,
    show_default=True,
    help="Token ceiling passed to the inference adapter.",
)
@click.option(
    "--inference",
    type=click.Choice(["fixture", "curl"]),
    default="fixture",
    show_default=True,
    help=(
        "Inference adapter. fixture=replay a real-recorded completion "
        "(requires --fixture-completion), curl=live model via separate-binary LAN. "
        "There is no prompt-echo path."
    ),
)
@click.option(
    "--fixture-completion",
    default=None,
    help=(
        "Completion recorded from a real model call to replay (required for "
        "--inference=fixture). No prompt-echo / synthesized default."
    ),
)
@click.option("--endpoint", default=None, help="curl inference endpoint.")
@click.option(
    "--model",
    default="recorded-fixture",
    show_default=True,
    help="Model identifier recorded in the projection payload.",
)
@click.option(
    "--sqlite-path",
    default=":memory:",
    show_default=True,
    help="SQLite projection DB path (:memory: for ephemeral).",
)
@click.option(
    "--runtime-sha",
    default="unknown",
    show_default=True,
    help="Runtime SHA stamped into the evidence packet.",
)
def run(
    ctx: click.Context,
    workflow: str,
    prompt: str | None,
    correlation_id: str | None,
    task_type: str,
    max_tokens: int,
    inference: str,
    fixture_completion: str | None,
    endpoint: str | None,
    model: str,
    sqlite_path: str,
    runtime_sha: str,
) -> None:
    """Run an ONEX workflow on the local in-process runtime.

    Local counterpart of `onex run-node` (which dispatches to a remote runtime over
    Kafka): this command needs no Kafka, no Postgres and no LAN. It publishes a typed
    command on the in-memory bus, pumps it through the registered handlers to a
    terminal event, materializes a SQLite projection row, and prints a JSON evidence
    packet to stdout.

    Exits with the harness result's exit code.
    """
    exit_code = run_harness_workflow(
        workflow=workflow.lower(),
        prompt=prompt,
        correlation_id=correlation_id,
        task_type=task_type,
        max_tokens=max_tokens,
        inference=inference,
        fixture_completion=fixture_completion,
        endpoint=endpoint,
        model=model,
        sqlite_path=sqlite_path,
        runtime_sha=runtime_sha,
    )
    # Propagate the harness's own exit code, so a failed workflow is visible to the
    # shell (and to CI) rather than being flattened to success.
    ctx.exit(exit_code)


__all__ = ["run"]
