# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for ``onex run`` — the packaged CLI surface over the tier-0 local harness.

OMN-16677. The infra-free local runtime harness (OMN-13420) was previously reachable
only as ``python -m omnibase_core.runtime.harness.harness_cli <workflow>``. These tests
pin the packaged ``onex run`` surface, the evidence-packet contract it prints, the
OMN-13496 false-green negative control, and the fact that the ``python -m`` module
entry point still routes through the *same* shared callable rather than a copy.
"""

from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from click.testing import CliRunner, Result

from omnibase_core.cli.cli_commands import cli
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.runtime.harness.model_harness_result import ModelHarnessResult
from omnibase_core.models.runtime.harness.model_projection_row import ModelProjectionRow
from omnibase_core.protocols.runtime.protocol_harness_inference_adapter import (
    ProtocolHarnessInferenceAdapter,
)
from omnibase_core.runtime.harness import harness_cli
from omnibase_core.runtime.harness.harness_projection_store_sqlite import (
    SqliteProjectionStore,
)

pytestmark = pytest.mark.unit

# Completions standing in for ones recorded from a real model call (golden-chain
# replay). The harness refuses to run fixture inference without one.
RECORDED_DELEGATION_COMPLETION = (
    "Local-first re-convergence runs the runtime in-process, with no broker."
)
RECORDED_SEA_COMPLETION = "def handle(request: ModelIn) -> ModelOut: ..."


def _invoke_run(
    workflow: str,
    *,
    sqlite_path: Path,
    completion: str | None,
    extra: list[str] | None = None,
) -> Result:
    """Invoke ``onex run <workflow>`` through the packaged click group."""
    args = [
        "run",
        workflow,
        "--inference",
        "fixture",
        "--sqlite-path",
        str(sqlite_path),
    ]
    if completion is not None:
        args += ["--fixture-completion", completion]
    if extra:
        args += extra
    return CliRunner().invoke(cli, args)


def _packet(
    result: Result,
) -> dict[str, object]:  # dict-str-any-ok: JSON evidence packet
    """Parse the evidence packet the command prints to stdout."""
    payload = json.loads(result.output)
    assert isinstance(payload, dict)
    return payload


def _spy_on_run_workflow(
    monkeypatch: pytest.MonkeyPatch,
    captured: dict[str, object],  # dict-str-any-ok: test spy record
) -> None:
    """Record the arguments the CLI hands the harness, then run it for real.

    Prompt, task type and token ceiling do not appear in the evidence packet, so a
    spy is the only way to prove they are forwarded rather than silently dropped.
    """
    real_run_workflow = harness_cli.run_workflow

    async def _spy(
        *,
        workflow: str,
        prompt: str,
        correlation_id: UUID,
        task_type: str,
        max_tokens: int,
        adapter: ProtocolHarnessInferenceAdapter,
        store: SqliteProjectionStore,
    ) -> tuple[ModelHarnessResult, ModelProjectionRow | None]:
        captured.update(
            {
                "workflow": workflow,
                "prompt": prompt,
                "correlation_id": correlation_id,
                "task_type": task_type,
                "max_tokens": max_tokens,
            }
        )
        return await real_run_workflow(
            workflow=workflow,
            prompt=prompt,
            correlation_id=correlation_id,
            task_type=task_type,
            max_tokens=max_tokens,
            adapter=adapter,
            store=store,
        )

    monkeypatch.setattr(harness_cli, "run_workflow", _spy)


@pytest.mark.parametrize(
    ("workflow", "completion"),
    [
        ("delegation", RECORDED_DELEGATION_COMPLETION),
        ("sea", RECORDED_SEA_COMPLETION),
    ],
)
def test_onex_run_emits_infra_free_evidence_packet(
    workflow: str, completion: str, tmp_path: Path
) -> None:
    """``onex run <workflow>`` exits 0 and prints an infra-free evidence packet."""
    result = _invoke_run(
        workflow, sqlite_path=tmp_path / "projection.db", completion=completion
    )

    assert result.exit_code == 0, result.output
    packet = _packet(result)
    assert packet["workflow"] == workflow
    assert packet["bus_impl"] == "EventBusInmemory"
    assert packet["infra_free"] is True
    assert packet["inference_adapter"] == "fixture"
    assert packet["terminal_status"] == "success"
    assert packet["exit_code"] == 0

    # The projection row is the durable half of the proof — it must carry the
    # replayed completion, not a synthesized echo.
    row = packet["projection_row"]
    assert isinstance(row, dict)
    assert row["workflow"] == workflow
    assert row["payload"]["completion"] == completion


def test_onex_run_defaults_sqlite_path_to_memory(tmp_path: Path) -> None:
    """With no ``--sqlite-path`` the projection store is the ephemeral in-memory DB."""
    result = CliRunner().invoke(
        cli,
        [
            "run",
            "delegation",
            "--inference",
            "fixture",
            "--fixture-completion",
            RECORDED_DELEGATION_COMPLETION,
        ],
    )

    assert result.exit_code == 0, result.output
    assert _packet(result)["projection_backend"] == "sqlite::memory:"
    # No stray DB file was created on disk.
    assert not list(tmp_path.glob("*.db"))


def test_onex_run_fixture_without_completion_is_a_validation_error(
    tmp_path: Path,
) -> None:
    """OMN-13496 negative control: fixture inference with nothing recorded must fail.

    A fixture run with no recorded completion would report success on nothing. The
    packaged surface must preserve that refusal, not soften it into a default.
    """
    result = _invoke_run(
        "delegation", sqlite_path=tmp_path / "projection.db", completion=None
    )

    assert result.exit_code != 0
    assert isinstance(result.exception, ModelOnexError)
    assert result.exception.error_code == EnumCoreErrorCode.VALIDATION_ERROR
    assert "--fixture-completion is required" in str(result.exception)


def test_onex_run_blank_fixture_completion_is_a_validation_error(
    tmp_path: Path,
) -> None:
    """A whitespace-only completion is refused too — it replays nothing."""
    result = _invoke_run(
        "delegation", sqlite_path=tmp_path / "projection.db", completion="   "
    )

    assert result.exit_code != 0
    assert isinstance(result.exception, ModelOnexError)
    assert result.exception.error_code == EnumCoreErrorCode.VALIDATION_ERROR


def test_onex_run_curl_without_endpoint_is_a_validation_error(tmp_path: Path) -> None:
    """``--inference curl`` still requires an explicit ``--endpoint``."""
    result = CliRunner().invoke(
        cli,
        [
            "run",
            "delegation",
            "--inference",
            "curl",
            "--sqlite-path",
            str(tmp_path / "projection.db"),
        ],
    )

    assert result.exit_code != 0
    assert isinstance(result.exception, ModelOnexError)
    assert result.exception.error_code == EnumCoreErrorCode.VALIDATION_ERROR
    assert "--endpoint is required" in str(result.exception)


def test_onex_run_honors_an_explicit_correlation_id(tmp_path: Path) -> None:
    """A caller-supplied correlation ID flows into the packet and the projection."""
    correlation_id = uuid4()
    result = _invoke_run(
        "delegation",
        sqlite_path=tmp_path / "projection.db",
        completion=RECORDED_DELEGATION_COMPLETION,
        extra=["--correlation-id", str(correlation_id)],
    )

    assert result.exit_code == 0, result.output
    packet = _packet(result)
    assert packet["correlation_id"] == str(correlation_id)
    row = packet["projection_row"]
    assert isinstance(row, dict)
    assert row["correlation_id"] == str(correlation_id)


def test_onex_run_rejects_a_non_uuid_correlation_id(tmp_path: Path) -> None:
    """Correlation IDs stay UUID-only — a free-form string is refused, not coerced."""
    result = _invoke_run(
        "delegation",
        sqlite_path=tmp_path / "projection.db",
        completion=RECORDED_DELEGATION_COMPLETION,
        extra=["--correlation-id", "not-a-uuid"],
    )

    assert result.exit_code != 0
    assert isinstance(result.exception, ValueError)


def test_onex_run_generates_a_correlation_id_when_omitted(tmp_path: Path) -> None:
    """Omitting ``--correlation-id`` mints a fresh UUID rather than failing."""
    result = _invoke_run(
        "delegation",
        sqlite_path=tmp_path / "projection.db",
        completion=RECORDED_DELEGATION_COMPLETION,
    )

    assert result.exit_code == 0, result.output
    # Raises if the emitted correlation ID is not a well-formed UUID.
    UUID(str(_packet(result)["correlation_id"]))


def test_onex_run_forwards_prompt_task_type_and_max_tokens(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The passthrough options reach the harness rather than being dropped."""
    captured: dict[str, object] = {}  # dict-str-any-ok: test spy record
    _spy_on_run_workflow(monkeypatch, captured)

    result = CliRunner().invoke(
        cli,
        [
            "run",
            "delegation",
            "--inference",
            "fixture",
            "--fixture-completion",
            RECORDED_DELEGATION_COMPLETION,
            "--sqlite-path",
            str(tmp_path / "projection.db"),
            "--prompt",
            "explain the tier-0 harness",
            "--task-type",
            "review",
            "--max-tokens",
            "128",
        ],
    )

    assert result.exit_code == 0, result.output
    assert captured["prompt"] == "explain the tier-0 harness"
    assert captured["task_type"] == "review"
    assert captured["max_tokens"] == 128


