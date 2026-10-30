# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelNodeAnnouncement: frozen, extra-forbidden, strict about hash and time (OMN-21589)."""

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_announced_node_kind import EnumAnnouncedNodeKind
from omnibase_core.enums.enum_announcement_operation import EnumAnnouncementOperation
from omnibase_core.models.events.contract_registration import (
    ModelAnnouncedPackage,
    ModelNodeAnnouncement,
)
from tests.unit.models.nodes.package_announce.fixture_planted import (
    GOOD_FIELDS,
    PLANTED_INVALID_FIELDS,
)


@pytest.mark.unit
def test_the_control_record_is_valid_and_round_trips_through_json() -> None:
    record = ModelNodeAnnouncement.model_validate(GOOD_FIELDS)
    assert record.operation is EnumAnnouncementOperation.ANNOUNCE
    assert record.node_kind is EnumAnnouncedNodeKind.NODE
    assert record.package == ModelAnnouncedPackage(
        distribution="example-pkg", version="1.2.3"
    )
    assert ModelNodeAnnouncement.model_validate_json(record.model_dump_json()) == record


@pytest.mark.unit
def test_the_record_is_frozen() -> None:
    record = ModelNodeAnnouncement.model_validate(GOOD_FIELDS)
    with pytest.raises(ValidationError):
        setattr(record, "generation", 2)


@pytest.mark.unit
@pytest.mark.parametrize("planted", sorted(PLANTED_INVALID_FIELDS))
def test_each_planted_violation_is_refused(planted: str) -> None:
    """Each planted record breaks one rule of an otherwise valid record."""
    with pytest.raises(ValidationError):
        ModelNodeAnnouncement.model_validate(
            {**GOOD_FIELDS, **PLANTED_INVALID_FIELDS[planted]}
        )


@pytest.mark.unit
def test_every_field_of_the_control_record_is_required_or_defaulted_on_purpose() -> (
    None
):
    """Dropping a required field is refused; the two list fields default to empty."""
    for required in (
        "entity_id",
        "operation",
        "content_hash",
        "package",
        "node_kind",
        "announcer_id",
        "generation",
        "announced_at",
    ):
        fields = {k: v for k, v in GOOD_FIELDS.items() if k != required}
        with pytest.raises(ValidationError):
            ModelNodeAnnouncement.model_validate(fields)
    optional = {
        k: v
        for k, v in GOOD_FIELDS.items()
        if k not in {"declared_topics", "handler_dependencies"}
    }
    record = ModelNodeAnnouncement.model_validate(optional)
    assert record.declared_topics == () and record.handler_dependencies == ()
