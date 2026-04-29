# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Wire CI gate declaration model."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelWireCiGate(BaseModel):
    """CI gate declaration in a wire schema contract."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    test_file: str = Field(..., description="Path to the handshake test file")
    test_class: str = Field(default="", description="Test class name")
