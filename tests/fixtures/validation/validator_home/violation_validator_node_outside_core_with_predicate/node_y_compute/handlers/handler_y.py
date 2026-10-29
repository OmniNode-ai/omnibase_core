# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
import re

from omnibase_core.validation.checker_routing_authority import check_routing_authority

LOCAL = re.compile(r"y")


def handle(text: str) -> bool:
    return LOCAL.search(text) is not None and check_routing_authority is not None
