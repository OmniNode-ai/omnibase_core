# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed path-to-count baseline consumed by transport mock lint."""

from pydantic import RootModel


class ModelTransportMockLintBaseline(RootModel[dict[str, int]]):
    """Per-file allowed finding counts for the transport mock ratchet."""


__all__ = ["ModelTransportMockLintBaseline"]
