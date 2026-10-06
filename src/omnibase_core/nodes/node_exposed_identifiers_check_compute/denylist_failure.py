# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Configuration failure for a missing or malformed hash-only denylist."""


class DenylistError(RuntimeError):
    """The denylist is missing, malformed, or self-inconsistent."""
