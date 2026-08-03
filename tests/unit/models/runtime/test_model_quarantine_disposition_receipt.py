# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for ModelQuarantineDispositionReceipt -- the post-ack quarantine
disposition receipt (OMN-15667).

This is the sole surface carrying quarantine broker coordinates
(quarantine_topic/quarantine_partition/quarantine_offset), and it exists only
AFTER the broker has acknowledged the quarantine publish. It is a distinct
model from the pre-ack ``ModelQuarantineWirePayload`` -- the causal invariant
under test in the sibling wire-payload suite is enforced here from the other
side: this receipt is the ONLY place those coordinates may appear.

Frozen r2 contract authority: Linear comment cfb64e0f-c2e6-4ae2-94cf-308c7e1a1efb
on OMN-15666 ("Existing ModelQuarantineDispositionReceipt remains the exact
validated quarantine payload plus broker-returned quarantine
topic/partition/offset" -- unchanged from OMN-15667's original acceptance),
pinned verbatim by the R2 harness reference
(tests/fixtures/omn_15663_r2/target_models.py, READ-ONLY).
"""

from __future__ import annotations

import uuid

import pytest
from pydantic import ValidationError

from omnibase_core.models.event_bus.model_delivery_failure_evidence import (
    ModelDeliveryFailureEvidence,
)
from omnibase_core.models.event_bus.model_quarantine_wire_payload import (
    ModelQuarantineWirePayload,
)
from omnibase_core.models.runtime.model_quarantine_disposition_receipt import (
    ModelQuarantineDispositionReceipt,
)


def _valid_wire_payload() -> ModelQuarantineWirePayload:
    return ModelQuarantineWirePayload(
        source_envelope_id=uuid.uuid4(),
        source_topic="onex.cmd.omnibase-infra.delegation-request.v1",
        source_partition=0,
        source_offset=42,
        source_key_b64="a2V5",
        source_value_b64="dmFsdWU=",
        source_headers_b64=(("trace-id", "dHJhY2U="),),
        primary_dlq_error_type="ConnectionError",
        primary_dlq_error_message="mock broker refused publish",
        source_failure=ModelDeliveryFailureEvidence(
            stage="primary_dlq_publish",
            error_type="ConnectionError",
            error_message="mock broker refused publish",
            retryable=True,
        ),
    )


@pytest.mark.unit
class TestModelQuarantineDispositionReceiptConstruction:
    def test_construction_with_required_fields(self) -> None:
        payload = _valid_wire_payload()
        receipt = ModelQuarantineDispositionReceipt(
            quarantine_payload=payload,
            quarantine_topic="onex.dlq.quarantine.v1",
            quarantine_partition=0,
            quarantine_offset=7,
        )
        assert receipt.quarantine_payload == payload
        assert receipt.quarantine_topic == "onex.dlq.quarantine.v1"
        assert receipt.quarantine_partition == 0
        assert receipt.quarantine_offset == 7

    def test_exact_four_required_fields(self) -> None:
        assert set(ModelQuarantineDispositionReceipt.model_fields) == {
            "quarantine_payload",
            "quarantine_topic",
            "quarantine_partition",
            "quarantine_offset",
        }

    def test_is_frozen(self) -> None:
        receipt = ModelQuarantineDispositionReceipt(
            quarantine_payload=_valid_wire_payload(),
            quarantine_topic="onex.dlq.quarantine.v1",
            quarantine_partition=0,
            quarantine_offset=7,
        )
        with pytest.raises(ValidationError):
            receipt.quarantine_offset = 8  # type: ignore[misc]

    def test_extra_field_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            ModelQuarantineDispositionReceipt(
                quarantine_payload=_valid_wire_payload(),
                quarantine_topic="onex.dlq.quarantine.v1",
                quarantine_partition=0,
                quarantine_offset=7,
                schema_version="1.0.0",  # type: ignore[call-arg]
            )

    @pytest.mark.parametrize("field", ["quarantine_partition", "quarantine_offset"])
    def test_negative_coordinate_rejected(self, field: str) -> None:
        kwargs = {
            "quarantine_payload": _valid_wire_payload(),
            "quarantine_topic": "onex.dlq.quarantine.v1",
            "quarantine_partition": 0,
            "quarantine_offset": 7,
        }
        kwargs[field] = -1
        with pytest.raises(ValidationError):
            ModelQuarantineDispositionReceipt(**kwargs)

    def test_missing_quarantine_payload_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ModelQuarantineDispositionReceipt(  # type: ignore[call-arg]
                quarantine_topic="onex.dlq.quarantine.v1",
                quarantine_partition=0,
                quarantine_offset=7,
            )


@pytest.mark.unit
class TestModelQuarantineDispositionReceiptCausalInvariant:
    """The receipt is the ONLY surface carrying quarantine broker
    coordinates; the embedded wire payload must remain the exact pre-ack
    model with no coordinate fields of its own."""

    def test_embedded_payload_has_no_quarantine_coordinate_fields(self) -> None:
        receipt = ModelQuarantineDispositionReceipt(
            quarantine_payload=_valid_wire_payload(),
            quarantine_topic="onex.dlq.quarantine.v1",
            quarantine_partition=0,
            quarantine_offset=7,
        )
        payload_fields = type(receipt.quarantine_payload).model_fields
        assert "quarantine_topic" not in payload_fields
        assert "quarantine_partition" not in payload_fields
        assert "quarantine_offset" not in payload_fields

    def test_replaying_identical_source_tuple_is_a_distinct_receipt_per_ack(
        self,
    ) -> None:
        """Replaying the identical authoritative source tuple against two
        separate acknowledgements (e.g. an idempotent retry that lands the
        same publish twice) produces two receipts that are equal in payload
        identity but may carry distinct broker coordinates -- the receipt
        model itself does not collapse them; that collapsing is an
        idempotency-layer concern (owned elsewhere), not a schema concern."""
        payload = _valid_wire_payload()
        first = ModelQuarantineDispositionReceipt(
            quarantine_payload=payload,
            quarantine_topic="onex.dlq.quarantine.v1",
            quarantine_partition=0,
            quarantine_offset=7,
        )
        second = ModelQuarantineDispositionReceipt(
            quarantine_payload=payload,
            quarantine_topic="onex.dlq.quarantine.v1",
            quarantine_partition=0,
            quarantine_offset=7,
        )
        assert first == second
        assert (
            first.quarantine_payload.source_envelope_id
            == second.quarantine_payload.source_envelope_id
        )
