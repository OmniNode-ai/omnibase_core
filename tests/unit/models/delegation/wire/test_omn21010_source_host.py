# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""The lab host a delegation request was sent from (OMN-21010).

Operator ruling 2026-10-11T17:58:45Z binds each Claude account's API key to the
machine the account lives on, so a review placed on a lab host spends only that
host's key. Lab lanes delegate through a deployed runtime rather than on their
own host, so the router can honour the binding only when the request names its
host. These tests pin the contract: the accepted shape, the refusals, and that
an unset host leaves the wire shape exactly as it was.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from omnibase_core.models.delegation.wire import ModelDelegationRequest


def _request(**kwargs: object) -> ModelDelegationRequest:
    defaults: dict[str, object] = {
        "prompt": "review this diff",
        "task_type": "test",
        "correlation_id": uuid.UUID("00000000-0000-0000-0000-000000021010"),
        "emitted_at": datetime(2026, 10, 11, 23, 0, tzinfo=UTC),
    }
    defaults.update(kwargs)
    return ModelDelegationRequest.model_validate(defaults)


@pytest.mark.unit
@pytest.mark.parametrize("host", ["h201", "h200", "h101", "lab-host-7"])
def test_source_host_accepts_a_lab_registry_name(host: str) -> None:
    request = _request(source_host=host)
    assert request.source_host == host
    dumped = request.model_dump(mode="json")
    assert dumped["source_host"] == host
    assert ModelDelegationRequest.model_validate(dumped).source_host == host


@pytest.mark.unit
@pytest.mark.parametrize(
    "host",
    [
        "",
        " ",
        " h201",
        "h201 ",
        "H201",
        "h201.local",
        "h201:8085",
        "-h201",
        "h201-",
        "h_201",
        "h" * 64,
    ],
)
def test_source_host_refuses_a_malformed_name(host: str) -> None:
    with pytest.raises(ValidationError, match="source_host"):
        _request(source_host=host)


@pytest.mark.unit
def test_source_host_unset_keeps_the_wire_shape() -> None:
    request = _request()
    assert request.source_host is None
    assert "source_host" not in request.model_dump()
    assert "source_host" not in request.model_dump(mode="json")
    assert "source_host" not in request.model_dump_json()
