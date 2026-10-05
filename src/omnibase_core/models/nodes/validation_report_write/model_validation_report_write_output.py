# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Output model for the validation_report_write EFFECT node."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

__all__ = ["ModelValidationReportWriteOutput"]


class ModelValidationReportWriteOutput(BaseModel):
    """Where the report was written and how many bytes it holds."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    report_path: str
    bytes_written: int
