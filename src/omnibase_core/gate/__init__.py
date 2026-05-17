# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure OmniGate helpers owned by omnibase_core."""

from omnibase_core.gate.config_loader import (
    DEFAULT_OMNIGATE_CONFIG_NAMES,
    discover_omnigate_config,
    load_omnigate_config,
)

__all__ = [
    "DEFAULT_OMNIGATE_CONFIG_NAMES",
    "discover_omnigate_config",
    "load_omnigate_config",
]
