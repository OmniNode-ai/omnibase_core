# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
from omnibase_core.validation.checker_routing_authority import check_routing_authority


def handle(facts: object) -> object:
    return check_routing_authority(facts)
