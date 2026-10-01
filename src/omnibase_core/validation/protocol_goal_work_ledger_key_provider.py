# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Protected runtime key lookup used to authenticate Work Ledger envelopes."""

from typing import Protocol


class ProtocolGoalWorkLedgerKeyProvider(Protocol):
    """Structural subset of runtime key lookup needed by the history reader."""

    def get_public_key(self, runtime_id: str) -> bytes | None:
        """Return the trusted runtime Ed25519 key, if registered."""
        ...

    def register_key(self, runtime_id: str, public_key: bytes) -> None:
        """Satisfy the existing key-provider structural contract."""
        ...

    def has_key(self, runtime_id: str) -> bool:
        """Return whether a runtime key is provisioned."""
        ...

    def list_runtime_ids(self) -> list[str]:
        """Return configured runtime identifiers without exposing key bytes."""
        ...
