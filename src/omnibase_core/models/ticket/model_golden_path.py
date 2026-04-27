# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelGoldenPath — golden path event chain test declaration.

OMN-10064 / OMN-9582: Ported from onex_change_control.models.model_golden_path.
OCC re-exports this class after Task 4 lands.

Related models (one class per file per ONEX convention):
  model_golden_path_assertion.py — ModelGoldenPathAssertion
  model_golden_path_input.py     — ModelGoldenPathInput
  model_golden_path_output.py    — ModelGoldenPathOutput
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.ticket.model_golden_path_input import ModelGoldenPathInput
from omnibase_core.models.ticket.model_golden_path_output import ModelGoldenPathOutput

_MAX_STRING_LENGTH = 10000


class ModelGoldenPath(BaseModel):
    """Golden path event chain test declaration.

    Declares a full input-to-output contract test for a node pipeline. The golden
    path runner publishes the input fixture to the input topic, waits for a matching
    output event on the output topic, and evaluates all assertions.

    The timeout_ms field lives here (not in input or output) as the single source
    of truth for the test timeout. The infra field controls whether real Kafka or
    a mock is used.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    input: ModelGoldenPathInput = Field(
        ...,
        description="Input event specification",
    )
    output: ModelGoldenPathOutput = Field(
        ...,
        description="Output event specification",
    )
    timeout_ms: int = Field(
        default=30000,
        description="Timeout in milliseconds for the full input-to-output round trip",
        ge=1,
    )
    infra: Literal["real", "mock"] = Field(
        default="real",
        description=(
            "Infrastructure mode: 'real' uses live Kafka, "
            "'mock' uses an in-process stub"
        ),
    )
    test_file: str | None = Field(
        default=None,
        description=(
            "Optional path to the pytest golden path file relative to the repo root"
        ),
        max_length=_MAX_STRING_LENGTH,
    )


__all__ = ["ModelGoldenPath"]
