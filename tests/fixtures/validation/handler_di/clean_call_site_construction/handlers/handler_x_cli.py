# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
def main(container, req):
    return container.get_service(HandlerX).handle(req)
