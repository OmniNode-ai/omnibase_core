# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ValidatorDuplicateConfigIds (OMN-14401).

Covers:
- Flat list_path (grants shape): duplicate id with no disambiguator FAILS
- Flat list_path: unique ids PASS
- Grouped list_path (routing_tiers shape): duplicate id disambiguated by a
  disjoint second field PASSES (the load-bearing nuance — must not ban
  duplicate ids outright)
- Grouped list_path: duplicate id with OVERLAPPING disambiguator FAILS
- Grouped list_path: a duplicate id ACROSS different groups (different tiers)
  does not false-positive — only same-group collisions are checked
- Missing disambiguator field on one of the colliding entries FAILS
- Fail-closed structural cases: missing file, unparseable YAML, non-dict
  top-level, missing list_path key, non-list resolved value, entry missing
  id_field, malformed manifest
- RED -> GREEN against the REAL historical omnimarket routing_tiers.yaml
  duplicate-id-disambiguated-by-use_for shape (OMN-14396), and its mutation
  into a genuine same-tier ambiguity
- CLI main(): no manifest -> 0, clean manifest -> 0, violations -> 1
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from omnibase_core.errors import OnexError
from omnibase_core.models.validation.model_duplicate_id_manifest import (
    ModelDuplicateIdManifest,
)
from omnibase_core.validation.validator_duplicate_config_ids import (
    ModelDuplicateIdCheckSpec,
    ValidatorDuplicateConfigIds,
    main,
)


def _write_yaml(path: Path, data: object) -> None:
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


# ---------------------------------------------------------------------------
# Flat list_path (prod_promotion_grants.yaml shape) — no disambiguator
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFlatListNoDisambiguator:
    """Grants-shaped registry: any duplicate id_field is a hard failure."""

    def test_duplicate_grant_id_fails(self, tmp_path: Path) -> None:
        registry = tmp_path / "grants.yaml"
        _write_yaml(
            registry,
            {
                "entries": [
                    {"grant_id": "grant-aaaa", "image_digest": "sha256:aaa"},
                    {"grant_id": "grant-aaaa", "image_digest": "sha256:bbb"},
                ]
            },
        )
        spec = ModelDuplicateIdCheckSpec(
            path="grants.yaml", list_path="entries", id_field="grant_id"
        )
        violations = ValidatorDuplicateConfigIds().check_registry(spec, tmp_path)
        assert len(violations) == 1
        assert "grant-aaaa" in violations[0].detail
        assert "no disambiguator_field" in violations[0].detail

    def test_legitimate_digest_reuse_is_not_the_checked_key(
        self, tmp_path: Path
    ) -> None:
        """image_digest legitimately repeats across re-grants (OMN-14395) —
        the guard must key on grant_id, not image_digest, or it would reject
        the exact scenario OMN-14395's fix was designed to correctly handle."""
        registry = tmp_path / "grants.yaml"
        _write_yaml(
            registry,
            {
                "entries": [
                    {"grant_id": "grant-aaaa", "image_digest": "sha256:same"},
                    {"grant_id": "grant-bbbb", "image_digest": "sha256:same"},
                ]
            },
        )
        spec = ModelDuplicateIdCheckSpec(
            path="grants.yaml", list_path="entries", id_field="grant_id"
        )
        violations = ValidatorDuplicateConfigIds().check_registry(spec, tmp_path)
        assert violations == []

    def test_unique_ids_pass(self, tmp_path: Path) -> None:
        registry = tmp_path / "grants.yaml"
        _write_yaml(
            registry,
            {
                "entries": [
                    {"grant_id": "grant-aaaa"},
                    {"grant_id": "grant-bbbb"},
                ]
            },
        )
        spec = ModelDuplicateIdCheckSpec(
            path="grants.yaml", list_path="entries", id_field="grant_id"
        )
        assert ValidatorDuplicateConfigIds().check_registry(spec, tmp_path) == []

    def test_empty_entries_pass(self, tmp_path: Path) -> None:
        registry = tmp_path / "grants.yaml"
        _write_yaml(registry, {"entries": []})
        spec = ModelDuplicateIdCheckSpec(
            path="grants.yaml", list_path="entries", id_field="grant_id"
        )
        assert ValidatorDuplicateConfigIds().check_registry(spec, tmp_path) == []


