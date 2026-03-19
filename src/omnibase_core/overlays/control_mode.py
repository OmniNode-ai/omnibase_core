# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Control mode session overlay for A/B savings measurement.

A control session has all intelligence capabilities removed so that raw
Claude Code token usage can be measured as a baseline. Comparing control
sessions against treatment sessions (with full intelligence) yields the
token savings estimate.

Part of the Token Savings Estimation epic (OMN-5546).

.. versionadded:: 0.29.0
"""

from __future__ import annotations

from omnibase_core.models.contracts.model_contract_patch import ModelContractPatch
from omnibase_core.models.contracts.model_profile_reference import ModelProfileReference

__all__ = [
    "CONTROL_MODE_REMOVED_CAPABILITIES",
    "build_control_mode_patch",
    "classify_treatment_group",
    "is_control_session",
]

CONTROL_MODE_REMOVED_CAPABILITIES: frozenset[str] = frozenset(
    {
        "intelligence_pattern_injection",
        "intelligence_local_model_routing",
        "intelligence_validator_hooks",
        "intelligence_memory_rag_retrieval",
    }
)


def is_control_session(resolved_capabilities: set[str]) -> bool:
    """A session is control only when ALL intelligence capabilities are absent."""
    return CONTROL_MODE_REMOVED_CAPABILITIES.isdisjoint(resolved_capabilities)


def classify_treatment_group(resolved_capabilities: set[str]) -> str:
    """Classify a session into a treatment group.

    Returns:
        ``"control"`` — all intelligence capabilities absent.
        ``"treatment"`` — all intelligence capabilities present.
        ``"unknown"`` — partial/mixed capability state.
    """
    has_all = CONTROL_MODE_REMOVED_CAPABILITIES.issubset(resolved_capabilities)
    has_none = CONTROL_MODE_REMOVED_CAPABILITIES.isdisjoint(resolved_capabilities)
    if has_none:
        return "control"
    if has_all:
        return "treatment"
    return "unknown"


def build_control_mode_patch() -> ModelContractPatch:
    """Build a ``ModelContractPatch`` that removes all intelligence capabilities.

    The returned patch is intended to be applied as a SESSION-scope overlay
    via :meth:`ContractMergeEngine.merge_with_overlays`.
    """
    return ModelContractPatch(
        extends=ModelProfileReference(profile="compute_pure", version="1.0.0"),
        capability_outputs__remove=sorted(CONTROL_MODE_REMOVED_CAPABILITIES),
    )
