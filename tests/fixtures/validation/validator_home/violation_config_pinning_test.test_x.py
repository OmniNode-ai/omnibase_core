# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
import re
from pathlib import Path

WRITING_ENTRY = re.compile(r"entry:\s+.*write")


def test_hook_entry_is_pinned() -> None:
    text = Path(".pre-commit-config.yaml").read_text()
    assert WRITING_ENTRY.search(text)
