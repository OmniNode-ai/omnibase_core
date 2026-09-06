# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Owner and disposition for one raw environment reader inventory entry."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelEnvironmentReaderInventoryAssignment:
    """The accountable ticket and required migration for one reader path."""

    owner: str
    disposition: str
