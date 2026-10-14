# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""OMN-20074 contract bindings must identify exactly one criterion and item."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.unit

CONTRACT = Path(__file__).resolve().parents[2] / "contracts" / "OMN-20074.yaml"


def test_requirement_ids_are_unique() -> None:
    contract = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    counts = Counter(item["id"] for item in contract["requirements"])
    assert not {key: count for key, count in counts.items() if count > 1}


def test_acceptance_ids_are_unique() -> None:
    contract = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    counts = Counter(
        ac["id"]
        for requirement in contract["requirements"]
        for ac in requirement["acceptance"]
    )
    assert not {key: count for key, count in counts.items() if count > 1}


def test_evidence_ids_are_unique() -> None:
    contract = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    counts = Counter(item["id"] for item in contract["dod_evidence"])
    assert not {key: count for key, count in counts.items() if count > 1}


def test_evidence_bindings_name_existing_criteria() -> None:
    contract = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    criteria = {
        ac["id"]
        for requirement in contract["requirements"]
        for ac in requirement["acceptance"]
    }
    bindings = {
        ac for item in contract["dod_evidence"] for ac in item.get("binds_ac", [])
    }
    assert bindings <= criteria
