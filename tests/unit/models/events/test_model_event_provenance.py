# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The provenance stamp on an event: what each lane may and must say.

ModelEventProvenance is attribution only -- a claim the producer made, never
proof of authority -- and its whole value comes from the runtime's lane
overlay, never a code default. The validators pin that claim's shape:

1. A stamped lane (DEV, STABILITY, OTHER) records its full overlay:
   host, install_source and revision, plus lane_kind for OTHER alone.
2. UNKNOWN records nothing: an event with no provenance says so by carrying
   no half of one.
3. A blank string reads as attribution to a writer and as nothing to a
   reader, so it is refused.
"""

from enum import Enum

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_provenance_install_source import (
    EnumProvenanceInstallSource,
)
from omnibase_core.enums.enum_provenance_lane import EnumProvenanceLane
from omnibase_core.enums.enum_provenance_lane_kind import EnumProvenanceLaneKind
from omnibase_core.models.events.model_event_provenance import ModelEventProvenance

# A full overlay as a lane overlay would hand it to a writer.
_FULL_OVERLAY: dict[str, object] = {
    "host": "mac-unit-1.local",
    "install_source": EnumProvenanceInstallSource.TAG,
    "revision": "v1.2.3",
}


def _stamp(**overrides: object) -> ModelEventProvenance:
    """Build a provenance stamp, defaulting to a fully overlaid dev lane."""
    data: dict[str, object] = {"lane": EnumProvenanceLane.DEV, **_FULL_OVERLAY}
    data.update(overrides)
    return ModelEventProvenance(**data)


@pytest.mark.unit
class TestValidStampsAreAccepted:
    def test_a_fully_overlaid_dev_stamp_is_accepted(self) -> None:
        stamp = _stamp()

        assert stamp.lane is EnumProvenanceLane.DEV
        assert stamp.lane_kind is None
        assert stamp.host == "mac-unit-1.local"
        assert stamp.install_source is EnumProvenanceInstallSource.TAG
        assert stamp.revision == "v1.2.3"

    def test_a_fully_overlaid_stability_stamp_is_accepted(self) -> None:
        stamp = _stamp(
            lane=EnumProvenanceLane.STABILITY,
            host="stability-1.local",
            install_source=EnumProvenanceInstallSource.BRANCH,
            revision="dev",
        )

        assert stamp.lane is EnumProvenanceLane.STABILITY
        assert stamp.lane_kind is None
        assert stamp.revision == "dev"

    @pytest.mark.parametrize("lane_kind", list(EnumProvenanceLaneKind))
    def test_an_other_stamp_is_accepted_for_each_lane_kind(
        self, lane_kind: EnumProvenanceLaneKind
    ) -> None:
        stamp = _stamp(
            lane=EnumProvenanceLane.OTHER,
            lane_kind=lane_kind,
            install_source=EnumProvenanceInstallSource.HAND,
        )

        assert stamp.lane is EnumProvenanceLane.OTHER
        assert stamp.lane_kind is lane_kind


@pytest.mark.unit
class TestValidatorRefusals:
    @pytest.mark.parametrize("blank", ["", "   ", "\t\n"])
    def test_a_blank_host_is_refused(self, blank: str) -> None:
        with pytest.raises(ValidationError, match="host"):
            _stamp(host=blank)

    @pytest.mark.parametrize("blank", ["", "   ", "\t\n"])
    def test_a_blank_revision_is_refused(self, blank: str) -> None:
        with pytest.raises(ValidationError, match="revision"):
            _stamp(revision=blank)

    @pytest.mark.parametrize(
        "lane", [EnumProvenanceLane.DEV, EnumProvenanceLane.STABILITY]
    )
    def test_a_stamped_lane_refuses_a_lane_kind(self, lane: EnumProvenanceLane) -> None:
        with pytest.raises(ValidationError, match="lane_kind"):
            _stamp(lane=lane, lane_kind=EnumProvenanceLaneKind.MAC_UNIT)

    def test_an_other_lane_requires_a_lane_kind(self) -> None:
        with pytest.raises(ValidationError, match="lane_kind"):
            _stamp(lane=EnumProvenanceLane.OTHER)

    @pytest.mark.parametrize(
        ("missing_field", "overlay"),
        [
            ("host", {"host": None}),
            ("install_source", {"install_source": None}),
            ("revision", {"revision": None}),
        ],
    )
    def test_a_stamped_lane_requires_its_full_overlay(
        self, missing_field: str, overlay: dict[str, object]
    ) -> None:
        with pytest.raises(ValidationError, match=missing_field):
            _stamp(
                lane=EnumProvenanceLane.OTHER,
                lane_kind=EnumProvenanceLaneKind.LANE_WORKTREE,
                **overlay,
            )

    @pytest.mark.parametrize(
        ("extra_field", "value"),
        [
            ("lane_kind", EnumProvenanceLaneKind.MAC_UNIT),
            ("host", "somewhere.local"),
            ("install_source", EnumProvenanceInstallSource.TAG),
            ("revision", "v1.2.3"),
        ],
    )
    def test_an_unknown_lane_refuses_every_other_field(
        self, extra_field: str, value: object
    ) -> None:
        with pytest.raises(
            ValidationError, match="must be None when lane is 'unknown'"
        ):
            _stamp(lane=EnumProvenanceLane.UNKNOWN, **{extra_field: value})


@pytest.mark.unit
class TestModelShape:
    def test_the_model_is_frozen(self) -> None:
        stamp = _stamp()

        with pytest.raises(ValidationError, match="frozen"):
            stamp.host = "somewhere-else.local"

    def test_an_unknown_extra_key_is_refused(self) -> None:
        with pytest.raises(ValidationError, match="attempted_install"):
            _stamp(attempted_install="not-a-field")


@pytest.mark.unit
class TestWireShape:
    def test_a_stamp_survives_a_json_round_trip_unchanged(self) -> None:
        stamp = _stamp(
            lane=EnumProvenanceLane.OTHER,
            lane_kind=EnumProvenanceLaneKind.HAND_RUN,
            install_source=EnumProvenanceInstallSource.WORKTREE,
        )

        restored = ModelEventProvenance.model_validate_json(stamp.model_dump_json())

        assert restored == stamp
        assert restored.model_dump() == stamp.model_dump()

    def test_an_unknown_stamp_round_trips_as_explicit_absence(self) -> None:
        stamp = _stamp(
            lane=EnumProvenanceLane.UNKNOWN,
            host=None,
            install_source=None,
            revision=None,
        )

        restored = ModelEventProvenance.model_validate_json(stamp.model_dump_json())

        assert restored == stamp
        assert restored.lane_kind is None
        assert restored.host is None


@pytest.mark.unit
class TestEnumValues:
    def test_lane_values_are_exact(self) -> None:
        assert EnumProvenanceLane.DEV.value == "dev"
        assert EnumProvenanceLane.STABILITY.value == "stability"
        assert EnumProvenanceLane.OTHER.value == "other"
        assert EnumProvenanceLane.UNKNOWN.value == "unknown"

    def test_lane_kind_values_are_exact(self) -> None:
        assert EnumProvenanceLaneKind.MAC_UNIT.value == "mac_unit"
        assert EnumProvenanceLaneKind.LANE_WORKTREE.value == "lane_worktree"
        assert EnumProvenanceLaneKind.HAND_RUN.value == "hand_run"

    def test_install_source_values_are_exact(self) -> None:
        assert EnumProvenanceInstallSource.TAG.value == "tag"
        assert EnumProvenanceInstallSource.BRANCH.value == "branch"
        assert EnumProvenanceInstallSource.WORKTREE.value == "worktree"
        assert EnumProvenanceInstallSource.HAND.value == "hand"

    @pytest.mark.parametrize(
        "enum_type",
        [EnumProvenanceLane, EnumProvenanceLaneKind, EnumProvenanceInstallSource],
    )
    def test_enum_values_are_unique(self, enum_type: type[Enum]) -> None:
        values = [member.value for member in enum_type]

        assert len(values) == len(set(values))
        assert len(values) == len(enum_type)
