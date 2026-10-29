# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
from pathlib import Path


def run(p: str) -> int:
    return Path(p).write_text("x")
