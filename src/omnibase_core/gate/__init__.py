# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OmniGate core helpers."""

from omnibase_core.gate.config_loader import (
    DEFAULT_OMNIGATE_CONFIG_NAMES,
    discover_omnigate_config,
    load_omnigate_config,
)
from omnibase_core.gate.diff_hash import (
    DETERMINISTIC_DIFF_FLAGS,
    compute_config_hash,
    compute_diff_hash,
    compute_pr_diff_hash,
    compute_staged_diff_hash,
)
from omnibase_core.gate.receipt_canonical import (
    canonical_receipt_payload,
    compute_receipt_schema_fingerprint,
)

__all__ = [
    "DEFAULT_OMNIGATE_CONFIG_NAMES",
    "DETERMINISTIC_DIFF_FLAGS",
    "canonical_receipt_payload",
    "compute_config_hash",
    "compute_diff_hash",
    "compute_pr_diff_hash",
    "compute_receipt_schema_fingerprint",
    "compute_staged_diff_hash",
    "discover_omnigate_config",
    "load_omnigate_config",
]
