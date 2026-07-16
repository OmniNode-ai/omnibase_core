# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Static module adjacency map — canonical model layer.

Canonical home (OMN-14700) for the shapes previously defined in
``scripts/ci/test_selection_loader.py``. Moved verbatim so both the
``node_test_selector_compute`` handler (which takes the loaded map as a pure
input) and the ``detect_test_paths.py`` oracle validate against ONE model.

The YAML file read (``load_adjacency_map``) is filesystem I/O and stays at the
caller boundary (``scripts/ci/test_selection_loader.py`` for the legacy oracle,
``runtime_test_selector.py`` for the node entrypoint) — never inside the node.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

__all__ = [
    "ModelAdjacencyEntry",
    "ModelAdjacencyMap",
    "ModelThresholds",
]


class ModelAdjacencyEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    reverse_deps: list[str] = Field(default_factory=list)


class ModelThresholds(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    modules_changed_for_full_suite: int = Field(..., ge=1)


class ModelAdjacencyMap(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: int = Field(..., ge=1)
    shared_modules: list[str]
    thresholds: ModelThresholds
    test_infrastructure_paths: list[str]
    adjacency: dict[str, ModelAdjacencyEntry]

    @model_validator(mode="after")
    def validate_shared_modules_in_adjacency(self) -> ModelAdjacencyMap:
        for shared in self.shared_modules:
            if shared not in self.adjacency:
                raise ValueError(f"shared_module '{shared}' has no adjacency entry")
        for module, entry in self.adjacency.items():
            for dep in entry.reverse_deps:
                if dep not in self.adjacency:
                    raise ValueError(
                        f"adjacency['{module}'].reverse_deps references unknown module '{dep}'"
                    )
        return self
