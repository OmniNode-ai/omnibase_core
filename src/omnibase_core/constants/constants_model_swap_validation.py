# SPDX-FileCopyrightText: 2026 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Shared open quality-floor bounds for model-swap validation contracts."""

from typing import Final

from pydantic import Field
from pydantic.fields import FieldInfo

MODEL_SWAP_QUALITY_FLOOR_BOUNDS: Final[FieldInfo] = Field(gt=0.8, lt=1.0)

__all__ = ["MODEL_SWAP_QUALITY_FLOOR_BOUNDS"]
