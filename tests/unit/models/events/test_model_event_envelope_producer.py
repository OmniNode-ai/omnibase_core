# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The producer identity on the envelope the bus carries (OMN-18717).

The work-events projection hardcoded every row's actor to the session because
the envelope carried nothing to say which node produced the event, and the
producing node could not be recovered from the topic for 27.4% of rows. The
envelope now has a home for that identity, shaped exactly like the tenant
dimension (OMN-16831): optional, attribution only, blank refused, serialized.

Four properties are pinned:

1. A producer identity a writer supplies is carried, not discarded.
2. It survives the JSON wire, so a reader downstream of the bus can see it.
3. Omitting it records an explicit absence; nothing invents one.
4. A blank value is refused, because it reads as attribution to a writer and
   as nothing to a reader.
"""

import pytest
from pydantic import BaseModel, ValidationError

from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.types.typed_dict_event_envelope import TypedDictEventEnvelopeDict


class _Payload(BaseModel):
    message: str


def _envelope(**extra: object) -> ModelEventEnvelope[_Payload]:
    return ModelEventEnvelope[_Payload](payload=_Payload(message="m"), **extra)


@pytest.mark.unit
class TestEnvelopeCarriesProducerIdentity:
    def test_supplied_producer_is_carried_not_discarded(self) -> None:
        envelope = _envelope(producer="node_projection_work_events")

        assert envelope.producer == "node_projection_work_events"
        assert envelope.model_dump()["producer"] == "node_projection_work_events"
        assert envelope.to_dict_lazy()["producer"] == "node_projection_work_events"

    def test_producer_survives_a_json_round_trip(self) -> None:
        envelope = _envelope(producer="node_projection_work_events")

        restored = ModelEventEnvelope[_Payload].model_validate_json(
            envelope.model_dump_json()
        )

        assert restored.producer == "node_projection_work_events"

    def test_omitting_the_producer_records_an_explicit_absence(self) -> None:
        envelope = _envelope()

        assert envelope.producer is None
        assert envelope.to_dict_lazy()["producer"] is None

    @pytest.mark.parametrize("blank", ["", "   ", "\t\n"])
    def test_a_blank_producer_is_refused(self, blank: str) -> None:
        with pytest.raises(ValidationError, match="producer"):
            _envelope(producer=blank)

    def test_the_typed_dict_projection_declares_the_key(self) -> None:
        assert "producer" in TypedDictEventEnvelopeDict.__annotations__

    def test_the_schema_version_signals_the_added_field(self) -> None:
        assert _envelope().envelope_version == ModelSemVer(major=2, minor=3, patch=0)
