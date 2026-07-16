# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Pydantic output contract for change-aware test selection.

Promotion bridge (OMN-14700): the canonical definitions now live in
``omnibase_core.models.nodes.test_selector.model_test_selection`` so the
RSD-regenerated ``node_test_selector_compute`` and this legacy
``detect_test_paths.py`` oracle share ONE model (no fork). This module re-exports
them so the oracle and its tests keep importing ``scripts.ci.test_selection_models``
unchanged until the CI + pre-push swap follow-up (OMN-14700 DoD 2/3) deletes the
script.
"""

from __future__ import annotations

from omnibase_core.enums.enum_full_suite_reason import EnumFullSuiteReason
from omnibase_core.models.nodes.test_selector.model_test_selection import (
    ModelTestSelection,
    ModuleName,
    TestPath,
)

__all__ = [
    "EnumFullSuiteReason",
    "ModelTestSelection",
    "ModuleName",
    "TestPath",
]
