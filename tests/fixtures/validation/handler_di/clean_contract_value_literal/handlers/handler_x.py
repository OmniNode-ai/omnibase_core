# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
def publish(bus, contract, payload):
    bus.publish(contract.publish_topics[0], payload)
