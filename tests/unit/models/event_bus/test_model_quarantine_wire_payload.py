# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for ModelQuarantineWirePayload -- the pre-ack Kafka quarantine wire
shape (OMN-15667).

Causal invariant under test: a record cannot contain the broker
partition/offset assigned by publishing that same record. This model
represents a FAILED, UNACKNOWLEDGED primary-DLQ publish -- quarantine broker
coordinates must be ABSENT BY CONSTRUCTION (there is no
``quarantine_topic``/``quarantine_partition``/``quarantine_offset`` field, and
``extra="forbid"`` rejects any attempt to smuggle them in). Post-ack truth
lives exclusively in the separate ``ModelQuarantineDispositionReceipt``.

Frozen r2 contract authority: Linear comment cfb64e0f-c2e6-4ae2-94cf-308c7e1a1efb
on OMN-15666 (2026-08-02T20:10:29Z), reconciled with the OMN-15667 causal-audit
comment c54fcc0e-015c-431a-a095-68558eada2b5 (2026-08-02T18:41:06Z) and pinned
verbatim by the R2 harness reference
(tests/fixtures/omn_15663_r2/target_models.py in the
omni_worktrees/OMN-15663/omninode_infra-renewal READ-ONLY worktree). Field set,
names, and types here MUST match that pin exactly so Family A of
tests/gateway/test_omn_15663_r2_family_a_dlq_durability.py can turn green
later without any test edit.
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

QUARANTINE_WIRE_PAYLOAD_REQUIRED_FIELDS: tuple[str, ...] = (
    "source_envelope_id",
    "source_topic",
    "source_partition",
    "source_offset",
    "source_key_b64",
    "source_value_b64",
    "source_headers_b64",
    "primary_dlq_error_type",
    "primary_dlq_error_message",
    "source_failure",
)


def _valid_failure_evidence() -> ModelDeliveryFailureEvidence:
    return ModelDeliveryFailureEvidence(
        stage="primary_dlq_publish",
        error_type="ConnectionError",
        error_message="mock broker refused publish",
        retryable=True,
    )


def _valid_quarantine_kwargs() -> dict:
    return {
        "source_envelope_id": uuid.uuid4(),
        "source_topic": "onex.cmd.omnibase-infra.delegation-request.v1",
        "source_partition": 0,
        "source_offset": 42,
        "source_key_b64": "a2V5",
        "source_value_b64": "dmFsdWU=",
        "source_headers_b64": (("trace-id", "dHJhY2U="),),
        "primary_dlq_error_type": "ConnectionError",
        "primary_dlq_error_message": "mock broker refused publish",
        "source_failure": _valid_failure_evidence(),
    }


@pytest.mark.unit
class TestModelQuarantineWirePayloadConstruction:
    """Basic construction and frozen/strict invariants."""

    def test_construction_with_required_fields(self) -> None:
        source_id = uuid.uuid4()
        payload = ModelQuarantineWirePayload(
            **{**_valid_quarantine_kwargs(), "source_envelope_id": source_id}
        )
        assert payload.source_envelope_id == source_id
        assert payload.source_topic == "onex.cmd.omnibase-infra.delegation-request.v1"
        assert payload.source_partition == 0
        assert payload.source_offset == 42
        assert payload.source_failure.error_type == "ConnectionError"

    def test_exact_ten_required_fields(self) -> None:
        assert set(ModelQuarantineWirePayload.model_fields) == set(
            QUARANTINE_WIRE_PAYLOAD_REQUIRED_FIELDS
        )
        assert len(QUARANTINE_WIRE_PAYLOAD_REQUIRED_FIELDS) == 10

    def test_is_frozen(self) -> None:
        payload = ModelQuarantineWirePayload(**_valid_quarantine_kwargs())
        with pytest.raises(ValidationError):
            payload.source_offset = 999  # type: ignore[misc]

    def test_missing_required_field_rejected(self) -> None:
        kwargs = _valid_quarantine_kwargs()
        del kwargs["source_failure"]
        with pytest.raises(ValidationError):
            ModelQuarantineWirePayload(**kwargs)

    @pytest.mark.parametrize("field", ["source_partition", "source_offset"])
    def test_negative_coordinate_rejected(self, field: str) -> None:
        kwargs = _valid_quarantine_kwargs()
        kwargs[field] = -1
        with pytest.raises(ValidationError):
            ModelQuarantineWirePayload(**kwargs)


@pytest.mark.unit
class TestModelQuarantineWirePayloadCausalInvariant:
    """The causal invariant IS the ticket: this model cannot carry quarantine
    broker coordinates, because those coordinates are assigned only by
    publishing this exact record -- a record cannot contain its own
    not-yet-assigned broker offset."""

    def test_quarantine_coordinates_are_not_fields(self) -> None:
        assert "quarantine_topic" not in ModelQuarantineWirePayload.model_fields
        assert "quarantine_partition" not in ModelQuarantineWirePayload.model_fields
        assert "quarantine_offset" not in ModelQuarantineWirePayload.model_fields

    def test_construction_impossible_with_quarantine_topic(self) -> None:
        kwargs = {
            **_valid_quarantine_kwargs(),
            "quarantine_topic": "onex.dlq.quarantine.v1",
        }
        with pytest.raises(ValidationError):
            ModelQuarantineWirePayload(**kwargs)

    def test_construction_impossible_with_quarantine_partition_and_offset(self) -> None:
        kwargs = {
            **_valid_quarantine_kwargs(),
            "quarantine_partition": 0,
            "quarantine_offset": 7,
        }
        with pytest.raises(ValidationError):
            ModelQuarantineWirePayload(**kwargs)

    def test_construction_impossible_with_any_quarantine_coordinate_alone(self) -> None:
        for field, value in (
            ("quarantine_topic", "onex.dlq.quarantine.v1"),
            ("quarantine_partition", 0),
            ("quarantine_offset", 7),
        ):
            kwargs = {**_valid_quarantine_kwargs(), field: value}
            with pytest.raises(ValidationError):
                ModelQuarantineWirePayload(**kwargs)