# ---------------------------------------------------------------------------
# Grouped list_path (routing_tiers.yaml shape) — with disambiguator
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGroupedListWithDisambiguator:
    """routing_tiers-shaped registry: duplicate id tolerated iff a configured
    disambiguator field's values are disjoint across the colliding entries."""

    def test_disjoint_use_for_passes(self, tmp_path: Path) -> None:
        registry = tmp_path / "routing_tiers.yaml"
        _write_yaml(
            registry,
            {
                "tiers": [
                    {
                        "name": "local",
                        "models": [
                            {"id": "Qwen3.6-35B-A3B", "use_for": ["code_generation"]},
                            {"id": "Qwen3.6-35B-A3B", "use_for": ["research"]},
                        ],
                    }
                ]
            },
        )
        spec = ModelDuplicateIdCheckSpec(
            path="routing_tiers.yaml",
            list_path="tiers[].models",
            id_field="id",
            disambiguator_field="use_for",
        )
        assert ValidatorDuplicateConfigIds().check_registry(spec, tmp_path) == []

    def test_overlapping_use_for_fails(self, tmp_path: Path) -> None:
        registry = tmp_path / "routing_tiers.yaml"
        _write_yaml(
            registry,
            {
                "tiers": [
                    {
                        "name": "local",
                        "models": [
                            {
                                "id": "Qwen3.6-35B-A3B",
                                "use_for": ["code_generation", "research"],
                            },
                            {"id": "Qwen3.6-35B-A3B", "use_for": ["research"]},
                        ],
                    }
                ]
            },
        )
        spec = ModelDuplicateIdCheckSpec(
            path="routing_tiers.yaml",
            list_path="tiers[].models",
            id_field="id",
            disambiguator_field="use_for",
        )
        violations = ValidatorDuplicateConfigIds().check_registry(spec, tmp_path)
        assert len(violations) == 1
        assert violations[0].group_label == "local"
        assert "research" in violations[0].detail

    def test_cross_group_duplicate_does_not_false_positive(
        self, tmp_path: Path
    ) -> None:
        """Same id + same use_for repeated in a DIFFERENT tier is legitimate
        (the real routing_tiers.yaml repeats glm-5-turbo across cheap_cloud
        and claude tiers) — only a same-group collision is checked."""
        registry = tmp_path / "routing_tiers.yaml"
        _write_yaml(
            registry,
            {
                "tiers": [
                    {
                        "name": "cheap_cloud",
                        "models": [
                            {"id": "glm-5-turbo", "use_for": ["code_generation"]}
                        ],
                    },
                    {
                        "name": "claude",
                        "models": [
                            {"id": "glm-5-turbo", "use_for": ["code_generation"]}
                        ],
                    },
                ]
            },
        )
        spec = ModelDuplicateIdCheckSpec(
            path="routing_tiers.yaml",
            list_path="tiers[].models",
            id_field="id",
            disambiguator_field="use_for",
        )
        assert ValidatorDuplicateConfigIds().check_registry(spec, tmp_path) == []

    def test_missing_disambiguator_field_on_one_entry_fails(
        self, tmp_path: Path
    ) -> None:
        registry = tmp_path / "routing_tiers.yaml"
        _write_yaml(
            registry,
            {
                "tiers": [
                    {
                        "name": "local",
                        "models": [
                            {"id": "Qwen3.6-35B-A3B", "use_for": ["code_generation"]},
                            {"id": "Qwen3.6-35B-A3B"},  # missing use_for entirely
                        ],
                    }
                ]
            },
        )
        spec = ModelDuplicateIdCheckSpec(
            path="routing_tiers.yaml",
            list_path="tiers[].models",
            id_field="id",
            disambiguator_field="use_for",
        )
        violations = ValidatorDuplicateConfigIds().check_registry(spec, tmp_path)
        assert len(violations) == 1
        assert "missing disambiguator field" in violations[0].detail

    def test_scalar_disambiguator_treated_as_singleton_set(
        self, tmp_path: Path
    ) -> None:
        registry = tmp_path / "reg.yaml"
        _write_yaml(
            registry,
            {
                "groups": [
                    {
                        "name": "g1",
                        "items": [
                            {"id": "x", "kind": "a"},
                            {"id": "x", "kind": "b"},
                        ],
                    }
                ]
            },
        )
        spec = ModelDuplicateIdCheckSpec(
            path="reg.yaml",
            list_path="groups[].items",
            id_field="id",
            disambiguator_field="kind",
        )
        assert ValidatorDuplicateConfigIds().check_registry(spec, tmp_path) == []

    def test_scalar_disambiguator_equal_values_fails(self, tmp_path: Path) -> None:
        registry = tmp_path / "reg.yaml"
        _write_yaml(
            registry,
            {
                "groups": [
                    {
                        "name": "g1",
                        "items": [
                            {"id": "x", "kind": "a"},
                            {"id": "x", "kind": "a"},
                        ],
                    }
                ]
            },
        )
        spec = ModelDuplicateIdCheckSpec(
            path="reg.yaml",
            list_path="groups[].items",
            id_field="id",
            disambiguator_field="kind",
        )
        violations = ValidatorDuplicateConfigIds().check_registry(spec, tmp_path)
        assert len(violations) == 1


