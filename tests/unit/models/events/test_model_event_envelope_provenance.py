# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The provenance stamp on the envelope the bus carries (OMN-19998 L1-08).

The envelope already says WHO produced an event (`producer`, OMN-18717); it
said nothing about WHERE that producer ran. Provenance adds that -- lane, host,
install source, revision -- shaped exactly like the dimensions before it:
optional so no consumer breaks, attribution only, and filled from the runtime
lane overlay, never a code default, because a defaulted stamp is an invention
that reads to a reader as a recorded fact.

Pinned:

1. A provenance stamp a writer supplies is carried, not discarded, and
   survives the JSON wire.
2. Omitting it records an explicit absence, and `provenance_lane` reads that
   absence as UNKNOWN -- never DEV, the one lane an absent stamp must not
   claim.
3. A half-invented stamp is refused: a stamped lane carries its full overlay
   or none of it.
4. Consumers that do not know the field keep working (seam tests below).
"""

import json

import pytest
from pydantic import BaseModel, ValidationError

from omnibase_core.enums.enum_provenance_install_source import (
    EnumProvenanceInstallSource,
)
from omnibase_core.enums.enum_provenance_lane import EnumProvenanceLane
from omnibase_core.enums.enum_provenance_lane_kind import EnumProvenanceLaneKind
from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope
from omnibase_core.models.events.model_event_envelope_v1_minimal import (
    ModelEventEnvelopeV1Minimal,
)
from omnibase_core.models.events.model_event_provenance import ModelEventProvenance
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.types.typed_dict_event_envelope import TypedDictEventEnvelopeDict


class _Payload(BaseModel):
    message: str


def _envelope(**extra: object) -> ModelEventEnvelope[_Payload]:
    return ModelEventEnvelope[_Payload](payload=_Payload(message="m"), **extra)


def _overlay(
    lane: EnumProvenanceLane,
    *,
    host: str = "host-1",
    install_source: EnumProvenanceInstallSource = EnumProvenanceInstallSource.WORKTREE,
    revision: str = "abc1234",
    **extra: object,
) -> ModelEventProvenance:
    """A lane-overlay-shaped stamp: what the runtime would read, verbatim."""
    return ModelEventProvenance(
        lane=lane,
        host=host,
        install_source=install_source,
        revision=revision,
        **extra,
    )


@pytest.mark.unit
class TestEnvelopeCarriesProvenance:
    def test_supplied_provenance_is_carried_not_discarded(self) -> None:
        provenance = _overlay(EnumProvenanceLane.DEV)
        envelope = _envelope(provenance=provenance)

        assert envelope.provenance == provenance
        assert envelope.model_dump()["provenance"]["lane"] is EnumProvenanceLane.DEV
        lazy = envelope.to_dict_lazy()
        assert lazy["provenance"] == provenance.model_dump(mode="json")
        assert lazy["provenance"]["lane"] == "dev"

    def test_provenance_survives_a_json_round_trip(self) -> None:
        provenance = _overlay(EnumProvenanceLane.STABILITY)
        envelope = _envelope(provenance=provenance)

        restored = ModelEventEnvelope[_Payload].model_validate_json(
            envelope.model_dump_json()
        )

        assert restored.provenance == provenance

    def test_omitting_provenance_records_an_explicit_absence(self) -> None:
        envelope = _envelope()

        assert envelope.provenance is None
        assert envelope.to_dict_lazy()["provenance"] is None
        # The absence reads UNKNOWN. Never DEV: a reader that reports DEV for
        # an unstamped event invents the one fact the envelope deliberately
        # did not carry.
        assert envelope.provenance_lane is EnumProvenanceLane.UNKNOWN
        assert envelope.provenance_lane is not EnumProvenanceLane.DEV

    @pytest.mark.parametrize(
        ("lane", "overlay_extra"),
        [
            (EnumProvenanceLane.DEV, {}),
            (EnumProvenanceLane.STABILITY, {}),
            (
                EnumProvenanceLane.OTHER,
                {"lane_kind": EnumProvenanceLaneKind.LANE_WORKTREE},
            ),
        ],
    )
    def test_provenance_lane_reads_back_the_stamped_lane(
        self,
        lane: EnumProvenanceLane,
        overlay_extra: dict[str, object],
    ) -> None:
        envelope = _envelope(provenance=_overlay(lane, **overlay_extra))

        assert envelope.provenance_lane is lane

    def test_an_unknown_key_inside_provenance_is_refused(self) -> None:
        with pytest.raises(ValidationError, match="bogus_field"):
            _envelope(
                provenance={
                    "lane": "dev",
                    "host": "host-1",
                    "install_source": "worktree",
                    "revision": "abc1234",
                    "bogus_field": "invented",
                }
            )

    def test_the_typed_dict_projection_declares_the_key(self) -> None:
        assert "provenance" in TypedDictEventEnvelopeDict.__annotations__

    def test_the_schema_version_signals_the_added_field(self) -> None:
        assert _envelope().envelope_version == ModelSemVer(major=2, minor=4, patch=0)


@pytest.mark.unit
class TestSeamEnvelopeWithoutProvenanceStillValidates:
    """Consumer shape: the pre-change wire shape stays valid.

    Every envelope already on the bus lacks the key; a reader pinned to this
    release must accept exactly what it accepted before, and read the absence
    as UNKNOWN.
    """

    def test_a_provenance_free_envelope_validates_on_the_wire(self) -> None:
        envelope = _envelope()
        wire = envelope.model_dump_json()

        restored = ModelEventEnvelope[_Payload].model_validate_json(wire)

        assert restored.provenance is None
        assert restored.provenance_lane is EnumProvenanceLane.UNKNOWN


@pytest.mark.unit
class TestSeamMinimalConsumerIgnoresProvenance:
    """Consumer shape: ModelEventEnvelopeV1Minimal, the cross-repo transport.

    It declares only event_type and payload. The wire JSON of an envelope WITH
    provenance, reshaped to those fields, must validate -- and the minimal
    model must not grow a provenance attribute. Ignoring the field is the
    contract: an optional field breaks no consumer.
    """

    def test_wire_json_with_provenance_validates_into_the_minimal_model(self) -> None:
        envelope = _envelope(
            event_type="core.provenance.test",
            provenance=_overlay(EnumProvenanceLane.DEV),
        )
        wire = json.loads(envelope.model_dump_json())
        assert "provenance" in wire  # the stamp is on the wire

        minimal = ModelEventEnvelopeV1Minimal(
            event_type=wire["event_type"],
            payload=wire["payload"],
        )

        assert minimal.event_type == "core.provenance.test"
        assert not hasattr(minimal, "provenance")


@pytest.mark.unit
class TestSeamHalfInventedStampIsRefused:
    """Failing control: a stamped lane without its overlay is refused.

    ``{"lane": "dev"}`` alone is exactly the shape a code default would
    produce, and ModelEventProvenance requires host, install_source and
    revision on any stamped lane. The envelope must fail loudly rather than
    carry an attribution that a default invented.
    """

    def test_a_dev_stamp_without_its_overlay_is_refused(self) -> None:
        with pytest.raises(ValidationError, match="host"):
            _envelope(provenance={"lane": "dev"})
