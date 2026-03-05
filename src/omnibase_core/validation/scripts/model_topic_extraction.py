# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Data model for a topic string extracted from a source file."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TopicExtraction:
    """A topic string extracted from a source file."""

    file_path: Path
    line_number: int
    constant_value: str