# ---------------------------------------------------------------------------
# Fail-closed structural cases
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFailClosed:
    """Unparseable or unknown-shaped registries are a FAILURE, not a skip."""

    def test_missing_registry_file(self, tmp_path: Path) -> None:
        spec = ModelDuplicateIdCheckSpec(
            path="does_not_exist.yaml", list_path="entries", id_field="id"
        )
        violations = ValidatorDuplicateConfigIds().check_registry(spec, tmp_path)
        assert len(violations) == 1
        assert "not found" in violations[0].detail

    def test_unparseable_yaml(self, tmp_path: Path) -> None:
        registry = tmp_path / "broken.yaml"
        registry.write_text("entries: [this is: not: valid: yaml", encoding="utf-8")
        spec = ModelDuplicateIdCheckSpec(
            path="broken.yaml", list_path="entries", id_field="id"
        )
        violations = ValidatorDuplicateConfigIds().check_registry(spec, tmp_path)
        assert len(violations) == 1
        assert "unparseable" in violations[0].detail

    def test_non_dict_top_level(self, tmp_path: Path) -> None:
        registry = tmp_path / "listtop.yaml"
        _write_yaml(registry, ["a", "b"])
        spec = ModelDuplicateIdCheckSpec(
            path="listtop.yaml", list_path="entries", id_field="id"
        )
        violations = ValidatorDuplicateConfigIds().check_registry(spec, tmp_path)
        assert len(violations) == 1
        assert "must be a mapping" in violations[0].detail

    def test_missing_list_path_key(self, tmp_path: Path) -> None:
        registry = tmp_path / "reg.yaml"
        _write_yaml(registry, {"other_key": []})
        spec = ModelDuplicateIdCheckSpec(
            path="reg.yaml", list_path="entries", id_field="id"
        )
        violations = ValidatorDuplicateConfigIds().check_registry(spec, tmp_path)
        assert len(violations) == 1
        assert "not found" in violations[0].detail

    def test_resolved_value_not_a_list(self, tmp_path: Path) -> None:
        registry = tmp_path / "reg.yaml"
        _write_yaml(registry, {"entries": {"not": "a list"}})
        spec = ModelDuplicateIdCheckSpec(
            path="reg.yaml", list_path="entries", id_field="id"
        )
        violations = ValidatorDuplicateConfigIds().check_registry(spec, tmp_path)
        assert len(violations) == 1
        assert "did not resolve to a list" in violations[0].detail

    def test_entry_missing_id_field(self, tmp_path: Path) -> None:
        registry = tmp_path / "reg.yaml"
        _write_yaml(registry, {"entries": [{"other": "x"}]})
        spec = ModelDuplicateIdCheckSpec(
            path="reg.yaml", list_path="entries", id_field="id"
        )
        violations = ValidatorDuplicateConfigIds().check_registry(spec, tmp_path)
        assert len(violations) == 1
        assert "missing required id field" in violations[0].detail

    def test_entry_not_a_mapping(self, tmp_path: Path) -> None:
        registry = tmp_path / "reg.yaml"
        _write_yaml(registry, {"entries": ["not-a-mapping"]})
        spec = ModelDuplicateIdCheckSpec(
            path="reg.yaml", list_path="entries", id_field="id"
        )
        violations = ValidatorDuplicateConfigIds().check_registry(spec, tmp_path)
        assert len(violations) == 1
        assert "is not a mapping" in violations[0].detail

    def test_group_not_a_mapping(self, tmp_path: Path) -> None:
        registry = tmp_path / "reg.yaml"
        _write_yaml(registry, {"tiers": ["not-a-mapping"]})
        spec = ModelDuplicateIdCheckSpec(
            path="reg.yaml", list_path="tiers[].models", id_field="id"
        )
        violations = ValidatorDuplicateConfigIds().check_registry(spec, tmp_path)
        assert len(violations) == 1
        assert "is not a mapping" in violations[0].detail

    def test_malformed_manifest_missing_registries_key(self, tmp_path: Path) -> None:
        manifest = tmp_path / "manifest.yaml"
        _write_yaml(manifest, {"not_registries": []})
        with pytest.raises(OnexError, match="registries"):
            ModelDuplicateIdManifest.from_yaml(manifest)

    def test_malformed_manifest_registries_not_list(self, tmp_path: Path) -> None:
        manifest = tmp_path / "manifest.yaml"
        _write_yaml(manifest, {"registries": "not-a-list"})
        with pytest.raises(OnexError, match="failed schema validation"):
            ModelDuplicateIdManifest.from_yaml(manifest)

    def test_malformed_manifest_unparseable(self, tmp_path: Path) -> None:
        manifest = tmp_path / "manifest.yaml"
        manifest.write_text("registries: [this is: not: valid", encoding="utf-8")
        with pytest.raises(OnexError, match="unparseable"):
            ModelDuplicateIdManifest.from_yaml(manifest)


