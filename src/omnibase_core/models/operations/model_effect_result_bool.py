# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Effect Result Bool Model.

Boolean result for effect operations (e.g., event emissions).
"""

from typing import Literal

from pydantic import BaseModel


class ModelEffectResultBool(BaseModel):
    """Boolean result for effect operations (e.g., event emissions)."""

    result_type: Literal["bool"] = "bool"
    value: bool