def test_onex_run_uses_the_per_workflow_default_prompt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Omitting ``--prompt`` falls back to the workflow's documented default."""
    captured: dict[str, object] = {}  # dict-str-any-ok: test spy record
    _spy_on_run_workflow(monkeypatch, captured)

    result = CliRunner().invoke(
        cli,
        [
            "run",
            "sea",
            "--inference",
            "fixture",
            "--fixture-completion",
            RECORDED_SEA_COMPLETION,
            "--sqlite-path",
            str(tmp_path / "projection.db"),
        ],
    )

    assert result.exit_code == 0, result.output
    assert captured["prompt"] == harness_cli.WORKFLOW_DEFAULT_PROMPTS["sea"]


def test_onex_run_rejects_an_unknown_workflow() -> None:
    """Only the declared workflows are accepted; click rejects anything else."""
    result = CliRunner().invoke(cli, ["run", "not-a-workflow"])

    assert result.exit_code != 0
    assert "not-a-workflow" in result.output


def test_onex_run_is_registered_alongside_run_node() -> None:
    """``run`` is a distinct command from the pre-existing ``run-node``."""
    assert "run" in cli.commands
    assert "run-node" in cli.commands
    assert cli.commands["run"] is not cli.commands["run-node"]


def test_run_and_run_node_help_distinguish_local_from_remote() -> None:
    """Each command's help says which runtime it targets, so they are not confusable."""
    runner = CliRunner()

    run_help = runner.invoke(cli, ["run", "--help"]).output
    assert "local" in run_help.lower()
    assert "run-node" in run_help

    run_node_help = runner.invoke(cli, ["run-node", "--help"]).output
    assert "kafka" in run_node_help.lower()
    assert "onex run" in run_node_help


