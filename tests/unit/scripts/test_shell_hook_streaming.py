# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Shell hooks must stream loop input instead of materializing here-strings."""

from pathlib import Path

import pytest


@pytest.mark.unit
def test_transport_import_hook_has_no_here_string_fed_read_loop() -> None:
    script = Path("scripts/validate-no-transport-imports.sh").read_text(
        encoding="utf-8"
    )

    assert "done <<<" not in script
