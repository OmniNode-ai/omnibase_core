# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Named tests ride the deployed delegation wire (OMN-17427).

The deployed lane could not grade a code answer on tests because the request
wire had nowhere to carry them and the gate input had nowhere to receive the
run. These tests pin the contract: the request carries the tests it names and
the sources they run from, the gate input carries the executed run, and a
request that names none keeps its wire shape exactly as it was.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from omnibase_core.models.delegation.wire import (
    ModelDelegationNamedTestRun,
    ModelDelegationNamedTests,
    ModelDelegationRequest,
    ModelQualityGateInput,
)

_CORRELATION = uuid.UUID("00000000-0000-0000-0000-000000017427")


def _tests(**kwargs: object) -> dict[str, object]:
    spec: dict[str, object] = {
        "test_ids": ["test_answer.py::test_adds"],
        "answer_path": "answer.py",
        "test_files": [
            {
                "path": "test_answer.py",
                "content": "from answer import add\n\ndef test_adds():\n    assert add(1, 2) == 3\n",
            }
        ],
    }
    spec.update(kwargs)
    return spec


def _request(**kwargs: object) -> ModelDelegationRequest:
    defaults: dict[str, object] = {
        "prompt": "write add",
        "task_type": "code_generation",
        "correlation_id": _CORRELATION,
        "emitted_at": datetime(2026, 10, 15, 3, 0, tzinfo=UTC),
    }
    defaults.update(kwargs)
    return ModelDelegationRequest.model_validate(defaults)


@pytest.mark.unit
def test_request_carries_named_tests_through_a_wire_round_trip() -> None:
    request = _request(named_tests=_tests())
    assert isinstance(request.named_tests, ModelDelegationNamedTests)
    dumped = request.model_dump(mode="json")
    assert dumped["named_tests"]["test_ids"] == ["test_answer.py::test_adds"]
    assert ModelDelegationRequest.model_validate(dumped) == request


@pytest.mark.unit
def test_request_naming_no_tests_keeps_its_wire_shape() -> None:
    dumped = _request().model_dump(mode="json")
    assert "named_tests" not in dumped


@pytest.mark.unit
@pytest.mark.parametrize(
    "override",
    [
        {"test_ids": []},
        {"test_ids": ["-k adds"]},
        {"test_ids": ["../test_answer.py::test_adds"]},
        {"test_ids": ["/etc/test_answer.py::test_adds"]},
        {"test_ids": [f"test_answer.py::t{n}" for n in range(21)]},
        {"answer_path": "../answer.py"},
        {"answer_path": "/tmp/answer.py"},
        {"answer_path": "test_answer.py"},
        {"test_files": []},
        {"test_files": [{"path": "../t.py", "content": "x"}]},
        {"test_files": [{"path": "/t.py", "content": "x"}]},
        {"test_files": [{"path": ".git/hooks/t.py", "content": "x"}]},
        {"test_files": [{"path": "t.py", "content": "x" * 200_001}]},
    ],
)
def test_unsafe_or_incomplete_named_tests_are_refused(
    override: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        _request(named_tests=_tests(**override))


@pytest.mark.unit
def test_named_tests_refuse_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        _request(named_tests=_tests(workspace_root="/srv/work"))


@pytest.mark.unit
def test_named_test_run_passed_needs_exit_zero_and_no_failures() -> None:
    ran = ModelDelegationNamedTestRun(test_ids=("a::t",), exit_code=0)
    failed = ModelDelegationNamedTestRun(
        test_ids=("a::t",), failed_test_ids=("a::t",), exit_code=1
    )
    assert ran.passed
    assert not failed.passed


@pytest.mark.unit
def test_named_test_run_refuses_a_failure_outside_the_named_tests() -> None:
    with pytest.raises(ValidationError):
        ModelDelegationNamedTestRun(
            test_ids=("a::t",), failed_test_ids=("b::t",), exit_code=1
        )


@pytest.mark.unit
def test_gate_input_carries_the_run_and_whether_tests_were_named() -> None:
    run = ModelDelegationNamedTestRun(test_ids=("a::t",), exit_code=0)
    gate_input = ModelQualityGateInput(
        correlation_id=_CORRELATION,
        task_type="code_generation",
        llm_response_content="def add(a, b):\n    return a + b\n",
        named_test_run=run,
        named_tests_requested=True,
    )
    dumped = gate_input.model_dump(mode="json")
    assert dumped["named_test_run"]["exit_code"] == 0
    assert dumped["named_tests_requested"] is True
    assert ModelQualityGateInput.model_validate(dumped) == gate_input


@pytest.mark.unit
def test_gate_input_without_a_run_keeps_its_wire_shape() -> None:
    dumped = ModelQualityGateInput(
        correlation_id=_CORRELATION,
        task_type="document",
        llm_response_content="x" * 80,
    ).model_dump(mode="json")
    assert "named_test_run" not in dumped
    assert "named_tests_requested" not in dumped
