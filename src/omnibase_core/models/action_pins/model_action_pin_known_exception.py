# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One first-party ref the overlay admits as a sha pin, with the reason (OMN-17427)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelActionPinKnownException"]


class ModelActionPinKnownException(BaseModel):
    """A first-party ``uses:`` value that has no dev-merge tag yet.

    ``uses`` is the whole value as written (``owner/repo/path@<sha>``), so a
    moved sha is a new finding. The entry is reported as a WARN while it is in
    use and as a WARN to remove once no file uses it.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    uses: str = Field(min_length=3, pattern=r"^[^@\s]+@[^@\s]+$")
    reason: str = Field(min_length=10)
