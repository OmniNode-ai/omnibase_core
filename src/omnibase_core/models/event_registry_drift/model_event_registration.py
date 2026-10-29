# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One event registration, in the shape both registries must agree on (OMN-21416).

Only the fields that must stay synchronized between a producer's declared
registrations and a consumer's emit registry are carried: the event type, the
topics it fans out to, its partition key and its required payload fields.
Transforms are not compared, because each side names them in its own terms.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelEventRegistration"]


class ModelEventRegistration(BaseModel):
    """A comparable event registration read from one declared source.

    Attributes:
        event_type: The registration key, e.g. ``delegation.usage_call``.
        topics: Every topic the event fans out to.
        partition_key_field: The payload field used as the partition key, or
            ``None`` when the source declares no key.
        required_fields: Payload fields the event must carry. Order carries no
            wire meaning and is ignored when two registrations are compared.
        source: Where the registration was declared, for findings.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    event_type: str = Field(min_length=1)
    topics: tuple[str, ...]
    partition_key_field: str | None
    required_fields: tuple[str, ...]
    source: str = Field(min_length=1)
