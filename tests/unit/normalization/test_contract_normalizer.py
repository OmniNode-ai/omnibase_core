# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for contract_normalizer (OMN-9765, parent epic OMN-9757).

Phase 2 Task 8: ``normalize_omnimarket_v0_contract`` rewrites the
legacy omnimarket v0 contract shape (top-level ``handler``,
``descriptor``, ``terminal_event`` blocks) into the canonical
contract layout.
"""

from __future__ import annotations

import copy

import pytest

from omnibase_core.normalization.contract_normalizer import (
    is_omnimarket_v0,
    normalize_omnimarket_v0_contract,
)


@pytest.mark.unit
class TestIsOmnimarketV0:
    """Detection helper for the legacy omnimarket v0 contract shape."""

    def test_detects_omnimarket_v0_shape(self) -> None:
        raw = {
            "handler": {
                "module": "omnimarket.nodes.x.handlers.h",
                "class": "NodeX",
                "input_model": "...",
            },
            "descriptor": {"node_archetype": "compute"},
            "terminal_event": "onex.evt.omnimarket.x-completed.v1",
        }
        assert is_omnimarket_v0(raw) is True

    def test_non_omnimarket_v0_shape(self) -> None:
        raw = {"name": "node_foo", "node_type": "EFFECT_GENERIC"}
        assert is_omnimarket_v0(raw) is False


@pytest.mark.unit
class TestNormalizeOmnimarketV0Contract:
    """Rewrite legacy v0 contract dicts to the canonical layout."""

    def test_extracts_input_model_from_handler(self) -> None:
        raw = {
            "name": "node_aislop_sweep",
            "handler": {
                "module": "omnimarket.nodes.node_aislop_sweep.handlers.h",
                "class": "NodeAislopSweep",
                "input_model": "omnimarket.nodes.node_aislop_sweep.handlers.h.AislopSweepRequest",
            },
            "descriptor": {"node_archetype": "compute", "timeout_ms": 120000},
            "terminal_event": "onex.evt.omnimarket.aislop-sweep-completed.v1",
        }
        result = normalize_omnimarket_v0_contract(raw)
        assert (
            result.get("input_model")
            == "omnimarket.nodes.node_aislop_sweep.handlers.h.AislopSweepRequest"
        )
        assert "handler" not in result
        assert "descriptor" not in result
        assert "terminal_event" not in result

    def test_does_not_mutate_input(self) -> None:
        raw = {
            "handler": {"module": "m", "class": "C", "input_model": "m.M"},
            "descriptor": {},
        }
        raw_copy = copy.deepcopy(raw)
        normalize_omnimarket_v0_contract(raw)
        assert raw == raw_copy
