# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""CLI for the core-resident local runtime harness (OMN-13420).

``delegation`` and ``sea`` subcommands mirror
``docs/evidence/2026-06-15-runtime-integration/publish_runtime_probe.py`` but run
fully in-process: no Kafka, no Postgres, no LAN. Each subcommand publishes a typed
command on the core in-memory bus, pumps it through the registered handlers to a
terminal event, materializes a SQLite projection row, and prints a JSON evidence
packet (runtime SHA + correlation ID + bus impl + projection backend + exit code).

Entry points::

    onex run delegation --prompt "hello"
    python -m omnibase_core.runtime.harness.harness_cli delegation --prompt "hello"

``onex run`` (:mod:`omnibase_core.cli.cli_run`) is the packaged surface and the one
to document; the ``python -m`` module path is a thin argparse shim retained for
existing scripted callers. Both parse their own flags and then hand off to
:func:`run_harness_workflow`, which is the single implementation of the run — there
is no second copy of this logic to drift.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from uuid import UUID, uuid4

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope
from omnibase_core.models.runtime.harness.model_harness_command import (
    ModelHarnessCommand,
)
from omnibase_core.models.runtime.harness.model_harness_result import ModelHarnessResult
from omnibase_core.models.runtime.harness.model_projection_row import ModelProjectionRow
from omnibase_core.protocols.runtime.protocol_harness_inference_adapter import (
    ProtocolHarnessInferenceAdapter,
)
from omnibase_core.runtime.harness.harness_builder import build_workflow
from omnibase_core.runtime.harness.harness_inference_curl import (
    CurlSubprocessInferenceAdapter,
)
from omnibase_core.runtime.harness.harness_inference_fixture import (
    RecordedFixtureInferenceAdapter,
)
from omnibase_core.runtime.harness.harness_projection_store_sqlite import (
    SqliteProjectionStore,
)

# The workflows the harness can run, each with the default prompt used when the
# caller supplies none. Both entry points read this map, so the accepted workflow
# names and their defaults cannot drift apart.
WORKFLOW_DEFAULT_PROMPTS: dict[str, str] = {
    "delegation": "summarize the local-first runtime re-convergence",
    "sea": "generate a COMPUTE node that uppercases its input",
}


async def run_workflow(
    *,
    workflow: str,
    prompt: str,
    correlation_id: UUID,
    task_type: str,
    max_tokens: int,
    adapter: ProtocolHarnessInferenceAdapter,
    store: SqliteProjectionStore,
) -> tuple[ModelHarnessResult, ModelProjectionRow | None]:
    """Run one harness workflow end-to-end and return (result, projection row)."""
    harness, cmd_topic = build_workflow(workflow=workflow, adapter=adapter, store=store)
    command = ModelHarnessCommand(
        correlation_id=correlation_id,
        workflow=workflow,
        prompt=prompt,
        task_type=task_type,
        max_tokens=max_tokens,
    )
    envelope: ModelEventEnvelope[ModelHarnessCommand] = ModelEventEnvelope(
        payload=command,
        correlation_id=correlation_id,
        event_type=cmd_topic,
        payload_type="ModelHarnessCommand",
        source_tool="harness-cli",
    )
    envelope.metadata.tags["message_category"] = "command"
    result = await harness.run(command_topic=cmd_topic, command_envelope=envelope)
    projection = store.read(correlation_id)
    return result, projection


def build_evidence_packet(
    *,
    workflow: str,
    result: ModelHarnessResult,
    projection: ModelProjectionRow | None,
    adapter: ProtocolHarnessInferenceAdapter,
    store: SqliteProjectionStore,
    bus_impl: str,
    runtime_sha: str,
) -> dict[str, object]:  # dict-str-any-ok: JSON evidence packet
    """Assemble the durable evidence packet for an infra-free harness run."""
    return {
        "ticket": "OMN-13420",
        "workflow": workflow,
        "runtime_sha": runtime_sha,
        "correlation_id": str(result.correlation_id),
        "bus_impl": bus_impl,
        "inference_adapter": adapter.adapter_id,
        "projection_backend": store.backend,
        "terminal_topic": result.terminal_topic,
        "terminal_status": result.status,
        "emitted_topics": list(result.emitted_topics),
        "projection_row": (
            json.loads(projection.model_dump_json()) if projection else None
        ),
        "infra_free": True,
        "exit_code": result.exit_code,
    }


def build_inference_adapter(
    *,
    inference: str,
    fixture_completion: str | None,
    endpoint: str | None,
    model: str,
) -> ProtocolHarnessInferenceAdapter:
    """Select the inference adapter for a run, refusing under-specified combinations."""
    if inference == "curl":
        if not endpoint:
            raise ModelOnexError(
                message="--endpoint is required when --inference=curl",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )
        return CurlSubprocessInferenceAdapter(endpoint=endpoint, model=model)
    # fixture replays a completion recorded from a real model call. There is no
    # prompt-echo default: a run with no real or recorded inference must FAIL,
    # never report success on nothing (OMN-13496).
    if not fixture_completion or not fixture_completion.strip():
        raise ModelOnexError(
            message=(
                "--fixture-completion is required when --inference=fixture; it must "
                "be a completion recorded from a real model call (golden-chain "
                "replay). Use --inference=curl for a live model. A fixture run with "
                "no recorded completion is a false-green stub (OMN-13496)."
            ),
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        )
    return RecordedFixtureInferenceAdapter(completion=fixture_completion)


