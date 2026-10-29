# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
# timeout=30
# _POLL_TIMEOUT_MS = 1000
# time.sleep(5)
def poll(client, timeout):
    return client.get(timeout=timeout)
