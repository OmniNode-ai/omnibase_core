#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Assert OMN-13305 backend-secret-discipline remote hook exposure."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
HOOKS_FILE = REPO_ROOT / ".pre-commit-hooks.yaml"


@pytest.fixture(scope="module")
def hooks() -> dict[str, dict[str, object]]:
    raw = yaml.safe_load(HOOKS_FILE.read_text(encoding="utf-8"))
    assert isinstance(raw, list), ".pre-commit-hooks.yaml must be a list of hooks"
    by_id: dict[str, dict[str, object]] = {}
    for entry in raw:
        assert isinstance(entry, dict)
        hook_id = entry.get("id")
        assert isinstance(hook_id, str)
        by_id[hook_id] = entry
    return by_id


@pytest.mark.unit
def test_backend_secret_discipline_compute_hook_exported(
    hooks: dict[str, dict[str, object]],
) -> None:
    hook = hooks["check-backend-secret-discipline"]
    assert hook["language"] == "python"
    assert (
        hook["entry"]
        == "python -m omnibase_core.validation.validator_backend_secret_discipline"
    )
    assert hook["files"] == r"\.(ya?ml|json)$"
    assert hook["pass_filenames"] is True


@pytest.mark.unit
def test_existing_backend_secret_hook_alias_retained(
    hooks: dict[str, dict[str, object]],
) -> None:
    hook = hooks["backend-secret-discipline"]
    assert (
        hook["entry"] == "python -m omnibase_core.validators.backend_secret_discipline"
    )
