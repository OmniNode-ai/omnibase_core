# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""The sprint roll's transport error (OMN-20397).

Its own module because the single-class-per-file gate allows one non-enum class per
file, and `SprintRollJournal` is the class that belongs with the roll's write ordering.

NOT NAMED `error_*`, AND NOT IN `errors/`, deliberately. Those two gates conflict for a
file like this one: `canonical-file-shape` admits only `nodes`, `handlers`, `models`,
`protocols`, `contracts`, `enums`, `tests` and `docs`, so it refuses a new file under
`errors/`; `validate-file-locations` requires any `error_*.py` to BE in `errors/`. The
honest reading is that this is not a shared core error at all -- it is one node's
transport failure, raised by the caller's adapter and read by this node's retry policy --
so it belongs in the node package under a name that does not claim the shared-error
convention.

`status` is the HTTP status when the caller's adapter knows one, and None otherwise. It
is the only thing core needs to know about HTTP, and it arrives as DATA rather than as an
imported client type -- ADR-005 forbids a transport import anywhere in omnibase_core, so
the adapter that knows what a 503 is lives with the client, outside this package, and
raises this.
"""

from __future__ import annotations

__all__ = ["LinearTransportError"]


class LinearTransportError(RuntimeError):
    """A Linear call failed, carrying the status when the caller could classify it."""

    def __init__(self, message: str, *, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status
