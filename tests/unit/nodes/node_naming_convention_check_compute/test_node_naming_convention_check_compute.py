# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Handler and runtime tests for node_naming_convention_check_compute (OMN-21520)."""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.models.nodes.naming_convention_check.model_naming_convention_check_input import (
    ModelNamingConventionCheckInput,
)
from omnibase_core.nodes.node_naming_convention_check_compute.handler import (
    NodeNamingConventionCheckCompute,
)
from omnibase_core.nodes.node_naming_convention_check_compute.runtime_naming_convention_check import (
    main,
)

pytestmark = pytest.mark.unit


def test_handle_pass_and_fail() -> None:
    handler = NodeNamingConventionCheckCompute()
    ok = handler.handle(
        ModelNamingConventionCheckInput(
            paths=("src/omnibase_core/models/model_user.py",)
        )
    )
    assert ok.errors == ()
    bad_path = "src/omnibase_core/models/user.py"
    bad = handler.handle(ModelNamingConventionCheckInput(paths=(bad_path,)))
    assert bad.errors == (
        f"{bad_path}: File 'user.py' in 'models/' directory must start with 'model_'",
    )


def test_main_exit_codes(tmp_path: Path) -> None:
    models = tmp_path / "src" / "omnibase_core" / "models"
    models.mkdir(parents=True)
    (models / "model_user.py").write_text("")
    assert main([str(tmp_path)]) == 0
    (models / "user.py").write_text("")
    assert main([str(tmp_path)]) == 1
    assert main(["--warning-mode", str(tmp_path)]) == 0