def test_module_entry_point_still_runs_end_to_end(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """``python -m ...harness_cli`` keeps working, unchanged, with no mocking."""
    exit_code = harness_cli.main(
        [
            "delegation",
            "--inference",
            "fixture",
            "--fixture-completion",
            RECORDED_DELEGATION_COMPLETION,
            "--sqlite-path",
            str(tmp_path / "projection.db"),
        ]
    )

    assert exit_code == 0
    packet = json.loads(capsys.readouterr().out)
    assert packet["workflow"] == "delegation"
    assert packet["bus_impl"] == "EventBusInmemory"
    assert packet["infra_free"] is True


def test_module_entry_point_routes_through_the_shared_callable(tmp_path: Path) -> None:
    """The module path is a thin shim over the callable the click command uses.

    Both entry points must land on one implementation, so behavior cannot drift
    between ``onex run`` and ``python -m ...harness_cli``.
    """
    calls: list[dict[str, object]] = []  # dict-str-any-ok: test spy record

    def _fake(**kwargs: object) -> int:
        calls.append(dict(kwargs))
        return 0

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(harness_cli, "run_harness_workflow", _fake)
        exit_code = harness_cli.main(
            [
                "sea",
                "--inference",
                "fixture",
                "--fixture-completion",
                RECORDED_SEA_COMPLETION,
                "--sqlite-path",
                str(tmp_path / "projection.db"),
                "--runtime-sha",
                "abc123",
            ]
        )

    assert exit_code == 0
    assert len(calls) == 1
    assert calls[0] == {
        "workflow": "sea",
        "prompt": None,
        "correlation_id": None,
        "task_type": "harness",
        "max_tokens": 512,
        "inference": "fixture",
        "fixture_completion": RECORDED_SEA_COMPLETION,
        "endpoint": None,
        "model": "recorded-fixture",
        "sqlite_path": str(tmp_path / "projection.db"),
        "runtime_sha": "abc123",
    }
