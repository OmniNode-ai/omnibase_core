# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The causal edge on the envelope the bus actually carries (OMN-18116).

A replay is a re-derivation compared against a record. For an event chain the
thing re-derived is the causal edge: hop N's recorded parent must re-derive to
hop N-1's own identity. Before this field existed the edge was recorded nowhere,
so a ``replay_green`` verdict could only ever be a claim.

Measured on the dev lane before the field was added, two-hour window of
``event_ledger``: 4920 rows, ``envelope_id`` populated on 4920, ``correlation_id``
populated on 4920, ``span_id`` populated on 0, ``parent_span_id`` populated on 0.
That is why the edge references ``envelope_id`` -- the only per-hop identity the
platform already originates on every envelope -- and not the declared-but-dead
span pair. The decision is recorded in the approved plan
``beta/plans/2026-09-10-causal-edge-origination-proposal.md`` (option A).

These tests pin four properties:

1. The field exists on ``ModelEventEnvelope`` and round-trips.
2. It is optional, and its absence is the checkable statement "this hop is a
   chain head" rather than an accident.
3. A self-referencing edge is refused. An envelope cannot be caused by itself,
   and a self-edge would let a verifier's re-derivation close against nothing.
4. The edge survives serialization, so a reader downstream of the wire can see
   it. An edge that exists only in memory is the ``ModelEnvelope.causation_id``
   failure shape this design exists to avoid.
"""

from uuid import UUID, uuid4

import pytest
from pydantic import BaseModel, ValidationError

from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope


class _Payload(BaseModel):
    """Minimal payload; the edge is an envelope property, not a payload one."""

    message: str


@pytest.mark.unit
class TestParentEnvelopeIdField:
    """The causal edge is declared, optional, and carried."""

    def test_parent_envelope_id_round_trips(self) -> None:
        """A hop records the identity of the envelope it consumed."""
        parent_id = uuid4()
        envelope = ModelEventEnvelope[_Payload](
            payload=_Payload(message="child"),
            parent_envelope_id=parent_id,
        )
        assert envelope.parent_envelope_id == parent_id
        assert isinstance(envelope.parent_envelope_id, UUID)

    def test_absent_parent_is_the_chain_head_statement(self) -> None:
        """No parent means chain head, and it is the default."""
        envelope = ModelEventEnvelope[_Payload](payload=_Payload(message="head"))
        assert envelope.parent_envelope_id is None

    def test_self_reference_is_refused(self) -> None:
        """An envelope cannot be its own cause.

        ``ModelEnvelope`` already proves this shape for ``causation_id``. The
        reason it matters here is sharper: a verifier re-derives the expected
        parent and compares. A self-edge closes the comparison against the hop
        itself, so a broken chain would read as a valid one-hop chain.
        """
        envelope_id = uuid4()
        with pytest.raises(ValidationError) as exc_info:
            ModelEventEnvelope[_Payload](
                payload=_Payload(message="ouroboros"),
                envelope_id=envelope_id,
                parent_envelope_id=envelope_id,
            )
        message = str(exc_info.value)
        assert "parent_envelope_id" in message
        # Named explicitly so the assertion cannot be satisfied by the
        # ``extra="forbid"`` refusal that fires before the field exists.
        assert "self-reference" in message

    def test_distinct_parent_is_accepted(self) -> None:
        """The negative control for the self-reference test.

        Without this, a validator that refused every parent would pass the
        test above while breaking the feature.
        """
        envelope = ModelEventEnvelope[_Payload](
            payload=_Payload(message="child"),
            envelope_id=uuid4(),
            parent_envelope_id=uuid4(),
        )
        assert envelope.parent_envelope_id is not None
        assert envelope.parent_envelope_id != envelope.envelope_id

    def test_edge_survives_model_dump(self) -> None:
        """The edge reaches a reader, not only the constructing process."""
        parent_id = uuid4()
        envelope = ModelEventEnvelope[_Payload](
            payload=_Payload(message="child"),
            parent_envelope_id=parent_id,
        )
        dumped = envelope.model_dump(mode="json")
        assert dumped["parent_envelope_id"] == str(parent_id)

        revived = ModelEventEnvelope[_Payload].model_validate(dumped)
        assert revived.parent_envelope_id == parent_id

    def test_edge_survives_to_dict_lazy(self) -> None:
        """The lazy dict form is a separate hand-written projection.

        It enumerates fields explicitly, so a field added to the model is NOT
        automatically present here. That is exactly how a recorded edge gets
        silently dropped on the way to a consumer.
        """
        parent_id = uuid4()
        envelope = ModelEventEnvelope[_Payload](
            payload=_Payload(message="child"),
            parent_envelope_id=parent_id,
        )
        lazy = envelope.to_dict_lazy()
        assert lazy["parent_envelope_id"] == str(parent_id)

    def test_chain_head_lazy_dict_records_absence_explicitly(self) -> None:
        """A head's absent edge is present-and-null, not missing."""
        envelope = ModelEventEnvelope[_Payload](payload=_Payload(message="head"))
        lazy = envelope.to_dict_lazy()
        assert "parent_envelope_id" in lazy
        assert lazy["parent_envelope_id"] is None

    def test_envelope_version_records_the_added_field(self) -> None:
        """The schema gained a declared field, so its version moves.

        This matters more here than for an ordinary additive field: the model
        is ``extra="forbid"`` (OMN-16831), so a consumer pinned to an older
        core REFUSES an envelope carrying this key rather than ignoring it. The
        version is the signal that a reader must be on a core that declares it.
        """
        envelope = ModelEventEnvelope[_Payload](payload=_Payload(message="x"))
        assert (envelope.envelope_version.major, envelope.envelope_version.minor) == (
            2,
            2,
        )