def run_harness_workflow(
    *,
    workflow: str,
    prompt: str | None = None,
    correlation_id: str | None = None,
    task_type: str = "harness",
    max_tokens: int = 512,
    inference: str = "fixture",
    fixture_completion: str | None = None,
    endpoint: str | None = None,
    model: str = "recorded-fixture",
    sqlite_path: str = ":memory:",
    runtime_sha: str = "unknown",
) -> int:
    """Run one harness workflow, print its evidence packet, and return the exit code.

    This is the single implementation behind both entry points: the packaged
    ``onex run`` click command and the ``python -m ...harness_cli`` argparse shim.
    Each of those only parses flags; all behavior lives here.

    Args:
        workflow: Workflow to run; a key of :data:`WORKFLOW_DEFAULT_PROMPTS`.
        prompt: Prompt to send. ``None`` selects the workflow's default prompt.
        correlation_id: Correlation UUID as a string. ``None`` mints a fresh one.
        task_type: Task-type tag recorded on the command.
        max_tokens: Token ceiling passed to the inference adapter.
        inference: ``"fixture"`` to replay a recorded completion, ``"curl"`` for a
            live model over the LAN.
        fixture_completion: Recorded completion to replay; required for fixture runs.
        endpoint: Inference endpoint; required for curl runs.
        model: Model identifier recorded in the projection payload.
        sqlite_path: Projection DB path; ``":memory:"`` for an ephemeral store.
        runtime_sha: Runtime SHA stamped into the evidence packet.

    Returns:
        The harness result's process exit code.

    Raises:
        ModelOnexError: If the inference options are under-specified.
        ValueError: If ``correlation_id`` is not a well-formed UUID.
    """
    resolved_prompt = (
        prompt if prompt is not None else WORKFLOW_DEFAULT_PROMPTS[workflow]
    )
    resolved_correlation_id = UUID(correlation_id) if correlation_id else uuid4()
    adapter = build_inference_adapter(
        inference=inference,
        fixture_completion=fixture_completion,
        endpoint=endpoint,
        model=model,
    )
    store = SqliteProjectionStore(path=sqlite_path)
    try:
        result, projection = asyncio.run(
            run_workflow(
                workflow=workflow,
                prompt=resolved_prompt,
                correlation_id=resolved_correlation_id,
                task_type=task_type,
                max_tokens=max_tokens,
                adapter=adapter,
                store=store,
            )
        )
        packet = build_evidence_packet(
            workflow=workflow,
            result=result,
            projection=projection,
            adapter=adapter,
            store=store,
            bus_impl="EventBusInmemory",
            runtime_sha=runtime_sha,
        )
        # print-ok: CLI emits the evidence packet to stdout (the durable proof artifact)
        print(json.dumps(packet, default=str, indent=2), flush=True)
        return result.exit_code
    finally:
        store.close()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="harness",
        description=(
            "Core-resident infra-free local runtime harness (OMN-13420). "
            "`onex run` is the packaged equivalent of this command."
        ),
    )
    sub = parser.add_subparsers(dest="workflow", required=True)
    for workflow, default_prompt in WORKFLOW_DEFAULT_PROMPTS.items():
        sp = sub.add_parser(workflow, help=f"Run the {workflow} workflow in-process.")
        sp.add_argument(
            "--prompt",
            default=None,
            help=f"Prompt to send. Default: {default_prompt!r}",
        )
        sp.add_argument("--correlation-id", default=None, dest="correlation_id")
        sp.add_argument("--task-type", default="harness", dest="task_type")
        sp.add_argument("--max-tokens", type=int, default=512, dest="max_tokens")
        sp.add_argument(
            "--inference",
            choices=("fixture", "curl"),
            default="fixture",
            help=(
                "Inference adapter. fixture=replay a real-recorded completion "
                "(requires --fixture-completion), curl=live model via separate-binary "
                "LAN. There is no prompt-echo path."
            ),
        )
        sp.add_argument(
            "--fixture-completion",
            default=None,
            dest="fixture_completion",
            help=(
                "Completion recorded from a real model call to replay (required for "
                "--inference=fixture). No prompt-echo / synthesized default."
            ),
        )
        sp.add_argument("--endpoint", default=None, help="curl inference endpoint.")
        sp.add_argument("--model", default="recorded-fixture")
        sp.add_argument(
            "--sqlite-path",
            default=":memory:",
            dest="sqlite_path",
            help="SQLite projection DB path (:memory: for ephemeral).",
        )
        sp.add_argument("--runtime-sha", default="unknown", dest="runtime_sha")
    return parser


def main(argv: list[str] | None = None) -> int:
    """``python -m`` entry point: parse argv, then defer to the shared callable.

    Kept as a thin shim so existing scripted callers keep working. ``onex run`` is
    the packaged surface; both land on :func:`run_harness_workflow`.
    """
    args = _parser().parse_args(argv)
    return run_harness_workflow(
        workflow=args.workflow,
        prompt=args.prompt,
        correlation_id=args.correlation_id,
        task_type=args.task_type,
        max_tokens=args.max_tokens,
        inference=args.inference,
        fixture_completion=args.fixture_completion,
        endpoint=args.endpoint,
        model=args.model,
        sqlite_path=args.sqlite_path,
        runtime_sha=args.runtime_sha,
    )


if __name__ == "__main__":
    sys.exit(main())


__all__ = [
    "WORKFLOW_DEFAULT_PROMPTS",
    "build_evidence_packet",
    "build_inference_adapter",
    "main",
    "run_harness_workflow",
    "run_workflow",
]
