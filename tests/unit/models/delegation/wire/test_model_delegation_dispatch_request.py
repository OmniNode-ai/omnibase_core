# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""RED-first tests for ``ModelDelegationDispatchRequest`` (OMN-19838, Task A).

The request replaces the keyword arguments of the delegation dispatch call. Its
field set is every argument the consumer handler sends today, plus the
provider's ``output_schema_key``. The identity and the resolved execution budget
are required; every other field is an option with a default, so a provider that
does not know a newer option sees its default.
"""

from __future__ import annotations

import uuid

import pytest
from pydantic import ValidationError

from omnibase_core.models.delegation.wire import (
    EnumDelegationTrafficClass,
    ModelDelegationDispatchRequest,
    ModelDelegationProvenance,
)

pytestmark = pytest.mark.unit

_REQUIRED: dict[str, object] = {
    "prompt": "Summarize the diff.",
    "task_type": "research",
    "correlation_id": uuid.UUID("00000000-0000-4000-8000-000000000001"),
    "execution_timeout_seconds": 240,
    "terminal_delivery_margin_seconds": 60,
}


def test_every_field_the_call_site_sends_is_accepted() -> None:
    provenance = ModelDelegationProvenance(
        source="claude-code",
        traffic_class=EnumDelegationTrafficClass.ORGANIC,
    )
    request = ModelDelegationDispatchRequest(
        prompt="Summarize the diff.",
        task_type="research",
        correlation_id=uuid.UUID("00000000-0000-4000-8000-000000000002"),
        max_tokens=512,
        source_file_path="src/pkg/module.py",
        source_session_id="session-1",
        wait=False,
        execution_timeout_seconds=120,
        terminal_delivery_margin_seconds=30,
        quality_contract_mode="replace_task_class",
        acceptance_criteria=("names the changed files",),
        tenant_id="tenant-a",
        provenance=provenance,
        backend_id="backend-a",
        response_contract={"type": "object"},
        system_prompt="You are terse.",
        temperature=0.2,
        response_format={"type": "json_object"},
        no_escalation=True,
        output_schema_key="schema.v1",
    )

    assert request.prompt == "Summarize the diff."
    assert request.task_type == "research"
    assert request.max_tokens == 512
    assert request.source_file_path == "src/pkg/module.py"
    assert request.source_session_id == "session-1"
    assert request.wait is False
    assert request.execution_timeout_seconds == 120
    assert request.terminal_delivery_margin_seconds == 30
    assert request.quality_contract_mode == "replace_task_class"
    assert request.acceptance_criteria == ("names the changed files",)
    assert request.tenant_id == "tenant-a"
    assert request.provenance == provenance
    assert request.backend_id == "backend-a"
    assert request.response_contract == {"type": "object"}
    assert request.system_prompt == "You are terse."
    assert request.temperature == 0.2
    assert request.response_format == {"type": "json_object"}
    assert request.no_escalation is True
    assert request.output_schema_key == "schema.v1"


def test_every_option_has_its_default() -> None:
    request = ModelDelegationDispatchRequest.model_validate(_REQUIRED)

    assert request.max_tokens is None
    assert request.source_file_path is None
    assert request.source_session_id is None
    assert request.wait is True
    assert request.quality_contract_mode == "extend_task_class"
    assert request.acceptance_criteria == ()
    assert request.tenant_id is None
    assert request.provenance is None
    assert request.backend_id is None
    assert request.response_contract is None
    assert request.system_prompt is None
    assert request.temperature is None
    assert request.response_format is None
    assert request.no_escalation is False
    assert request.output_schema_key is None


@pytest.mark.parametrize("missing", sorted(_REQUIRED))
def test_identity_and_budget_are_required(missing: str) -> None:
    payload = {key: value for key, value in _REQUIRED.items() if key != missing}
    with pytest.raises(ValidationError):
        ModelDelegationDispatchRequest.model_validate(payload)


def test_an_unknown_field_is_rejected() -> None:
    with pytest.raises(ValidationError, match="extra_forbidden"):
        ModelDelegationDispatchRequest.model_validate(
            {**_REQUIRED, "not_a_dispatch_option": True}
        )


@pytest.mark.parametrize(
    "field", ["execution_timeout_seconds", "terminal_delivery_margin_seconds"]
)
def test_budget_seconds_must_be_positive(field: str) -> None:
    with pytest.raises(ValidationError):
        ModelDelegationDispatchRequest.model_validate({**_REQUIRED, field: 0})


def test_max_tokens_must_be_positive_when_set() -> None:
    with pytest.raises(ValidationError):
        ModelDelegationDispatchRequest.model_validate({**_REQUIRED, "max_tokens": 0})


def test_no_escalation_requires_a_backend_pin() -> None:
    with pytest.raises(ValidationError, match="backend_id"):
        ModelDelegationDispatchRequest.model_validate(
            {**_REQUIRED, "no_escalation": True}
        )


def test_request_is_frozen() -> None:
    request = ModelDelegationDispatchRequest.model_validate(_REQUIRED)
    with pytest.raises(ValidationError):
        request.prompt = "changed"
