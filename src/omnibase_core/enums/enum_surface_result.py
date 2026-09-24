# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Surface-Result Enum (OMN-16177, typed work ledger).

How the work that held a surface lease ended, recorded on the release of that
lease (``work.hold.released``). Paired with ``surface_restored``.
"""

from enum import StrEnum, unique


@unique
class EnumSurfaceResult(StrEnum):
    """Outcome of the work that held a surface."""

    PASS = "pass"
    """The run on the surface completed and its proof passed."""

    FAIL = "fail"
    """The run on the surface completed and its proof failed."""

    ABORTED = "aborted"
    """The run never completed, including a lease reaped after it expired."""


__all__: list[str] = ["EnumSurfaceResult"]
