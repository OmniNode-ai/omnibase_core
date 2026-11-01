# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The ``dod_verify`` overlay document body (OMN-21504)."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


class ModelDodVerifyOverlay(BaseModel):
    """The tickets the receipt gate refuses as a pull request's only citation.

    A parent ticket groups task tickets and carries no contract of its own, so a
    pull request that cites only a parent has no task whose definition of done
    it could be verified against.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    schema_version: Literal["dod_verify.v1"] = Field(
        ..., description="Schema version tag."
    )
    parent_tickets: tuple[
        Annotated[str, StringConstraints(pattern=r"^OMN-[0-9]+$")], ...
    ] = Field(
        default=(),
        description="Ticket ids refused when they are the only ticket a PR cites.",
    )


__all__ = ["ModelDodVerifyOverlay"]
