# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""One journalled mutation from a sprint roll (OMN-20397).

Written to the journal BEFORE it is sent, which is the whole point of the record: a run
interrupted midway still leaves a manifest that undoes what it managed to do. `before`
is what the field held, so an undo replays prior values rather than recomputing them --
recomputation would re-derive from a board that has since moved.
"""

from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelSprintRollWrite"]


class ModelSprintRollWrite(BaseModel):
    """A single field change on a single issue."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    issue_uuid: str
    identifier: str
    field: str
    #: Always a tuple of ids, never a bare string. A scalar field such as `projectId`
    #: carries a one-element tuple, and `labelIds` carries the whole set. One shape
    #: rather than `str | tuple[str, ...]`: that union reads as primitive soup to the
    #: union gate, and it made every reader branch on the field's arity as well as its
    #: name. `None` means the field held nothing.
    before: tuple[str, ...] | None
    after: tuple[str, ...] | None
    at: dt.datetime = Field(default_factory=lambda: dt.datetime.now(dt.UTC))
