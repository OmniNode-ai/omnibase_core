# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
import re
import subprocess
from pathlib import Path

CONFIG = Path(".pre-commit-config.yaml")
WRITING_ENTRY = re.compile(
    r"write"
)  # validator-home-canary: runs the hook on a planted violation


def test_hook_rejects_planted_violation() -> None:
    result = subprocess.run(
        ["pre-commit", "run", "--config", str(CONFIG)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert WRITING_ENTRY.search(result.stdout)
