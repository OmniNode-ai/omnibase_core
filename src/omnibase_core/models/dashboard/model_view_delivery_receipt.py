# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""An app's receipt for delivery and decoding of a view document (OMN-21999).

The receipt identifies the compose tick and the document the app actually
received. Decode failures and partial outcomes carry a typed empty-state cause.
"""

from __future__ import annotations

from typing import Self

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_empty_state_reason import EnumEmptyStateReason
from omnibase_core.enums.enum_view_decode_outcome import EnumViewDecodeOutcome
from omnibase_core.models.dashboard.model_view_id_patterns import (
    ViewDigest,
    ViewId,
)

__all__ = ["ModelViewDeliveryReceipt"]


class ModelViewDeliveryReceipt(BaseModel):
    """Document identity, delivery time and the app's decode outcome.

    A successful decode has no cause. A decode with a cause or a refusal must
    name the empty-state reason the app observed.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    request_id: ViewId = Field(..., description="Delivery request identifier")
    view_id: ViewId = Field(
        ...,
        description="Identifier of the received view",
    )
    origin_tick: AwareDatetime = Field(
        ..., description="Time of the compose tick that produced the document"
    )
    source_document_digest: ViewDigest = Field(
        ...,
        description="Digest of the document the app received, as 'sha256:<64 lowercase hex>'",
    )
    received_at: AwareDatetime = Field(
        ..., description="Time the app received the document"
    )
    decode_outcome: EnumViewDecodeOutcome = Field(
        ..., description="Outcome of decoding the received document"
    )
    decode_cause: EnumEmptyStateReason | None = Field(
        default=None, description="Empty-state reason for a partial decode or refusal"
    )

    @model_validator(mode="after")
    def validate_decode_cause(self) -> Self:
        """Require a cause exactly when the decode outcome needs one.

        Raises:
            ValueError: If a decoded document has a cause, or a decode with a
                cause or refusal omits its cause.
        """
        if self.decode_outcome == EnumViewDecodeOutcome.DECODED:
            if self.decode_cause is not None:
                raise ValueError("decoded requires decode_cause to be None")
        elif self.decode_cause is None:
            raise ValueError("decoded-with-cause and refused require decode_cause")
        return self
