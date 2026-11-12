# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The release-consistency report: one line per check and an overall verdict."""

from typing import Literal

from pydantic import BaseModel, ConfigDict

ReleaseConsistencyVerdict = Literal["AGREE", "MISMATCH", "UNKNOWN"]

_EXIT_CODES: dict[ReleaseConsistencyVerdict, int] = {
    "AGREE": 0,
    "MISMATCH": 1,
    "UNKNOWN": 2,
}


class ModelReleaseConsistencyReport(BaseModel):
    """AGREE when every check agrees, MISMATCH when any differs, else UNKNOWN.

    Each line opens with its own state (``AGREE``, ``MISMATCH`` or
    ``UNKNOWN``) followed by what was compared.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    tag: str
    verdict: ReleaseConsistencyVerdict
    lines: tuple[str, ...] = ()

    @property
    def exit_code(self) -> int:
        """0 AGREE, 1 MISMATCH, 2 UNKNOWN."""
        return _EXIT_CODES[self.verdict]
