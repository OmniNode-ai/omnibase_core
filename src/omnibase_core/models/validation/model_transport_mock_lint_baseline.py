# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelTransportMockLintBaseline — transport-mock-lint ratchet baseline (OMN-18038).

Typed contract boundary for the ``--baseline`` document read by
``omnibase_core.validators.transport_mock_lint``: a mapping of repo-relative path to
the allowed violation count for that path. ``RootModel`` is the right shape because
the document's KEYS are data (paths), not a fixed field set; Pydantic coerces and
rejects a non-integer allowance at the boundary instead of letting ``int(v)`` raise
deep inside the ratchet.
"""

from __future__ import annotations

from pydantic import RootModel


class ModelTransportMockLintBaseline(RootModel[dict[str, int]]):
    """Parsed transport-mock-lint baseline: relative path -> allowed violations."""

    @property
    def allowances(self) -> dict[str, int]:
        """Path -> allowed violation count."""
        return self.root


__all__ = ["ModelTransportMockLintBaseline"]
