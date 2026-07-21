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

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

__all__ = [
    "ModelAdjacencyEntry",
    "ModelAdjacencyMap",
    "ModelThresholds",
]


class _DuplicateKeyRejectingLoader(yaml.SafeLoader):
    """SafeLoader that FAILS on a duplicate mapping key instead of last-wins.

    Plain ``yaml.safe_load`` silently keeps the last occurrence of a duplicate
    key. In the adjacency map that is a fail-OPEN shape (OMN-14897): a second
    ``models:`` (or ``dispatch:``/``analysis:``) entry with a *narrower*
    ``reverse_deps`` would be dropped with no signal, and the selector would
    compute a smaller test closure than the author intended. The
    ``ModelAdjacencyMap`` set-equality validator cannot catch it — the dict has
    already collapsed before validation runs — so detection has to happen at
    parse time, here.
    """


def _construct_mapping_no_duplicates(
    loader: yaml.SafeLoader, node: yaml.MappingNode, deep: bool = False
) -> dict[object, object]:
    mapping: dict[object, object] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=True)
        if key in mapping:
            # A yaml SafeLoader mapping constructor must raise a plain exception;
            # ValueError keeps parity with the ModelAdjacencyMap validator errors
            # the loader already surfaces (and with the loader's
            # pytest.raises(ValueError) contract).
            # error-ok: yaml constructor boundary requires a plain ValueError
            raise ValueError(
                f"duplicate key {key!r} in adjacency YAML: YAML silently keeps the "
                "last occurrence, which would drop a differing reverse_deps entry "
                "unnoticed (OMN-14897). Remove the duplicate."
            )
        mapping[key] = loader.construct_object(value_node, deep=True)
    return mapping


_DuplicateKeyRejectingLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_mapping_no_duplicates,
)


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

    @classmethod
    def from_yaml_text(cls, text: str) -> ModelAdjacencyMap:
        """Parse adjacency-map YAML text into the typed model, FAILING on a
        duplicate mapping key rather than silently keeping the last occurrence.

        This is the single canonical parse used by BOTH the legacy oracle
        (``scripts/ci/test_selection_loader.load_adjacency_map``) and the node
        entrypoint (``runtime_test_selector._load_adjacency``), so the fail-closed
        duplicate-key guard (OMN-14897) runs wherever the map is loaded.
        """
        # S506 (unsafe yaml.load): FALSE POSITIVE — _DuplicateKeyRejectingLoader
        # subclasses yaml.SafeLoader and only overrides the mapping constructor to
        # reject duplicate keys; it constructs no arbitrary objects. yaml.load with
        # an explicit SafeLoader subclass is the only way to install a custom
        # mapping constructor (safe_load hardcodes SafeLoader).
        raw = yaml.load(text, Loader=_DuplicateKeyRejectingLoader)  # noqa: S506
        return cls.model_validate(raw)

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
