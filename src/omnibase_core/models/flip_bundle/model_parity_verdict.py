# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Executed parity evidence for a flip proof."""

from pydantic import BaseModel, ConfigDict


class ModelParityVerdict(BaseModel):
    """An EXECUTED verdict over a hand-flip receipt's declared parity test ids."""

    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)

    executed: bool
    green: bool
    detail: str
