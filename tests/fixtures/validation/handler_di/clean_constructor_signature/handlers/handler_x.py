# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
class HandlerX:
    def __init__(self, container: ModelONEXContainer) -> None:
        self._bus = container.get_service(ProtocolEventBus)
