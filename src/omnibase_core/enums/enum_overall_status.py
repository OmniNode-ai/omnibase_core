# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Overall status enum for contract.verify.replay verification reports.

Represents the aggregated outcome of an entire verification run: pass
(all required checks passed), fail (one or more checks failed), or error
(the verification run itself encountered an unexpected exception).

.. versionadded:: 0.20.0
"""

from enum import Enum

__all__ = ["EnumOverallStatus"]


class EnumOverallStatus(str, Enum):
    """Aggregated outcome of a verification report.

    Attributes:
        PASS: All required checks passed.
        FAIL: One or more checks failed.
        ERROR: The verification run itself raised an unexpected exception.
    """

    PASS = "pass"
    FAIL = "fail"
    ERROR = "error"
