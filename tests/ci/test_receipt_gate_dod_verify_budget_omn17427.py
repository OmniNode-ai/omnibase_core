# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Pin the hosted dod-verify job budget for OMN-17427 so a large caller contract
gets a verdict instead of a timeout cancel.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.unit

WORKFLOW_PATH = (
    Path(__file__).resolve().parents[2] / ".github" / "workflows" / "receipt-gate.yml"
)


def test_dod_verify_job_budget_is_sixty_minutes() -> None:
    workflow = yaml.safe_load(WORKFLOW_PATH.read_text())
    assert workflow["jobs"]["dod-verify"]["timeout-minutes"] == 60


def test_verify_noop_job_budget_unchanged() -> None:
    workflow = yaml.safe_load(WORKFLOW_PATH.read_text())
    assert workflow["jobs"]["verify"]["timeout-minutes"] == 5
