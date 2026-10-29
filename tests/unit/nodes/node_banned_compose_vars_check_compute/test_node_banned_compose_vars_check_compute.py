# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Handler and runtime tests for node_banned_compose_vars_check_compute (OMN-21520)."""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.models.nodes.banned_compose_vars_check.model_banned_compose_vars_check_input import (
    ModelBannedComposeVarsCheckInput,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile
from omnibase_core.nodes.node_banned_compose_vars_check_compute.handler import (
    NodeBannedComposeVarsCheckCompute,
)
from omnibase_core.nodes.node_banned_compose_vars_check_compute.runtime_banned_compose_vars_check import (
    main,
)

pytestmark = pytest.mark.unit

COMPOSE = "services:\n  app:\n    environment:\n      ONEX_INPUT_TOPIC: t\n      LOG_LEVEL: INFO\n"
KERNEL = '_DEPRECATED_TOPIC_ENV_VARS = ("ONEX_INPUT_TOPIC",)\n'


def test_handle_pass_and_fail() -> None:
    handler = NodeBannedComposeVarsCheckCompute()
    ok = handler.handle(
        ModelBannedComposeVarsCheckInput(
            banned=("OTHER",),
            files=(ModelSourceFile(path="docker-compose.yml", source=COMPOSE),),
        )
    )
    assert ok.violations == ()
    bad = handler.handle(
        ModelBannedComposeVarsCheckInput(
            banned=("ONEX_INPUT_TOPIC",),
            files=(ModelSourceFile(path="docker-compose.yml", source=COMPOSE),),
        )
    )
    assert [v.var_name for v in bad.violations] == ["ONEX_INPUT_TOPIC"]
    assert bad.violations[0].compose_path == Path("docker-compose.yml")


def test_main_exit_codes(tmp_path: Path) -> None:
    kernel = tmp_path / "service_kernel.py"
    kernel.write_text(KERNEL)
    compose = tmp_path / "docker-compose.yml"
    compose.write_text(COMPOSE)
    assert main(["--kernel-source", str(kernel), "-q", str(compose)]) == 2
    compose.write_text("services:\n  app:\n    environment:\n      LOG_LEVEL: INFO\n")
    assert main(["--kernel-source", str(kernel), "-q", str(compose)]) == 0
