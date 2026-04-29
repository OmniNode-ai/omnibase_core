# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Migration Status Enum.

Status tracking for imperative-to-declarative handler migrations.
"""

from enum import Enum, unique


@unique
class EnumMigrationStatus(str, Enum):
    """Status of a handler's migration from imperative to declarative.

    Lifecycle: PENDING -> GENERATED -> VALIDATED -> DEPLOYED -> RETIRED

    - PENDING: Migration identified but not yet started.
    - GENERATED: Migration spec generated with contract.yaml changes.
    - VALIDATED: Migration validated via contract-dispatch equivalence.
    - DEPLOYED: Migrated handler deployed and serving traffic.
    - RETIRED: Old imperative wiring fully removed.
    """

    PENDING = "pending"
    """Migration identified but not yet started."""

    GENERATED = "generated"
    """Migration spec generated with contract.yaml changes."""

    VALIDATED = "validated"
    """Migration validated via contract-dispatch equivalence."""

    DEPLOYED = "deployed"
    """Migrated handler deployed and serving traffic."""

    RETIRED = "retired"
    """Old imperative wiring fully removed."""

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value
