# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelHandlerDiModuleFact — one Python module as the K1 handler_di checker reads it (OMN-21531)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ModelHandlerDiModuleFact:
    """One module under ``handlers/``, ``nodes/`` or named ``*_cli.py``: its posix path and source."""

    posix_path: str
    source: str
