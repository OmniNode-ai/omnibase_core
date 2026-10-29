# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Runtime tests of the generic validator format: the report writer comes from the container.

The checker is pure and the validator reads; the runtime resolves the report-writing
EFFECT from the container with ``get_service(NodeValidationReportWriteEffect)`` and never builds it. A container spy
records the resolution, a second composition injects a different writer with no code
change, and both reports equal the committed golden report once the run id and the
timestamps are normalised.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import cast

import pytest

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.handlers.handler_validator_run import (
    build_validator_container,
    main,
    run_validator,
)
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.nodes.validation_report_write.model_validation_report_write_input import (
    ModelValidationReportWriteInput,
)
from omnibase_core.models.nodes.validation_report_write.model_validation_report_write_output import (
    ModelValidationReportWriteOutput,
)
from omnibase_core.nodes.node_validation_report_write_effect.handler import (
    NodeValidationReportWriteEffect,
)
from omnibase_core.validation.validator_hook_writes import ValidatorHookWrites

pytestmark = pytest.mark.unit

_ROOT = Path(__file__).resolve().parents[3]
_FIXTURES = _ROOT / "tests/fixtures/validation/hook_writes"
_PLANTED = _FIXTURES / "violation_hook_writes_fix_flag.yaml"
_GOLDEN = _FIXTURES / "golden_hook_writes_fix_flag.json"
_NORMALISED = "<normalised>"


class _SpyContainer:
    """Records every type resolved through ``get_service`` and delegates to a container."""

    def __init__(self, inner: ModelONEXContainer) -> None:
        self._inner = inner
        self.resolved: list[type] = []

    def get_service(
        self, protocol_type: type, service_name: str | None = None
    ) -> object:
        self.resolved.append(protocol_type)
        return self._inner.get_service(protocol_type, service_name)


class _RecordingWriter(NodeValidationReportWriteEffect):
    """A different injected writer: the composition changes, the runtime does not."""

    def __init__(self) -> None:
        self.requests: list[ModelValidationReportWriteInput] = []

    def handle(
        self, request: ModelValidationReportWriteInput
    ) -> ModelValidationReportWriteOutput:
        self.requests.append(request)
        return super().handle(request)


def _normalise(report: dict[str, object]) -> dict[str, object]:
    report["report_id"] = _NORMALISED
    provenance = cast(dict[str, object], report["provenance"])
    provenance["generated_at"] = _NORMALISED
    return report


def _written(path: Path) -> dict[str, object]:
    return _normalise(json.loads(path.read_text(encoding="utf-8")))


def test_runtime_resolves_the_report_writer_from_the_container(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(_ROOT)
    spy = _SpyContainer(build_validator_container())
    report_path = tmp_path / "report.json"
    result = run_validator(
        cast(ModelONEXContainer, spy),
        ValidatorHookWrites(),
        [_PLANTED],
        str(report_path),
    )
    assert not result.is_valid
    assert spy.resolved == [NodeValidationReportWriteEffect]
    assert _written(report_path) == json.loads(_GOLDEN.read_text(encoding="utf-8"))


def test_a_different_injected_writer_gives_the_same_report_with_no_code_change(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(_ROOT)
    writer = _RecordingWriter()
    container = ModelONEXContainer(enable_service_registry=True)
    asyncio.run(
        container.service_registry.register_instance(
            interface=NodeValidationReportWriteEffect, instance=writer
        )
    )
    report_path = tmp_path / "report.json"
    run_validator(container, ValidatorHookWrites(), [_PLANTED], str(report_path))
    assert len(writer.requests) == 1
    assert _written(report_path) == json.loads(_GOLDEN.read_text(encoding="utf-8"))


def test_no_report_path_resolves_no_writer(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(_ROOT)
    spy = _SpyContainer(build_validator_container())
    run_validator(
        cast(ModelONEXContainer, spy), ValidatorHookWrites(), [_PLANTED], None
    )
    assert spy.resolved == []


def test_a_report_path_without_a_container_is_an_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(_ROOT)
    with pytest.raises(ModelOnexError, match="needs a container"):
        run_validator(
            None, ValidatorHookWrites(), [_PLANTED], str(tmp_path / "report.json")
        )


def test_main_exits_one_on_a_planted_violation_and_zero_on_a_clean_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(_ROOT)
    report_path = tmp_path / "report.json"
    refused = main(
        ValidatorHookWrites,
        [str(_PLANTED), "--report-json", str(report_path)],
        build_validator_container,
    )
    clean = main(
        ValidatorHookWrites,
        [str(_FIXTURES / "clean_hook_writes_fix_flag.yaml")],
        build_validator_container,
    )
    assert (refused, clean) == (1, 0)
    assert _written(report_path)["overall_status"] == "FAIL"
