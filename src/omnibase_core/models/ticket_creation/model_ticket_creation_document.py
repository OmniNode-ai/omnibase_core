# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""A recorded ticket payload the file validator judges (OMN-22850)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, JsonValue


class ModelTicketCreationDocument(BaseModel):
    """One payload as the tracker write would receive it, and the context it was filed from."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    tool_input: JsonValue = Field(description="The save_issue payload, as filed")
    lane: str | None = Field(
        default=None,
        description="The filing lane's identity; None when the payload is not from a lane or node",
    )
    ledger_path: str | None = Field(
        default=None,
        description="Rolling ledger a Diagnosis citation resolves against; None resolves nothing",
    )
    route: str | None = Field(
        default=None,
        description="Who built the payload: 'node' (the ticket node), 'raw' (by hand), or None when not stated",
    )
    route_switch: str | None = Field(
        default=None,
        description="The overlay's route switch, 'allow' or 'refuse'; None takes the contract default",
    )
    current_description: str | None = Field(
        default=None,
        description="The updated ticket's current description, so a contract block edit can be judged",
    )
