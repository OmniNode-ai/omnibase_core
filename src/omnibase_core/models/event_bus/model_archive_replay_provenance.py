# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Typed provenance carried by records replayed from a topic archive.

This is deliberately separate from :class:`ModelEventHeaders`: archive
provenance is an optional transport-level header group, not a new field on
every ONEX event.  The representation matches the three headers emitted by
the topic archive replay contract and never decodes or rewrites the record
key, value, or unrelated Kafka headers.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError


def _validation_error(message: str) -> ModelOnexError:
    return ModelOnexError(
        error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        message=message,
    )


class ModelArchiveReplayProvenance(BaseModel):
    """Source position attached to one archive-replayed Kafka record."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    SOURCE_TOPIC_HEADER: ClassVar[str] = "onex-archive-source-topic"
    SOURCE_PARTITION_HEADER: ClassVar[str] = "onex-archive-source-partition"
    SOURCE_OFFSET_HEADER: ClassVar[str] = "onex-archive-source-offset"

    source_topic: str = Field(
        min_length=1,
        max_length=249,
        pattern=r"^[A-Za-z0-9._-]+$",
        strict=True,
    )
    source_partition: int = Field(ge=0, strict=True)
    source_offset: int = Field(ge=0, strict=True)

    @classmethod
    def from_kafka_headers(
        cls, headers: Sequence[tuple[str, bytes | None]]
    ) -> ModelArchiveReplayProvenance:
        """Parse the complete archive provenance group from Kafka headers.

        Duplicate, partial, null, non-UTF-8, or non-canonical numeric values
        are refused instead of being collapsed or defaulted. Other headers are
        intentionally ignored and remain the caller's responsibility to
        preserve byte-for-byte.
        """

        names = (
            cls.SOURCE_TOPIC_HEADER,
            cls.SOURCE_PARTITION_HEADER,
            cls.SOURCE_OFFSET_HEADER,
        )
        found: dict[str, bytes | None] = {}
        for name, value in headers:
            if name not in names:
                continue
            if name in found:
                raise _validation_error(f"duplicate archive provenance header: {name}")
            found[name] = value

        if set(found) != set(names):
            raise _validation_error(
                "archive provenance headers must be present as a complete set"
            )
        if any(found[name] is None for name in names):
            raise _validation_error("archive provenance headers must not be null")

        decoded: dict[str, str] = {}
        try:
            for name in names:
                value = found[name]
                assert value is not None
                decoded[name] = value.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise _validation_error("archive provenance headers must be UTF-8") from exc

        def parse_position(name: str) -> int:
            raw = decoded[name]
            if not raw.isascii() or not raw.isdecimal():
                raise _validation_error(
                    f"{name} must be a canonical non-negative integer"
                )
            value = int(raw)
            if str(value) != raw:
                raise _validation_error(
                    f"{name} must be a canonical non-negative integer"
                )
            return value

        return cls(
            source_topic=decoded[cls.SOURCE_TOPIC_HEADER],
            source_partition=parse_position(cls.SOURCE_PARTITION_HEADER),
            source_offset=parse_position(cls.SOURCE_OFFSET_HEADER),
        )

    def to_kafka_headers(self) -> tuple[tuple[str, bytes], ...]:
        """Return the canonical three-header wire representation."""

        return (
            (self.SOURCE_TOPIC_HEADER, self.source_topic.encode("utf-8")),
            (self.SOURCE_PARTITION_HEADER, str(self.source_partition).encode("ascii")),
            (self.SOURCE_OFFSET_HEADER, str(self.source_offset).encode("ascii")),
        )


__all__ = ["ModelArchiveReplayProvenance"]
