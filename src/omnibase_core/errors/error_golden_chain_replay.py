# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Golden-chain replay error type (OMN-13499)."""

from __future__ import annotations

from omnibase_core.enums.enum_golden_chain_failure_class import (
    EnumGoldenChainFailureClass,
)


class GoldenChainReplayError(RuntimeError):
    """A golden-chain replay failed in a named, classified way."""

    def __init__(
        self, failure_class: EnumGoldenChainFailureClass, message: str
    ) -> None:
        self.failure_class = failure_class
        super().__init__(f"{failure_class.value}: {message}")


__all__ = ["GoldenChainReplayError"]