@pytest.mark.unit
class TestModelQuarantineWirePayloadSourceTupleVerbatim:
    """Authoritative source tuple (source_topic, source_partition,
    source_offset) must survive verbatim -- it is the idempotency identity."""

    def test_source_tuple_round_trips_verbatim(self) -> None:
        payload = ModelQuarantineWirePayload(
            **{
                **_valid_quarantine_kwargs(),
                "source_topic": "onex.cmd.omnibase-infra.delegation-request.v1",
                "source_partition": 3,
                "source_offset": 99,
            }
        )
        assert (
            payload.source_topic,
            payload.source_partition,
            payload.source_offset,
        ) == ("onex.cmd.omnibase-infra.delegation-request.v1", 3, 99)

    def test_distinct_source_offset_yields_distinct_identity(self) -> None:
        source_id = uuid.uuid4()
        a = ModelQuarantineWirePayload(
            **{
                **_valid_quarantine_kwargs(),
                "source_envelope_id": source_id,
                "source_offset": 1,
            }
        )
        b = ModelQuarantineWirePayload(
            **{
                **_valid_quarantine_kwargs(),
                "source_envelope_id": source_id,
                "source_offset": 2,
            }
        )
        identity_a = (
            a.source_envelope_id,
            a.source_topic,
            a.source_partition,
            a.source_offset,
        )
        identity_b = (
            b.source_envelope_id,
            b.source_topic,
            b.source_partition,
            b.source_offset,
        )
        assert identity_a != identity_b


@pytest.mark.unit
class TestModelQuarantineWirePayloadHeadersRoundTrip:
    """Kafka headers are an ordered, duplicate-preserving sequence of
    (name, value) base64 pairs -- never a mapping, which would silently
    collapse repeated header names and lose ordering."""

    def test_headers_is_tuple_of_pairs(self) -> None:
        payload = ModelQuarantineWirePayload(**_valid_quarantine_kwargs())
        assert isinstance(payload.source_headers_b64, tuple)
        assert payload.source_headers_b64 == (("trace-id", "dHJhY2U="),)

    def test_duplicate_keys_and_order_preserved(self) -> None:
        headers = (
            ("trace-id", "dHJhY2U="),
            ("trace-id", "ZHVw"),
            ("span-id", "c3Bhbg=="),
            ("trace-id", "dGhpcmQ="),
        )
        payload = ModelQuarantineWirePayload(
            **{**_valid_quarantine_kwargs(), "source_headers_b64": headers}
        )
        assert payload.source_headers_b64 == headers
        # Sanity check on the anti-pattern this model prevents: collapsing
        # to a mapping silently drops duplicate keys and can reorder.
        collapsed_as_dict = dict(payload.source_headers_b64)
        assert len(collapsed_as_dict) == 2
        assert len(payload.source_headers_b64) == 4

    def test_empty_headers_allowed(self) -> None:
        payload = ModelQuarantineWirePayload(
            **{**_valid_quarantine_kwargs(), "source_headers_b64": ()}
        )
        assert payload.source_headers_b64 == ()

    def test_headers_as_dict_rejected(self) -> None:
        """A mapping must not be silently coerced into the pair-tuple shape."""
        with pytest.raises(ValidationError):
            ModelQuarantineWirePayload(
                **{
                    **_valid_quarantine_kwargs(),
                    "source_headers_b64": {"trace-id": "dHJhY2U="},
                }
            )


@pytest.mark.unit
class TestModelQuarantineWirePayloadR1RejectedMutations:
    """Permanent standing control reproducing the r1-rejection findings
    (Linear comment b1c09ed7): each named invented/renamed-field mutation
    must independently fail strict validation -- forever, so no future edit
    of this model can silently re-accept the rejected shape."""

    def test_invented_schema_version_rejected(self) -> None:
        kwargs = {**_valid_quarantine_kwargs(), "schema_version": "1.0.0"}
        with pytest.raises(ValidationError):
            ModelQuarantineWirePayload(**kwargs)

    def test_invented_primary_dlq_payload_rejected(self) -> None:
        kwargs = {
            **_valid_quarantine_kwargs(),
            "primary_dlq_payload": {"nested": "wrong"},
        }
        with pytest.raises(ValidationError):
            ModelQuarantineWirePayload(**kwargs)

    def test_renamed_nested_failure_key_rejected(self) -> None:
        kwargs = _valid_quarantine_kwargs()
        failure = kwargs.pop("source_failure")
        kwargs["failure_evidence"] = failure
        with pytest.raises(ValidationError):
            ModelQuarantineWirePayload(**kwargs)
