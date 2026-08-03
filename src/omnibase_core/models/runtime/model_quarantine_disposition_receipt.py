# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Canonical post-ack quarantine disposition receipt (OMN-15667).

``ModelQuarantineDispositionReceipt`` is the sole surface carrying quarantine
broker coordinates (``quarantine_topic``/``quarantine_partition``/
``quarantine_offset``). It exists only AFTER the broker has acknowledged the
publish of a ``ModelQuarantineWirePayload`` to the quarantine topic -- it is
never serialized as that same Kafka record, and it is a distinct model from
the pre-ack payload for exactly the reason that payload cannot contain these
coordinates: they are assigned by publishing the payload, so they cannot
also be a field of it.

Frozen public Core name/field-set authority: Linear comment
cfb64e0f-c2e6-4ae2-94cf-308c7e1a1efb on OMN-15666 (2026-08-02T20:10:29Z):
"Existing ModelQuarantineDispositionReceipt remains the exact validated
quarantine payload plus broker-returned quarantine topic/partition/offset" --
unchanged from OMN-15667's original acceptance (comment
822ef49f-68df-4902-abad-f0764a1258e6). Field set/names/types are pinned
verbatim by the R2 harness reference
(tests/fixtures/omn_15663_r2/target_models.py in the READ-ONLY
omni_worktrees/OMN-15663/omninode_infra-renewal worktree).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.event_bus.model_quarantine_wire_payload import (
    ModelQuarantineWirePayload,
)


class ModelQuarantineDispositionReceipt(BaseModel):
    """Post-ack quarantine disposition receipt.

    Carries the exact validated pre-ack wire payload plus the broker
    acknowledgement's quarantine topic/partition/offset. Constructed only
    after that acknowledgement is observed.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    quarantine_payload: ModelQuarantineWirePayload = Field(
        ...,
        description="The exact validated pre-ack quarantine wire payload that was published.",
    )
    quarantine_topic: str = Field(
        ...,
        description="Quarantine topic the payload was published to.",
    )
    quarantine_partition: int = Field(
        ...,
        description="Partition assigned by the broker acknowledgement.",
        ge=0,
    )
    quarantine_offset: int = Field(
        ...,
        description="Offset assigned by the broker acknowledgement.",
        ge=0,
    )


__all__ = ["ModelQuarantineDispositionReceipt"]
