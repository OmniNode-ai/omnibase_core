# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Point the pre-push tests' workspace-config resolver at a synthetic table (OMN-20939).

The hook and the full-suite guard read the deployment's host rows from a private
table. Every test in this directory that runs either one sees the invented rows
of ``_prepush_private_table`` unless it sets ``ONEX_WORKSPACE_CONFIG_ROOT``
itself, so no test depends on an operator's real configuration being present.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.scripts._prepush_private_table import write_private_root


@pytest.fixture(autouse=True)
def _synthetic_workspace_config_root(
    tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> Path:
    root = write_private_root(tmp_path_factory.mktemp("prepush_private"))
    monkeypatch.setenv("ONEX_WORKSPACE_CONFIG_ROOT", str(root))
    return root
