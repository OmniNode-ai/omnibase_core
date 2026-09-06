# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Regression tests for the typed process-environment bootstrap boundary."""

from __future__ import annotations

from typing import cast

import pytest

from omnibase_core.bootstrap.environment_bootstrap import (
    ModelEnvironmentBootstrap,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError


@pytest.mark.unit
def test_process_snapshot_is_unchanged_after_environment_mutation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Consumers keep the injected snapshot, not a live process-environment view."""
    monkeypatch.setenv("OMN17744_BOOTSTRAP_VALUE", "before")
    bootstrap = ModelEnvironmentBootstrap.capture_process_environment(
        declared_keys={"OMN17744_BOOTSTRAP_VALUE"},
    )

    monkeypatch.setenv("OMN17744_BOOTSTRAP_VALUE", "after")

    assert bootstrap.environment.require("OMN17744_BOOTSTRAP_VALUE") == "before"


@pytest.mark.unit
def test_injected_snapshot_cannot_be_mutated_through_its_public_mapping() -> None:
    """Pydantic's outer frozen setting is insufficient for a mutable dict field."""
    bootstrap = ModelEnvironmentBootstrap.from_mapping(
        {"DECLARED_VALUE": "before"},
        declared_keys={"DECLARED_VALUE"},
    )
    values = cast(dict[str, str], bootstrap.environment.values)

    with pytest.raises(TypeError):
        values["DECLARED_VALUE"] = "after"

    assert bootstrap.environment.require("DECLARED_VALUE") == "before"


@pytest.mark.unit
def test_injected_snapshot_rejects_unrecognized_environment_key() -> None:
    """Dynamic lookups must be declared by the bootstrap boundary."""
    bootstrap = ModelEnvironmentBootstrap.from_mapping(
        {"DECLARED_VALUE": "present"},
        declared_keys={"DECLARED_VALUE"},
    )

    with pytest.raises(ModelOnexError, match="not declared"):
        bootstrap.environment.require("UNDECLARED_VALUE")
