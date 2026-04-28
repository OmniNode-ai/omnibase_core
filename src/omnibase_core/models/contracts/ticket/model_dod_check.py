# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelDodCheck — executable check entry for a DoD evidence item. OMN-10066

Absorbs OCC's ModelDodCheck fields so OCC can re-export from core and delete
its local definition (Part B of OMN-10066).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ModelDodCheck(BaseModel):
    """A single executable check for a DoD evidence item.

    Both fields default to empty string so existing core callers that omit
    them continue to construct without error.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    check_type: str = ""
    check_value: str = ""


__all__ = ["ModelDodCheck"]
