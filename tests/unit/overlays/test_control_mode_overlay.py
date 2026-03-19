# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Unit tests for control mode session overlay (OMN-5546).

Tests cover:
- CONTROL_MODE_REMOVED_CAPABILITIES constant content
- classify_treatment_group with full/empty/partial capability sets
- is_control_session agreement with classify_treatment_group
- build_control_mode_patch produces correct remove operations
"""

from __future__ import annotations

import pytest

from omnibase_core.overlays.control_mode import (
    CONTROL_MODE_REMOVED_CAPABILITIES,
    build_control_mode_patch,
    classify_treatment_group,
    is_control_session,
)

pytestmark = pytest.mark.unit


class TestControlModeRemovedCapabilities:
    """Validate the capability constant."""

    def test_is_frozenset(self) -> None:
        assert isinstance(CONTROL_MODE_REMOVED_CAPABILITIES, frozenset)

    def test_contains_expected_capabilities(self) -> None:
        expected = {
            "intelligence_pattern_injection",
            "intelligence_local_model_routing",
            "intelligence_validator_hooks",
            "intelligence_memory_rag_retrieval",
        }
        assert expected == CONTROL_MODE_REMOVED_CAPABILITIES

    def test_nonempty(self) -> None:
        assert len(CONTROL_MODE_REMOVED_CAPABILITIES) > 0


class TestClassifyTreatmentGroup:
    """Validate treatment group classification logic."""

    def test_full_capabilities_returns_treatment(self) -> None:
        caps = set(CONTROL_MODE_REMOVED_CAPABILITIES) | {"some.other.cap"}
        assert classify_treatment_group(caps) == "treatment"

    def test_exact_capabilities_returns_treatment(self) -> None:
        caps = set(CONTROL_MODE_REMOVED_CAPABILITIES)
        assert classify_treatment_group(caps) == "treatment"

    def test_empty_set_returns_control(self) -> None:
        assert classify_treatment_group(set()) == "control"

    def test_unrelated_capabilities_returns_control(self) -> None:
        caps = {"unrelated.cap_a", "unrelated.cap_b"}
        assert classify_treatment_group(caps) == "control"

    def test_partial_capabilities_returns_unknown(self) -> None:
        # Only one of the intelligence capabilities present
        caps = {"intelligence_pattern_injection"}
        assert classify_treatment_group(caps) == "unknown"

    def test_all_but_one_returns_unknown(self) -> None:
        caps = set(CONTROL_MODE_REMOVED_CAPABILITIES)
        caps.discard("intelligence_memory_rag_retrieval")
        assert classify_treatment_group(caps) == "unknown"


class TestIsControlSession:
    """Validate is_control_session matches classify_treatment_group 'control'."""

    def test_control_when_no_intelligence_caps(self) -> None:
        assert is_control_session(set()) is True

    def test_not_control_when_all_caps_present(self) -> None:
        caps = set(CONTROL_MODE_REMOVED_CAPABILITIES)
        assert is_control_session(caps) is False

    def test_not_control_when_partial_caps(self) -> None:
        caps = {"intelligence_pattern_injection"}
        assert is_control_session(caps) is False

    def test_agrees_with_classify_control(self) -> None:
        """is_control_session should be True iff classify returns 'control'."""
        test_sets: list[set[str]] = [
            set(),
            {"unrelated.cap"},
            set(CONTROL_MODE_REMOVED_CAPABILITIES),
            {"intelligence_pattern_injection"},
        ]
        for caps in test_sets:
            expected = classify_treatment_group(caps) == "control"
            assert is_control_session(caps) is expected, f"Mismatch for {caps}"


class TestBuildControlModePatch:
    """Validate the patch factory function."""

    def test_patch_removes_all_control_capabilities(self) -> None:
        patch = build_control_mode_patch()
        assert patch.capability_outputs__remove is not None
        removed = set(patch.capability_outputs__remove)
        assert removed == CONTROL_MODE_REMOVED_CAPABILITIES

    def test_patch_has_no_add_operations(self) -> None:
        patch = build_control_mode_patch()
        assert patch.capability_outputs__add is None
        assert patch.capability_inputs__add is None
        assert patch.handlers__add is None
        assert patch.dependencies__add is None

    def test_patch_extends_provided_profile(self) -> None:
        patch = build_control_mode_patch()
        assert patch.extends is not None
        assert patch.extends.profile == "compute_pure"
