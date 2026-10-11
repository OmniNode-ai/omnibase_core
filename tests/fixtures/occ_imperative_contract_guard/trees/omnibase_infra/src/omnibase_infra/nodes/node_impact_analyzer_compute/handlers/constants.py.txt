# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

# Copyright (c) 2026 OmniNode Team
"""Constants for the impact analyzer compute handler.

All scoring thresholds, multipliers, and reason codes are defined here
to ensure a single source of truth for the deterministic scoring logic.
"""

from __future__ import annotations

MERGE_POLICY_ORDER: dict[str, int] = {
    "none": 0,
    "warn": 1,
    "require": 2,
    "strict": 3,
}

SCOPE_MULTIPLIER_STRUCTURAL: float = 1.0
SCOPE_MULTIPLIER_PR: float = 0.7

POLICY_FLOORS: dict[str, float] = {
    "none": 0.0,
    "warn": 0.0,
    "require": 0.3,
    "strict": 0.5,
}

ACTION_THRESHOLD_REGENERATE: float = 0.8
ACTION_THRESHOLD_REVIEW: float = 0.5

STRUCTURAL_TRIGGER_TYPES: frozenset[str] = frozenset(
    {
        "contract_changed",
        "schema_changed",
    }
)

REASON_CODES: frozenset[str] = frozenset(
    {
        "contract_yaml_changed",
        "handler_routing_changed",
        "event_bus_topics_changed",
        "script_changed",
        "schema_changed",
        "config_changed",
        "manual_reconciliation",
        "full_repo_reconciliation",
    }
)
