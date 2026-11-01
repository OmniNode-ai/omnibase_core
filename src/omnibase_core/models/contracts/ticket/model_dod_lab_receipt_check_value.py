# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelDodLabReceiptCheckValue — the typed shape of a lab_receipt check. OMN-21831"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelDodLabReceiptCheckValue(BaseModel):
    """What a ticket contract states about the lab receipt its change needs.

    The lab-receipt checker reads a check of this type as the cited
    install-and-observe criterion instead of matching the criterion's text.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", str_strip_whitespace=True)

    installer: str = Field(
        min_length=1,
        description="Declared installer that puts the branch revision on the lab",
    )
    observation: str = Field(
        min_length=1,
        description="What is observed running at the PR head once installed",
    )


__all__ = ["ModelDodLabReceiptCheckValue"]
