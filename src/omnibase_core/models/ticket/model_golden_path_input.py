# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelGoldenPathInput — input specification for golden path event chain tests.

OMN-10064 / OMN-9582: Ported from onex_change_control.models.model_golden_path.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

_MAX_STRING_LENGTH = 10000


class ModelGoldenPathInput(BaseModel):
    """Input specification for a golden path test.

    Describes the Kafka topic and fixture file to use as the input event.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    topic: str = Field(
        ...,
        description="Kafka topic to publish the input event to",
        max_length=_MAX_STRING_LENGTH,
    )
    fixture: str = Field(
        ...,
        description="Path to the JSON fixture file relative to the repo root",
        max_length=_MAX_STRING_LENGTH,
    )
    input_correlation_id_field: str = Field(
        default="correlation_id",
        description="Field name in the fixture that holds the correlation ID",
        max_length=_MAX_STRING_LENGTH,
    )


__all__ = ["ModelGoldenPathInput"]
