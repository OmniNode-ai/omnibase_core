# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""An envelope with no provenance dumps no ``provenance`` key (OMN-25336).

The envelope is ``extra="forbid"``, so a reader pinned below the release that added ``provenance``
rejects any wire dump that carries the key, ``null`` included. The failing control is the dump of an
unstamped envelope: it carried ``provenance: null``.
"""

from __future__ import annotations

import json

import pytest
from pydantic import BaseModel

from omnibase_core.enums.enum_provenance_install_source import (
    EnumProvenanceInstallSource,
)
from omnibase_core.enums.enum_provenance_lane import EnumProvenanceLane
from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope
from omnibase_core.models.events.model_event_provenance import ModelEventProvenance


class _Payload(BaseModel):
    message: str


def _envelope(**extra: object) -> ModelEventEnvelope[_Payload]:
    return ModelEventEnvelope[_Payload](payload=_Payload(message="m"), **extra)


@pytest.mark.unit
def test_provenance_absent_from_the_dump_of_an_unstamped_envelope() -> None:
    envelope = _envelope()
    assert envelope.provenance is None
    assert "provenance" not in envelope.model_dump()
    assert "provenance" not in envelope.model_dump(mode="json")
    assert "provenance" not in json.loads(envelope.model_dump_json())


@pytest.mark.unit
def test_provenance_present_in_the_dump_of_a_stamped_envelope() -> None:
    """Positive control: a stamped envelope still carries the key on the wire."""
    stamp = ModelEventProvenance(
        lane=EnumProvenanceLane.DEV,
        host="host-1",
        install_source=EnumProvenanceInstallSource.WORKTREE,
        revision="abc1234",
    )
    wire = json.loads(_envelope(provenance=stamp).model_dump_json())
    assert wire["provenance"]["lane"] == "dev"


@pytest.mark.unit
def test_provenance_absent_dump_round_trips_to_an_unstamped_envelope() -> None:
    wire = _envelope().model_dump_json()
    restored = ModelEventEnvelope[_Payload].model_validate_json(wire)
    assert restored.provenance is None