# ---------------------------------------------------------------------------
# RED -> GREEN against the REAL historical routing_tiers.yaml shape (OMN-14396)
# ---------------------------------------------------------------------------

# Reproduces the load-bearing local-tier slice of the real omnimarket
# src/omnimarket/configs/routing_tiers.yaml as of OMN-14396's fix: two
# backends declare id "Qwen3.6-35B-A3B" with disjoint use_for sets. This is
# the exact shape that made `_select_model_for_task`'s id-only match pick the
# wrong backend for task_type=research before OMN-14396's code fix — the DATA
# was always correctly disambiguated, only the CONSUMING RESOLVER ignored the
# disambiguator. This guard checks the DATA side: it must not flag this
# legitimate shape as a violation.
_REAL_ROUTING_TIERS_LOCAL_TIER = {
    "tiers": [
        {
            "name": "local",
            "models": [
                {
                    "id": "Qwen3.6-35B-A3B",
                    "backend_id": "local-coder",
                    "use_for": ["code_generation", "code_review", "refactor"],
                },
                {
                    "id": "Qwen3.6-27B-MTP-IQ4_XS.gguf",
                    "backend_id": "local-reasoner",
                    "use_for": ["test", "research", "reasoning", "planning"],
                },
                {
                    "id": "Qwen3.6-35B-A3B",
                    "backend_id": "local-heavy-reasoning",
                    "use_for": [
                        "research",
                        "reasoning",
                        "complex_reasoning",
                        "planning",
                    ],
                },
            ],
        },
        {
            "name": "claude",
            "models": [
                # Same id/use_for legitimately repeated in a DIFFERENT tier
                # (escalation ceiling) — must not be flagged.
                {
                    "id": "glm-5-turbo",
                    "backend_id": "cloud-glm",
                    "use_for": ["code_generation", "reasoning"],
                },
            ],
        },
        {
            "name": "cheap_cloud",
            "models": [
                {
                    "id": "glm-5-turbo",
                    "backend_id": "cloud-glm",
                    "use_for": ["code_generation", "reasoning"],
                },
            ],
        },
    ]
}

