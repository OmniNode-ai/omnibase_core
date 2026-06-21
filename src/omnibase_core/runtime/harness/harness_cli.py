# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""CLI for the core-resident local runtime harness (OMN-13420).

``delegation`` and ``sea`` subcommands mirror
``docs/evidence/2026-06-15-runtime-integration/publish_runtime_probe.py`` but run
fully in-process: no Kafka, no Postgres, no LAN. Each subcommand publishes a typed
command on the core in-memory bus, pumps it through the registered handlers to a
terminal event, materializes a SQLite projection row, and prints a JSON evidence
packet (runtime SHA + correlation ID + bus impl + projection backend + exit code).

Entry point::

    python -m omnibase_core.runtime.harness.harness_cli delegation --prompt "hello"
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from uuid import UUID, uuid4

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
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


def _build_adapter(args: argparse.Namespace) -> ProtocolHarnessInferenceAdapter:
    if args.inference == "curl":
        if not args.endpoint:
            raise ModelOnexError(
                message="--endpoint is required when --inference=curl",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )
        return CurlSubprocessInferenceAdapter(endpoint=args.endpoint, model=args.model)
    return RecordedFixtureInferenceAdapter(completion=args.fixture_completion)


def _run(args: argparse.Namespace) -> int:
    correlation_id = UUID(args.correlation_id) if args.correlation_id else uuid4()
    adapter = _build_adapter(args)
    store = SqliteProjectionStore(path=args.sqlite_path)
    try:
        result, projection = asyncio.run(
            run_workflow(
                workflow=args.workflow,
                prompt=args.prompt,
                correlation_id=correlation_id,
                task_type=args.task_type,
                max_tokens=args.max_tokens,
                adapter=adapter,
                store=store,
            )
        )
        packet = build_evidence_packet(
            workflow=args.workflow,
            result=result,
            projection=projection,
            adapter=adapter,
            store=store,
            bus_impl="EventBusInmemory",
            runtime_sha=args.runtime_sha,
        )
        # print-ok: CLI emits the evidence packet to stdout (the durable proof artifact)
        print(json.dumps(packet, default=str, indent=2), flush=True)
        return result.exit_code
    finally:
        store.close()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="harness",
        description="Core-resident infra-free local runtime harness (OMN-13420).",
    )
    sub = parser.add_subparsers(dest="workflow", required=True)
    for workflow, default_prompt in (
        ("delegation", "summarize the local-first runtime re-convergence"),
        ("sea", "generate a COMPUTE node that uppercases its input"),
    ):
        sp = sub.add_parser(workflow, help=f"Run the {workflow} workflow in-process.")
        sp.add_argument("--prompt", default=default_prompt)
        sp.add_argument("--correlation-id", default=None, dest="correlation_id")
        sp.add_argument("--task-type", default="harness", dest="task_type")
        sp.add_argument("--max-tokens", type=int, default=512, dest="max_tokens")
        sp.add_argument(
            "--inference",
            choices=("fixture", "curl"),
            default="fixture",
            help="Inference adapter (fixture=offline, curl=separate-binary LAN).",
        )
        sp.add_argument("--fixture-completion", default=None, dest="fixture_completion")
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
    """CLI entry point. Returns a process exit code."""
    args = _parser().parse_args(argv)
    return _run(args)


if __name__ == "__main__":
    sys.exit(main())


__all__ = ["build_evidence_packet", "main", "run_workflow"]
