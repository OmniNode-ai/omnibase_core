# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

import pytest

from omnibase_core.enums.enum_content_kind import EnumContentKind
from omnibase_core.models.events.model_content_updated_event import (
    ModelContentPayload,
)
from omnibase_core.models.events.model_content_updated_event_envelope import (
    ModelContentUpdatedEvent,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer


def test_enum_content_kind_has_nine_values() -> None:
    kinds = list(EnumContentKind)
    assert len(kinds) == 9
    assert EnumContentKind.HERO == "hero"
    assert EnumContentKind.FOOTER == "footer"


def test_payload_round_trip() -> None:
    payload = ModelContentPayload(
        content_kind=EnumContentKind.HERO,
        schema_version=ModelSemVer(major=1, minor=0, patch=0),
        data={"headline_lines": ["Test"]},
    )
    assert payload.content_kind == EnumContentKind.HERO
    assert payload.data["headline_lines"][0] == "Test"


def test_event_inherits_runtime_base_fields() -> None:
    payload = ModelContentPayload(
        content_kind=EnumContentKind.HERO,
        schema_version=ModelSemVer(major=1, minor=0, patch=0),
        data={},
    )
    event = ModelContentUpdatedEvent(payload=payload)
    assert event.event_id is not None
    assert event.correlation_id is None  # optional
    assert event.timestamp is not None


def test_event_is_frozen() -> None:
    payload = ModelContentPayload(
        content_kind=EnumContentKind.HERO,
        schema_version=ModelSemVer(major=1, minor=0, patch=0),
        data={},
    )
    event = ModelContentUpdatedEvent(payload=payload)
    with pytest.raises(Exception):
        event.event_id = None  # type: ignore[misc]