_ROUTING_TIERS_SPEC = ModelDuplicateIdCheckSpec(
    path="routing_tiers.yaml",
    list_path="tiers[].models",
    id_field="id",
    disambiguator_field="use_for",
)


@pytest.mark.unit
class TestRealHistoricalRoutingTiersShape:
    """RED -> GREEN proof against the real OMN-14396 routing_tiers.yaml shape."""

    def test_green_real_shape_passes(self, tmp_path: Path) -> None:
        registry = tmp_path / "routing_tiers.yaml"
        _write_yaml(registry, _REAL_ROUTING_TIERS_LOCAL_TIER)
        violations = ValidatorDuplicateConfigIds().check_registry(
            _ROUTING_TIERS_SPEC, tmp_path
        )
        assert violations == [], (
            f"legitimate disambiguated shape must not fail: {violations}"
        )

    def test_red_same_tier_overlap_mutation_fails(self, tmp_path: Path) -> None:
        """Mutate the real shape: add 'research' to local-coder's use_for,
        colliding with local-heavy-reasoning's use_for WITHIN the same tier —
        a genuine authoring mistake this guard must catch."""
        import copy

        mutated = copy.deepcopy(_REAL_ROUTING_TIERS_LOCAL_TIER)
        mutated["tiers"][0]["models"][0]["use_for"].append("research")
        registry = tmp_path / "routing_tiers.yaml"
        _write_yaml(registry, mutated)
        violations = ValidatorDuplicateConfigIds().check_registry(
            _ROUTING_TIERS_SPEC, tmp_path
        )
        assert len(violations) == 1
        assert violations[0].group_label == "local"
        assert "Qwen3.6-35B-A3B" in violations[0].detail
        assert "research" in violations[0].detail


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCli:
    def test_no_manifest_returns_zero(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        rc = main(
            ["--manifest", str(tmp_path / "nope.yaml"), "--repo-root", str(tmp_path)]
        )
        assert rc == 0
        assert "nothing to check" in capsys.readouterr().out

    def test_clean_manifest_returns_zero(self, tmp_path: Path) -> None:
        registry = tmp_path / "grants.yaml"
        _write_yaml(registry, {"entries": [{"grant_id": "a"}, {"grant_id": "b"}]})
        manifest = tmp_path / "manifest.yaml"
        _write_yaml(
            manifest,
            {
                "registries": [
                    {
                        "path": "grants.yaml",
                        "list_path": "entries",
                        "id_field": "grant_id",
                    }
                ]
            },
        )
        rc = main(["--manifest", str(manifest), "--repo-root", str(tmp_path)])
        assert rc == 0

    def test_violations_return_one(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        registry = tmp_path / "grants.yaml"
        _write_yaml(
            registry,
            {"entries": [{"grant_id": "dup"}, {"grant_id": "dup"}]},
        )
        manifest = tmp_path / "manifest.yaml"
        _write_yaml(
            manifest,
            {
                "registries": [
                    {
                        "path": "grants.yaml",
                        "list_path": "entries",
                        "id_field": "grant_id",
                    }
                ]
            },
        )
        rc = main(["--manifest", str(manifest), "--repo-root", str(tmp_path)])
        assert rc == 1
        out = capsys.readouterr().out
        assert "dup" in out
        assert "1 duplicate-id registry violation" in out

    def test_malformed_manifest_returns_one(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        manifest = tmp_path / "manifest.yaml"
        _write_yaml(manifest, {"wrong_key": []})
        rc = main(["--manifest", str(manifest), "--repo-root", str(tmp_path)])
        assert rc == 1
        assert "cannot load manifest" in capsys.readouterr().out
