# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The handler-shape fixture set on a live broker through an overlay, observed by a run-id consumer (OMN-21536, KC-c).

Run on a lab host with ``--validator-runtime-overlay`` naming the overlay file; the
launch is otherwise the same as the in-memory case. The runtime runs as a child process
with ``--overlay``; this test consumes the run-event topic through the bus the same
overlay binds, filters by the run id the report carries, and compares the report to the
committed golden report after normalising run id and timestamps.
"""

from __future__ import annotations

import asyncio
import json
import shutil
import sys
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Protocol, cast

import pytest

from omnibase_core.models.event_bus.model_event_message import ModelEventMessage
from omnibase_core.models.validation.model_validator_run_event import (
    ModelValidatorRunEvent,
)
from omnibase_core.nodes.node_validation_report_write_effect import (
    runtime_validator_run,
)
from omnibase_core.nodes.node_validation_report_write_effect.handler_validator_runtime_overlay import (
    HandlerValidatorRuntimeOverlay,
)
from omnibase_core.validation.validator_handler_shape import ValidatorHandlerShape

pytestmark = pytest.mark.integration

_ROOT = Path(__file__).resolve().parents[4]
_FIXTURES = _ROOT / "tests/fixtures/validation/handler_shape"
_GOLDEN = _FIXTURES / "golden_handler_shape.json"
_CONSUMER_GROUP = "validator-runtime-lab-consumer"
_WAIT_SECONDS = 30.0


class _Consumer(Protocol):
    """The consuming half of the bus the overlay binds."""

    async def start(self) -> None: ...

    async def subscribe(
        self,
        topic: str,
        *,
        on_message: Callable[[ModelEventMessage], Awaitable[None]],
        group_id: str,
    ) -> object: ...

    async def close(self) -> None: ...


def _stage(work: Path) -> list[Path]:
    """The ticket's fixture set: every planted violation, under a handler module name."""
    for fixture in sorted(_FIXTURES.glob("violation_*.py")):
        shutil.copy(
            fixture, work / f"handler_{fixture.name.removeprefix('violation_')}"
        )
    return sorted(work.glob("handler_*.py"))


async def _observe(overlay_path: Path, report: Path, work: Path) -> list[str]:
    handler = HandlerValidatorRuntimeOverlay()
    bus = cast(_Consumer, handler.construct_bus(handler.load(overlay_path)))
    run_topic = handler.settings().run_topic
    seen: list[str] = []

    async def _record(message: ModelEventMessage) -> None:
        seen.append(
            ModelValidatorRunEvent.model_validate_json(message.value).report_ref
        )

    await bus.start()
    try:
        await bus.subscribe(run_topic, on_message=_record, group_id=_CONSUMER_GROUP)
        child = await asyncio.create_subprocess_exec(
            sys.executable,
            "-m",
            runtime_validator_run.__name__,
            f"{ValidatorHandlerShape.__module__}:{ValidatorHandlerShape.__name__}",
            *(str(target) for target in _stage(work)),
            "--report-json",
            str(report),
            "--overlay",
            str(overlay_path),
            cwd=work,
        )
        assert await child.wait() == 1
        run_id = json.loads(report.read_text(encoding="utf-8"))["report_id"]
        deadline = asyncio.get_running_loop().time() + _WAIT_SECONDS
        while run_id not in seen and asyncio.get_running_loop().time() < deadline:
            await asyncio.sleep(0.2)
        return [ref for ref in seen if ref == run_id]
    finally:
        await bus.close()


def test_the_overlay_run_matches_the_golden_report_and_one_run_event_arrives(
    tmp_path: Path, overlay_under_test: Path
) -> None:
    overlay_path = overlay_under_test
    report = tmp_path / "report.json"

    work = tmp_path / "work"
    work.mkdir()
    matching = asyncio.run(_observe(overlay_path, report, work))

    written = json.loads(report.read_text(encoding="utf-8"))
    assert matching == [written["report_id"]]
    written["report_id"] = "<normalised>"
    written["provenance"]["generated_at"] = "<normalised>"
    assert written == cast(dict[str, object], json.loads(_GOLDEN.read_text("utf-8")))
