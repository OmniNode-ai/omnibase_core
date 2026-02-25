# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Check status enum for contract.verify.replay individual check results.

Represents the outcome of a single static verification check: pass, fail,
or skip (when the check is intentionally not executed).

.. versionadded:: 0.20.0
"""

from enum import Enum

__all__ = ["EnumCheckStatus"]


class EnumCheckStatus(str, Enum):
    """Outcome of a single verification check.

    Attributes:
        PASS: The check passed successfully.
        FAIL: The check detected a violation.
        SKIP: The check was intentionally skipped (e.g. not implemented
            for the requested tier, or disabled via options).
    """

    PASS = "pass"
    FAIL = "fail"
    SKIP = "skip"
