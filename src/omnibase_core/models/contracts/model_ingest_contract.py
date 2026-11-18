# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Shared wire contract for HTTPS ingest clients and the ingest door."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from hashlib import sha256 as _sha256
from types import MappingProxyType
from typing import Final, Literal

from pydantic import BaseModel, ConfigDict
from pydantic_core import PydanticCustomError

__all__ = [
    "CLIENT_HEADER_SET",
    "HEADER_BUDGET_MARGIN",
    "IDENTITY_HEADERS",
    "SLUG_GRAMMAR",
    "ModelIngestOverlay",
    "canonical_topic",
    "compute_event_id",
]

SLUG_GRAMMAR: Final = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,30}[a-z0-9])?", re.ASCII)
# The incoming wire header, before the door substitutes its own stamp.
IDENTITY_HEADERS: Final = ("message-id",)

# Resolve the authorization entry using the client overlay's full value byte bound.
CLIENT_HEADER_SET: Final[Mapping[str, int | Literal["max_authorization_bytes"]]] = (
    MappingProxyType(
        {
            "host": 260,  # 253-byte DNS name, optional root dot, colon and 5-digit port.
            "authorization": "max_authorization_bytes",
            "idempotency-key": 64,  # SHA-256 in hex.
            "content-type": len("application/json"),
            "content-length": 20,  # Decimal digits in an unsigned 64-bit byte count.
        }
    )
)
# Extra header count and extra byte percentage, respectively.
HEADER_BUDGET_MARGIN: Final = (4, 25)

_EVENT_ID_VERSION: Final = b"onex-event-id-v1"
_TENANT_PREFIX: Final = "tenant-"


class ModelIngestOverlay(BaseModel):
    """Shared base for ingest overlays, with no configurable identity rule."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)


def canonical_topic(topic: str) -> str:
    """Strip one valid tenant prefix and preserve the remainder as sent."""
    if not topic.startswith(_TENANT_PREFIX):
        return topic

    slug, dot, canonical = topic[len(_TENANT_PREFIX) :].partition(".")
    if not dot or not SLUG_GRAMMAR.fullmatch(slug):
        raise PydanticCustomError("topic-malformed", "topic-malformed")
    return canonical


def compute_event_id(
    topic: str,
    key: bytes | None,
    value: bytes,
    headers: Mapping[str, bytes] | Iterable[tuple[str, bytes]],
) -> str:
    """Hash the canonical topic and original record bytes in v1 wire order.

    Pass the original header pairs if the transport preserves duplicates.
    An empty header value and an absent identity header have distinct frames.
    """
    topic_bytes = canonical_topic(topic).encode("utf-8")
    identity_values: dict[str, bytes] = {}
    pairs = headers.items() if isinstance(headers, Mapping) else headers
    for name, header_value in pairs:
        normalized_name = name.lower()
        if normalized_name not in IDENTITY_HEADERS:
            continue
        if normalized_name in identity_values:
            raise PydanticCustomError(
                "identity-header-duplicate", "identity-header-duplicate"
            )
        identity_values[normalized_name] = header_value

    digest = _sha256()
    digest.update(_length_prefixed(_EVENT_ID_VERSION))
    digest.update(_length_prefixed(topic_bytes))
    digest.update(_optional_bytes(key))
    digest.update(_length_prefixed(value))
    for name in IDENTITY_HEADERS:
        digest.update(_length_prefixed(name.encode("ascii")))
        digest.update(_optional_bytes(identity_values.get(name)))
    return digest.hexdigest()


def _length_prefixed(value: bytes) -> bytes:
    return len(value).to_bytes(8, "big") + value


def _optional_bytes(value: bytes | None) -> bytes:
    if value is None:
        return b"\x00"
    return b"\x01" + _length_prefixed(value)
