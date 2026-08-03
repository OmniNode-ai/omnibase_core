# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""RED-first tests for the canonical ``ModelDeliveryContext`` (OMN-15665).

Authority (binding order: frozen Linear comment > R2 harness pins > ruling prose):

* Linear comment ``cfb64e0f-c2e6-4ae2-94cf-308c7e1a1efb`` on OMN-15666 — the frozen
  r2 contract decision (author Jonah Gray, 2026-08-02T20:10:29Z).
* R2 harness pin (READ-ONLY reference, not modified here):
  ``omni_worktrees/OMN-15663/omninode_infra-renewal/tests/fixtures/omn_15663_r2/
  target_models.py::ModelDeliveryContext`` — this test asserts the SAME shape
  (field names, types, frozen/forbid, nonnegative validators) so that repo's
  Family F golden-RED tests can later turn GREEN against the real Core type
  without any test edits over there.
* 2026-08-02 lab-readiness ruling, accepted refinement 4: the canonical delivery
  context "belongs in the owning Core, SPI, or runtime layer, separate from the
  def-B handler argument."

``ModelDeliveryContext`` is immutable, broker-populated ONLY — never a
``uuid4()``-fabricated identity, never a negative/sentinel coordinate.
"""

from __future__ import annotations

import uuid

import pytest
from pydantic import ValidationError

from omnibase_core.models.runtime.model_delivery_context import ModelDeliveryContext


def test_exact_four_field_set_frozen_and_forbid() -> None:
    """[control] Matches the R2 harness pin exactly: four fields, frozen, forbid."""
    ctx = ModelDeliveryContext(
        envelope_id=uuid.uuid4(),
        topic="onex.cmd.omnitest.example.v1",
        partition=0,
        offset=1,
    )
    assert set(type(ctx).model_fields) == {
        "envelope_id",
        "topic",
        "partition",
        "offset",
    }
    assert type(ctx).model_config.get("frozen") is True
    assert type(ctx).model_config.get("extra") == "forbid"


def test_is_immutable() -> None:
    ctx = ModelDeliveryContext(
        envelope_id=uuid.uuid4(), topic="onex.cmd.x.v1", partition=0, offset=0
    )
    with pytest.raises(ValidationError):
        ctx.offset = 5  # type: ignore[misc]


def test_rejects_unknown_field() -> None:
    with pytest.raises(ValidationError):
        ModelDeliveryContext(
            envelope_id=uuid.uuid4(),
            topic="onex.cmd.x.v1",
            partition=0,
            offset=0,
            schema_version=1,  # type: ignore[call-arg]
        )


@pytest.mark.parametrize("field", ["partition", "offset"])
def test_rejects_negative_coordinate_sentinel(field: str) -> None:
    """A ``-1`` sentinel is a fabrication, never a legitimate broker coordinate."""
    kwargs = {
        "envelope_id": uuid.uuid4(),
        "topic": "onex.cmd.x.v1",
        "partition": 0,
        "offset": 0,
    }
    kwargs[field] = -1
    with pytest.raises(ValidationError):
        ModelDeliveryContext(**kwargs)


def test_envelope_id_must_be_a_real_uuid_type() -> None:
    ctx = ModelDeliveryContext(
        envelope_id=uuid.uuid4(), topic="onex.cmd.x.v1", partition=0, offset=0
    )
    assert isinstance(ctx.envelope_id, uuid.UUID)
