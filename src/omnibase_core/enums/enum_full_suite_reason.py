# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Full-suite escalation reason for change-aware test selection (OMN-14700).

Why the governed test selector escalated a change-set to the full suite instead
of a narrowed shard set. Consumed by
:class:`~omnibase_core.models.nodes.test_selector.model_test_selection.ModelTestSelection`
and produced by ``node_test_selector_compute``. Promoted verbatim from
``scripts/ci/test_selection_models.py`` (same string values) so the node and the
legacy ``detect_test_paths.py`` oracle share ONE enum (no fork).
"""

from __future__ import annotations

from enum import StrEnum

__all__ = ["EnumFullSuiteReason"]


class EnumFullSuiteReason(StrEnum):
    SHARED_MODULE = "shared_module"
    THRESHOLD_MODULES = "threshold_modules"
    TEST_INFRASTRUCTURE = "test_infrastructure"
    MAIN_BRANCH = "main_branch"
    MERGE_GROUP = "merge_group"
    SCHEDULED = "scheduled"
    FEATURE_FLAG_OFF = "feature_flag_off"
