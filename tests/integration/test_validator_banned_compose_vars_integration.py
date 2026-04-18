# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Integration tests for ValidatorBannedComposeVars wiring [OMN-9113].

Unit tests synthesize minimal kernels; this suite proves the wiring story end
to end:

* CLI entrypoint is resolvable as a module (what the pre-commit hook invokes).
* A realistic docker-compose.yml containing ``ONEX_INPUT_TOPIC`` is flagged
  against a real kernel tuple (OMN-8840 regression prevention).
* The hook contract declared in ``.pre-commit-hooks.yaml`` advertises the CLI
  entry the integration test just exercised.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.integration
def test_cli_module_is_importable() -> None:
    """`uv run python -m ...` must resolve — pre-commit hooks rely on it."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "omnibase_core.validation.validator_banned_compose_vars",
            "--help",
        ],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "--kernel-source" in result.stdout


@pytest.mark.integration
def test_realistic_compose_with_onex_input_topic_is_flagged(tmp_path: Path) -> None:
    """A real docker-compose.yml with ONEX_INPUT_TOPIC must fire the validator."""
    kernel = tmp_path / "service_kernel.py"
    kernel.write_text(
        '_DEPRECATED_TOPIC_ENV_VARS: tuple[str, ...] = ("ONEX_INPUT_TOPIC", "ONEX_OUTPUT_TOPIC")\n',
        encoding="utf-8",
    )

    compose = tmp_path / "docker-compose.yml"
    compose.write_text(
        yaml.safe_dump(
            {
                "services": {
                    "runtime-effects": {
                        "image": "omninode-runtime-effects:latest",
                        "environment": {
                            "KAFKA_BOOTSTRAP_SERVERS": "redpanda:9092",
                            "ONEX_INPUT_TOPIC": "onex.cmd.runtime.request.v1",
                            "LOG_LEVEL": "INFO",
                        },
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    from omnibase_core.enums.enum_compose_drift_kind import EnumComposeDriftKind
    from omnibase_core.validation.validator_banned_compose_vars import (
        ValidatorBannedComposeVars,
    )

    violations = ValidatorBannedComposeVars(kernel_source_path=kernel).check_paths(
        [tmp_path]
    )

    flagged = {v.var_name for v in violations}
    assert "ONEX_INPUT_TOPIC" in flagged
    assert all(v.kind is EnumComposeDriftKind.BANNED_VAR for v in violations)


@pytest.mark.integration
def test_pre_commit_hook_declaration_matches_cli_entry() -> None:
    """Hook id + entry in .pre-commit-hooks.yaml must reference the real module."""
    hooks_file = REPO_ROOT / ".pre-commit-hooks.yaml"
    hooks = yaml.safe_load(hooks_file.read_text(encoding="utf-8"))
    ids = {hook["id"] for hook in hooks}
    assert "validator-banned-compose-vars" in ids, (
        "hook id 'validator-banned-compose-vars' missing from .pre-commit-hooks.yaml"
    )
    hook = next(h for h in hooks if h["id"] == "validator-banned-compose-vars")
    assert "omnibase_core.validation.validator_banned_compose_vars" in hook["entry"]
