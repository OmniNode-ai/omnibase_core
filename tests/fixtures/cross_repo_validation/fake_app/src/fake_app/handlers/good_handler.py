# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""GOOD: This handler imports from allowed public APIs."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fake_core.protocols.protocol_foo import ProtocolFoo
    from fake_infra.protocols.protocol_bar import ProtocolBar


class GoodHandler:
    """Handler that follows import rules."""

    def __init__(self, foo: ProtocolFoo, bar: ProtocolBar) -> None:
        self.foo = foo
        self.bar = bar
