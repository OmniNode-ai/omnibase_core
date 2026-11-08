# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelValidatorShapeNodeFact — one node contract as the validator-shape checker reads it (OMN-21494)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ModelValidatorShapeNodeFact:
    """One node contract: its declared shape and the I/O its compute step performs.

    ``compute_step_io`` holds the message of every I/O finding the no-I/O check
    reports for a module of the node's package, judged as a non-EFFECT node.
    """

    directory_name: str
    tags: tuple[str, ...]
    node_type: str
    purity: str
    handler_bindings: tuple[str, ...]
    compute_step_io: tuple[str, ...]
