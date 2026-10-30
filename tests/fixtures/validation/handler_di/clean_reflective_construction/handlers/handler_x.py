# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
def build(container):
    return container.get_service(ProtocolBackend)
