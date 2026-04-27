# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelGoldenPathOutput — output specification for golden path event chain tests.

OMN-10064 / OMN-9582: Ported from onex_change_control.models.model_golden_path.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.ticket.model_golden_path_assertion import (
    ModelGoldenPathAssertion,
)

_MAX_STRING_LENGTH = 10000
_MAX_LIST_ITEMS = 1000


class ModelGoldenPathOutput(BaseModel):
    """Output specification for a golden path test.

    Describes the Kafka topic to listen on for the output event, with optional
    schema validation and field-level assertions.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    topic: str = Field(
        ...,
        description="Kafka topic to consume the output event from",
        max_length=_MAX_STRING_LENGTH,
    )
    output_correlation_id_field: str = Field(
        default="correlation_id",
        description="Field name in the output event that holds the correlation ID",
        max_length=_MAX_STRING_LENGTH,
    )
    schema_name: str | None = Field(
        default=None,
        description=(
            "Optional Pydantic model class name for output validation. "
            "When present and importable, the runner validates the output event "
            "against this schema."
        ),
        max_length=_MAX_STRING_LENGTH,
    )
    assertions: list[ModelGoldenPathAssertion] = Field(
        default_factory=list,
        description="Field-level assertions to evaluate against the output event",
        max_length=_MAX_LIST_ITEMS,
    )


__all__ = ["ModelGoldenPathOutput"]
