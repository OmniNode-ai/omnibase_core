# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The one ticket completion predicate (OMN-22969).

A ticket is done when its phase is DONE and the four completion checks hold.
Every ticket model in core states that policy by calling this function, so the
policy has exactly one definition.
"""

from __future__ import annotations


def is_ticket_complete(
    *,
    phase_done: bool,
    questions_complete: bool,
    spec_complete: bool,
    verification_complete: bool,
    gates_complete: bool,
) -> bool:
    """Return True only when the phase is DONE and every completion check holds."""
    return (
        phase_done
        and questions_complete
        and spec_complete
        and verification_complete
        and gates_complete
    )


__all__ = ["is_ticket_complete"]
