# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Real temporary git repositories prove tag listing and annotation handling."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import cast
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from omnibase_core.models.validation.model_first_party_tag_inventory_request import (
    ModelFirstPartyTagInventoryRequest,
)
from omnibase_core.models.validation.model_first_party_tag_inventory_result import (
    ModelFirstPartyTagInventoryResult,
)
from omnibase_core.models.validation.model_sibling_stale_parameters import (
    ModelSiblingStaleParameters,
)
from omnibase_core.nodes.node_first_party_tag_inventory_effect.handler import (
    NodeFirstPartyTagInventoryEffect,
)
from omnibase_core.validation.checker_first_party_ref import load_rule_parameters
from omnibase_core.validation.validator_first_party_ref import ValidatorFirstPartyRef

pytestmark = pytest.mark.unit
GIT = shutil.which("git") or "git"
TAG = "dev-20261018024445-b6ee996befa1"


def git(root: Path, *args: str):
    return subprocess.check_output(
        [GIT, "-C", str(root), *args],
        text=True,
        env={"PATH": str(Path(GIT).parent)},
    )


def test_effect_lists_real_lightweight_and_annotated_tags(tmp_path):
    repo = tmp_path / "sibling"
    repo.mkdir()
    git(repo, "init", "-q")
    git(
        repo,
        "-c",
        "user.name=Test",
        "-c",
        "user.email=test@example.org",
        "commit",
        "--allow-empty",
        "-qm",
        "initial",
    )
    git(repo, "tag", TAG)
    second = "dev-20261019024445-aaaaaaaaaaaa"
    git(
        repo,
        "-c",
        "user.name=Test",
        "-c",
        "user.email=test@example.org",
        "tag",
        "-a",
        second,
        "-m",
        "annotated",
    )
    git(repo, "tag", "v1.2.3")
    git(repo, "tag", "dev-invalid")
    policy = cast(
        ModelSiblingStaleParameters,
        load_rule_parameters(ValidatorFirstPartyRef().contract)["stale_pin"],
    )
    policy = policy.model_copy(update={"url_template": str(tmp_path / "{repo}")})
    effect = NodeFirstPartyTagInventoryEffect()
    result = effect.handle(
        ModelFirstPartyTagInventoryRequest(repo="sibling", policy=policy)
    )
    assert result == ModelFirstPartyTagInventoryResult(
        repo="sibling", tags=(TAG, second)
    )


@pytest.mark.parametrize(
    "failure",
    [
        OSError("no binary"),
        subprocess.CalledProcessError(1, ["git"]),
        subprocess.TimeoutExpired(["git"], 1),
    ],
)
def test_effect_does_not_swallow_inventory_failure(failure):
    policy = cast(
        ModelSiblingStaleParameters,
        load_rule_parameters(ValidatorFirstPartyRef().contract)["stale_pin"],
    )
    with (
        patch(
            "omnibase_core.nodes.node_first_party_tag_inventory_effect.handler.subprocess.run",
            side_effect=failure,
        ),
        pytest.raises(type(failure)),
    ):
        NodeFirstPartyTagInventoryEffect().handle(
            ModelFirstPartyTagInventoryRequest(repo="sibling", policy=policy)
        )


def test_inventory_models_are_frozen_forbid_extras_and_read_attributes():
    result = ModelFirstPartyTagInventoryResult(repo="sibling", tags=(TAG,))
    with pytest.raises(ValidationError):
        result.repo = "other"
    with pytest.raises(ValidationError):
        ModelFirstPartyTagInventoryResult.model_validate(
            {"repo": "sibling", "tags": [], "extra": True}
        )

    class Attributes:
        repo = "sibling"
        tags = (TAG,)

    assert ModelFirstPartyTagInventoryResult.model_validate(Attributes()) == result
