# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
class HandlerX:
    def __init__(self, container):
        self._bus = container.get_service(ProtocolEventBus)
