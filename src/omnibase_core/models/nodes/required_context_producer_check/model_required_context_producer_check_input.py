# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Immutable manifests and workflow sources consumed without I/O."""

from typing import Literal

from pydantic import BaseModel, ConfigDict

from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile


class ModelRequiredContextProducerCheckInput(BaseModel):
    """Head sources and optional base manifest, plus collection diagnostics."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    head_manifest_text: str | None
    base_manifest_text: str | None
    base_ref: str | None
    manifest_path: str
    head_workflows: tuple[ModelSourceFile, ...]
    runtime_errors: tuple[str, ...] = ()
    runtime_exit_code: Literal[1, 2] = 1
