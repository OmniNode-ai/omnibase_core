# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""A migrated one-off validator is gone and its generic-format replacement stands (OMN-21503).

The one-off ``handlers/handler_<id>.py`` + ``handler_<id>_cli.py`` pair is deleted, not
kept beside the new ``checker_<id>.py`` + ``validator_<id>.py`` +
``contracts/<id>.validation.yaml`` triple, and K10 finds the triple clean.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from omnibase_core.validation.validator_checker_rule_data import (
    ValidatorCheckerRuleData,
)

pytestmark = pytest.mark.unit

VALIDATION = (
    Path(__file__).resolve().parents[2] / "src" / "omnibase_core" / "validation"
)
MIGRATED = (
    "public_runner_placement",
    "event_registry_drift",
    "version_floor_consumers",
)


@pytest.mark.parametrize("validator_id", MIGRATED)
def test_the_one_off_pair_is_deleted(validator_id: str) -> None:
    for name in (f"handler_{validator_id}", f"handler_{validator_id}_cli"):
        assert importlib.util.find_spec(f"omnibase_core.handlers.{name}") is None


@pytest.mark.parametrize("validator_id", MIGRATED)
def test_the_generic_triple_stands_and_k10_finds_it_clean(validator_id: str) -> None:
    triple = (
        VALIDATION / f"checker_{validator_id}.py",
        VALIDATION / f"validator_{validator_id}.py",
        VALIDATION / "contracts" / f"{validator_id}.validation.yaml",
    )
    assert all(p.is_file() for p in triple)
    issues = ValidatorCheckerRuleData().validate(list(triple[:2])).issues
    assert issues == []
