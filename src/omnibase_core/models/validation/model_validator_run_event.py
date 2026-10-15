# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Validator run and fire events (OMN-17427).

RULING 2026-10-14T20:01:09Z: generic validators trigger events when they run
and when they fire, so the work ledger can answer which checks ever catch
anything. A ``run`` event says a validator ran and with what verdict; a
``fire`` event says one rule of it produced a FAIL, ERROR or WARN finding.
The repository, pull request or commit and duration come from the runner that
collects the events, which knows them; the report does not.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelValidatorRunEvent"]


class ModelValidatorRunEvent(BaseModel):
    """One run or fire event of a validator, taken from its canonical report."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    kind: Literal["run", "fire"] = Field(
        description="'run' once per report; 'fire' once per finding that fired."
    )
    validator_name: str = Field(description="Validator that ran.")
    report_ref: str = Field(description="Report these events were derived from.")
    emitted_at: str = Field(description="ISO-8601 timestamp of the report.")
    verdict: Literal["PASS", "WARN", "FAIL", "ERROR"] | None = Field(
        default=None, description="Overall status of the run; set on 'run' only."
    )
    fired_count: int | None = Field(
        default=None, ge=0, description="Findings that fired; set on 'run' only."
    )
    severity: Literal["WARN", "FAIL", "ERROR"] | None = Field(
        default=None, description="Severity of the finding; set on 'fire' only."
    )
    rule_name: str | None = Field(
        default=None,
        description="Rule that fired, else the validator; set on 'fire' only.",
    )
    location: str | None = Field(
        default=None, description="Finding location; set on 'fire' only."
    )
