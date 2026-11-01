# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
from omnibase_core.contracts.contract_loader import load_contract


class HandlerX:
    def handle(self, tag: str) -> bool:
        return tag.startswith(load_contract().dev_tag_pattern)
