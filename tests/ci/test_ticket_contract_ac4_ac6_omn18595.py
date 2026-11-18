# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OMN-18595: the ticket contract carries every criterion the live ticket carries.

AC4 to AC6 are settled in omnibase_infra, so each is declared under requirements
and bound by a ``local_done_gate`` evidence item here.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

pytestmark = pytest.mark.unit

CONTRACT = Path(__file__).resolve().parents[2] / "contracts" / "OMN-18595.yaml"
RELEASE_TRAIN_ACS = {"AC4", "AC5", "AC6"}


def _load() -> dict[str, Any]:
    loaded = yaml.safe_load(CONTRACT.read_text())
    assert isinstance(loaded, dict)
    return loaded


def test_ac4_to_ac6_are_declared() -> None:
    declared = {ac["id"] for req in _load()["requirements"] for ac in req["acceptance"]}
    assert declared >= RELEASE_TRAIN_ACS


def test_ac4_to_ac6_are_bound_by_local_done_gate_evidence() -> None:
    bound = {
        ac
        for item in _load()["dod_evidence"]
        if item.get("execution_scope") == "local_done_gate"
        for ac in item.get("binds_ac", [])
    }
    assert bound >= RELEASE_TRAIN_ACS
