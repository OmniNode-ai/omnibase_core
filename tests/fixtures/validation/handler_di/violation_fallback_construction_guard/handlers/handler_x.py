# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
class HandlerX:
    def __init__(self, contract=None):
        if contract is None:
            contract = load_contract()
        self._contract = contract
