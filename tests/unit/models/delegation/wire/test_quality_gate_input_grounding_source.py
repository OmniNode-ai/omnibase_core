# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""The quality gate input can carry the text a response was derived from.

The delegation quality gate grounds identifiers and numbers in a response
against the input the response was derived from. On the bus path that input
never reached the gate: this model had no field for it, so every grounding
check was recorded as skipped and a response citing numbers its input does not
contain still scored 1.0. The field is optional and omitted from the serialised
payload when unset, so a producer that predates it emits a byte-identical
payload and this release can be deployed as the consumer before any producer
stamps it.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.models.delegation.wire import ModelQualityGateInput


def _input(**overrides: object) -> ModelQualityGateInput:
    fields: dict[str, object] = {
        "correlation_id": uuid4(),
        "task_type": "summarization",
        "llm_response_content": "Nine classes work with caveats.",
    }
    fields.update(overrides)
    return ModelQualityGateInput.model_validate(fields)


@pytest.mark.unit
def test_grounding_source_is_accepted_and_round_trips() -> None:
    gate_input = _input(grounding_source="eight rows: a, b, c, d, e, f, g, h")

    assert gate_input.grounding_source == "eight rows: a, b, c, d, e, f, g, h"
    decoded = ModelQualityGateInput.model_validate_json(gate_input.model_dump_json())
    assert decoded.grounding_source == gate_input.grounding_source


@pytest.mark.unit
def test_unset_grounding_source_is_omitted_from_the_wire() -> None:
    gate_input = _input()

    assert gate_input.grounding_source is None
    assert "grounding_source" not in gate_input.model_dump()
    assert "grounding_source" not in gate_input.model_dump_json()


@pytest.mark.unit
def test_grounding_source_must_be_text() -> None:
    with pytest.raises(ValidationError):
        _input(grounding_source=42)
