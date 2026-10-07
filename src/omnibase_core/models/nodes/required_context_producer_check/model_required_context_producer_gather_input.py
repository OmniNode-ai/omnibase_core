# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Repository selection supplied to the producer gather EFFECT."""

from pydantic import BaseModel, ConfigDict


class ModelRequiredContextProducerGatherInput(BaseModel):
    """Select the checkout, optional base, and manifest and workflow locations."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    repo_root: str
    base: str | None = None
    manifest_path: str = ".github/required-checks.yaml"
    workflows_dir: str = ".github/workflows"
