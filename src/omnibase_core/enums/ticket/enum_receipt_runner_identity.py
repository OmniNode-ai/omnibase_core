# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""EnumReceiptRunnerIdentity — producers whose receipts are executed evidence."""

from __future__ import annotations

from enum import StrEnum


class EnumReceiptRunnerIdentity(StrEnum):
    """Identities a product-repo receipt runner writes on what it produces.

    The runner records its identity as ``runner`` on every receipt it executes
    and as ``superseder`` on every supersession record it files. Two readers
    key on it:

    * the OCC append-only gate (``validator_occ_append_only``), which refuses a
      branch commit that rewrites or deletes a record naming the runner;
    * the supersession resolver (``validator_receipt_supersession``), which
      lets a PASS clear a prior FAIL only when the runner produced it
      (OMN-19050, AC6), so a hand-authored receipt cannot clear a FAIL.

    Members
    -------
    OMNIMARKET_CI_OCC_RECEIPT_RUNNER
        omnimarket ``scripts/ci/occ_receipt_runner.py``.
    """

    OMNIMARKET_CI_OCC_RECEIPT_RUNNER = "omnimarket-ci occ-receipt-runner"


def is_receipt_runner_identity(value: object) -> bool:
    """Whether ``value`` is exactly one of the runner identities."""
    return isinstance(value, str) and value in EnumReceiptRunnerIdentity


__all__ = ["EnumReceiptRunnerIdentity", "is_receipt_runner_identity"]
