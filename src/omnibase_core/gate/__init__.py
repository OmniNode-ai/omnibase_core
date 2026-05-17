# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure OmniGate helpers owned by omnibase_core."""

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

__all__ = [
    "DEFAULT_OMNIGATE_CONFIG_NAMES",
    "DETERMINISTIC_DIFF_FLAGS",
    "compute_config_hash",
    "compute_diff_hash",
    "compute_pr_diff_hash",
    "compute_staged_diff_hash",
    "discover_omnigate_config",
    "load_omnigate_config",
]
