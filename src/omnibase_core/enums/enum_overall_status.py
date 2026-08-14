# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Overall status enum for contract.verify.replay verification reports.

Represents the aggregated outcome of an entire verification run: pass
(every check ran and passed), fail (one or more checks failed), skip (no
check failed, but at least one did not run), or error (the verification run
itself encountered an unexpected exception).

``SKIP`` exists because a skipped check is an *absence of evidence*, not
evidence of correctness. Folding it into ``PASS`` makes an unverified package
indistinguishable from a verified one (OMN-15862).

.. versionadded:: 0.20.0
.. versionchanged:: 0.20.1
   Added :attr:`EnumOverallStatus.SKIP` (OMN-15862).
"""

from enum import Enum

__all__ = ["EnumOverallStatus"]


class EnumOverallStatus(str, Enum):
    """Aggregated outcome of a verification report.

    Precedence when aggregating per-check results is FAIL > SKIP > PASS:
    any failed check makes the run a FAIL; otherwise any skipped check makes
    the run a SKIP; only a run in which every check executed and passed is a
    PASS.

    Attributes:
        PASS: Every check ran and passed. Nothing was skipped.
        FAIL: One or more checks failed.
        SKIP: No check failed, but at least one check did not run, so the
            package is *not* verified. Never treat SKIP as PASS.
        ERROR: The verification run itself raised an unexpected exception.
    """

    PASS = "pass"
    FAIL = "fail"
    SKIP = "skip"
    ERROR = "error"
