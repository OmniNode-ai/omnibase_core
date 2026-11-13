# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OMN-24039: the inference intent carries the delegation task class.

The field tells the inference effect which task class the call serves so the
effect can look up the call-time ceiling of that class in the deployment
overlay. These tests bind the wire properties: a stamped class round-trips
through JSON unchanged, and an intent from a producer that predates the field
reads back as ``None`` and stays off the wire rather than serializing an
explicit null.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from omnibase_core.models.delegation.wire import ModelInferenceIntent

pytestmark = pytest.mark.unit


def _intent(**overrides: object) -> ModelInferenceIntent:
    base: dict[str, object] = {
        "base_url": "https://provider.example/v1/chat/completions",
        "model": "example/model",
        "system_prompt": "s",
        "prompt": "p",
        "max_tokens": 256,
        "correlation_id": uuid4(),
    }
    base.update(overrides)
    return ModelInferenceIntent.model_validate(base)


def test_task_type_round_trips() -> None:
    """A stamped task class survives the wire unchanged.

    The effect reads the class to look up the call-time ceiling of the
    deployment overlay, so a value that is present in the producer and
    absent in the consumer would silently fall back to the wrong ceiling.
    """
    intent = _intent(task_type="reasoning")
    assert intent.task_type == "reasoning"

    dumped = intent.model_dump(mode="json")
    assert dumped["task_type"] == "reasoning"

    back = ModelInferenceIntent.model_validate(dumped)
    assert back.task_type == intent.task_type


def test_absent_task_type_is_none_and_not_on_the_wire() -> None:
    """A producer that predates the field makes no claim.

    ``None`` must read back as ``None`` and stay off the wire, not
    serialize as an explicit null -- the consumer distinguishes "no claim"
    from a stamped class, and the wire should not invent one.
    """
    intent = _intent()
    assert intent.task_type is None
    assert "task_type" not in intent.model_dump(mode="json")
