# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Typed archive replay provenance headers are complete and lossless."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.event_bus import ModelArchiveReplayProvenance


def _headers() -> tuple[tuple[str, bytes | None], ...]:
    return (
        ("message_id", b"00000000-0000-4000-8000-000000000001"),
        (ModelArchiveReplayProvenance.SOURCE_TOPIC_HEADER, b"source.events.v1"),
        ("opaque-original-header", b"\x00\xff"),
        (ModelArchiveReplayProvenance.SOURCE_PARTITION_HEADER, b"0"),
        (ModelArchiveReplayProvenance.SOURCE_OFFSET_HEADER, b"42"),
    )


def test_round_trip_uses_contract_header_names_and_canonical_bytes() -> None:
    provenance = ModelArchiveReplayProvenance.from_kafka_headers(_headers())

    assert provenance.source_topic == "source.events.v1"
    assert provenance.source_partition == 0
    assert provenance.source_offset == 42
    assert provenance.to_kafka_headers() == (
        ("onex-archive-source-topic", b"source.events.v1"),
        ("onex-archive-source-partition", b"0"),
        ("onex-archive-source-offset", b"42"),
    )


@pytest.mark.parametrize(
    "headers",
    [
        (),
        (("onex-archive-source-topic", b"source.events.v1"),),
        (
            ("onex-archive-source-topic", b"source.events.v1"),
            ("onex-archive-source-partition", b"0"),
            ("onex-archive-source-offset", None),
        ),
        (
            ("onex-archive-source-topic", b"source.events.v1"),
            ("onex-archive-source-topic", b"source.events.v1"),
            ("onex-archive-source-partition", b"0"),
            ("onex-archive-source-offset", b"42"),
        ),
        (
            ("onex-archive-source-topic", b"source.events.v1"),
            ("onex-archive-source-partition", b"00"),
            ("onex-archive-source-offset", b"42"),
        ),
        (
            ("onex-archive-source-topic", b"source.events.v1"),
            ("onex-archive-source-partition", b"0"),
            ("onex-archive-source-offset", b"-1"),
        ),
        (
            ("onex-archive-source-topic", b"source.events.v1"),
            ("onex-archive-source-partition", b"0"),
            ("onex-archive-source-offset", b"4\xff"),
        ),
    ],
)
def test_incomplete_ambiguous_or_malformed_headers_refuse(
    headers: tuple[tuple[str, bytes | None], ...],
) -> None:
    with pytest.raises(ModelOnexError) as exc_info:
        ModelArchiveReplayProvenance.from_kafka_headers(headers)
    assert exc_info.value.error_code is EnumCoreErrorCode.VALIDATION_ERROR


@pytest.mark.parametrize(
    "payload",
    [
        {
            "source_topic": " source.events.v1",
            "source_partition": 0,
            "source_offset": 1,
        },
        {
            "source_topic": "source.events.v1",
            "source_partition": -1,
            "source_offset": 1,
        },
        {
            "source_topic": "source.events.v1",
            "source_partition": 0,
            "source_offset": -1,
        },
        {
            "source_topic": "source.events.v1",
            "source_partition": "0",
            "source_offset": 1,
        },
        {
            "source_topic": "source.events.v1",
            "source_partition": 0,
            "source_offset": 1,
            "extra": True,
        },
    ],
)
def test_typed_values_are_strict_and_forbid_unknown_fields(
    payload: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        ModelArchiveReplayProvenance.model_validate(payload)
