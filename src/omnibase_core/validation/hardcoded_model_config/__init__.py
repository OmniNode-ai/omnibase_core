# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Hardcoded model-configuration validator (OMN-19252).

Task A1 of knowledge-base-internal
``beta/plans/2026-09-23-remove-hardcoded-model-config.md``: a blocking guard that
refuses NEW hardcoded lab model configuration (lab and private hosts, inference
endpoints, model ids, retired lab values, loaded example files) while a
content-keyed baseline tolerates the pre-existing set and may only shrink.

* ``models``: the policy, scan input, finding, scan result and baseline entry.
* ``handler``: ``HandlerHardcodedModelConfigCompute`` and the pure ``scan``.
* ``runtime_hardcoded_model_config``: the EFFECT boundary and CLI (the
  ``check-hardcoded-model-config-compute`` pre-commit hook).
* ``policy.yaml``: the whole allowlist. There is no inline suppression marker.
"""

from __future__ import annotations

from omnibase_core.validation.hardcoded_model_config.handler import (
    HandlerHardcodedModelConfigCompute,
    scan,
)
from omnibase_core.validation.hardcoded_model_config.models import (
    ModelHardcodedModelConfigBaselineEntry,
    ModelHardcodedModelConfigFinding,
    ModelHardcodedModelConfigPolicy,
    ModelHardcodedModelConfigScanInput,
    ModelHardcodedModelConfigScanResult,
)

__all__ = [
    "HandlerHardcodedModelConfigCompute",
    "ModelHardcodedModelConfigBaselineEntry",
    "ModelHardcodedModelConfigFinding",
    "ModelHardcodedModelConfigPolicy",
    "ModelHardcodedModelConfigScanInput",
    "ModelHardcodedModelConfigScanResult",
    "scan",
]
