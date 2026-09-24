# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One line of the on-disk work ledger (OMN-16177, typed work ledger T3)."""

from __future__ import annotations

from typing import Final, Literal

from pydantic import Field

from omnibase_core.models.events.model_event_payload_base import ModelEventPayloadBase
from omnibase_core.models.events.work.model_work_event_union import ModelWorkEvent

__all__ = ["WORK_LEDGER_SCHEMA", "ModelWorkLedgerRecord"]

WORK_LEDGER_SCHEMA: Final = "onex.work-ledger/1"
"""The record schema this core version writes and reads. Any other value is refused."""


class ModelWorkLedgerRecord(ModelEventPayloadBase):
    """A versioned envelope around one work event, as written to the JSONL ledger.

    The on-disk key is ``schema``. The attribute is ``ledger_schema`` because
    ``schema`` would shadow a ``BaseModel`` attribute. The key is required with
    no default, so a line that omits it is refused rather than read as version 1.
    """

    ledger_schema: Literal["onex.work-ledger/1"] = Field(
        ...,
        alias="schema",
        description="Record schema identifier. Serialized under the key 'schema'.",
    )
    event: ModelWorkEvent = Field(
        ...,
        description="The work event, discriminated on its 'kind'.",
    )
