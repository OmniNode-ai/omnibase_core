# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
def get_config(container):
    return container.get_service(ProtocolConfig)
