# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelValidatorHomeContractFact — one node contract as the K7 checker reads it (OMN-21503)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ModelValidatorHomeContractFact:
    """One node contract: its names, output model and its handler sources."""

    directory_name: str
    contract_name: str
    output_model: str
    handler_sources: tuple[str, ...]
