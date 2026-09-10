# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Internal match tuple returned by node-dispatch selection."""

from typing import NamedTuple

from omnibase_core.runtime.dispatch_entry import DispatchEntry


class DispatchMatch(NamedTuple):
    """One ordered route and dispatcher selection."""

    route_id: str
    entry: DispatchEntry


__all__ = ["DispatchMatch"]
