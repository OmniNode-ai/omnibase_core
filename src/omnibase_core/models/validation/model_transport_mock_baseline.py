# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed frozen baseline for the transport-mock validator."""

from typing import Self

from pydantic import ConfigDict, RootModel, model_validator


class ModelTransportMockBaseline(RootModel[dict[str, int]]):
    """Strict mapping of violation fingerprints to non-negative counts."""

    model_config = ConfigDict(frozen=True, strict=True)

    @model_validator(mode="after")
    def require_nonnegative_counts(self) -> Self:
        """Reject negative baseline counts without coercing YAML values."""
        if any(count < 0 for count in self.root.values()):
            raise ValueError("transport-mock baseline counts must be non-negative")
        return self


__all__ = ["ModelTransportMockBaseline"]
