# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for the theme instance + catalog layer (OMN-16882, Phase C1).

`ModelRendererThemeContract` is a *schema*: every token field is required and
the class holds no values. This module covers the instance layer that gives a
token value somewhere to live, and the publish/activate/rollback lifecycle that
makes changing one a data edit rather than a Python class edit.

Gates under test:

- **GC.1** — a theme instance's value can be changed, published, activated, and
  rolled back without editing a Python class.
- **GC.2** — two surfaces loading the same catalog entry report the same
  content digest.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.dashboard import (
    ModelRendererThemeContract,
    ModelThemeActivation,
    ModelThemeCatalog,
    ModelThemeCatalogEntry,
    ModelThemeInstance,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.utils.util_safe_yaml_loader import serialize_data_to_yaml
from omnibase_core.utils.util_theme_catalog import (
    THEME_CATALOG_ROOT,
    activate_theme,
    build_theme_catalog,
    compute_theme_content_digest,
    load_packaged_theme_catalog,
    load_theme_instance,
    roll_back_theme,
)

_REPO_ROOT = Path(__file__).resolve().parents[4]

#: The three theme instances the catalog ships (plan §2.1: light/dark/warm are
#: three catalog entries, not three hand-maintained stylesheets).
_SHIPPED_THEME_IDS = ("onex.theme.light", "onex.theme.dark", "onex.theme.warm")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _dark_tokens(*, accent: str = "#6366f1") -> ModelRendererThemeContract:
    """A complete token set; ``accent`` is the value a test wants to vary."""
    return ModelRendererThemeContract(
        theme_id="onex.theme.dark",
        contract_version=ModelSemVer(major=1, minor=0, patch=0),
        color_background_primary="#0f172a",
        color_background_secondary="#1e293b",
        color_background_elevated="#334155",
        color_text_primary="#f8fafc",
        color_text_secondary="#94a3b8",
        color_text_disabled="#475569",
        color_accent_primary=accent,
        color_accent_secondary="#818cf8",
        color_status_success="#22c55e",
        color_status_warning="#f59e0b",
        color_status_error="#ef4444",
        color_status_info="#38bdf8",
        color_border_default="#334155",
        color_border_strong="#475569",
        spacing_xs="0.25rem",
        spacing_sm="0.5rem",
        spacing_md="1rem",
        spacing_lg="1.5rem",
        spacing_xl="2rem",
        font_family_base="'Inter', system-ui, sans-serif",
        font_size_sm="0.875rem",
        font_size_md="1rem",
        font_size_lg="1.125rem",
        font_weight_normal="400",
        font_weight_bold="700",
        border_radius_sm="0.25rem",
        border_radius_md="0.5rem",
        border_radius_lg="1rem",
    )


def _dark_instance(
    *, revision: ModelSemVer, accent: str = "#6366f1"
) -> ModelThemeInstance:
    return ModelThemeInstance(
        theme_id="onex.theme.dark",
        schema_version=ModelSemVer(major=1, minor=0, patch=0),
        instance_revision=revision,
        summary="Dark theme fixture",
        tokens=_dark_tokens(accent=accent),
    )


def _write_instance(root: Path, instance: ModelThemeInstance) -> Path:
    """Write ``instance`` into a catalog tree the way a publish would."""
    target = root / instance.theme_id / f"{instance.instance_revision}.yaml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(serialize_data_to_yaml(instance.model_dump(mode="json")))
    return target


# ---------------------------------------------------------------------------
# The shipped catalog
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPackagedThemeCatalog:
    """The instance documents that ship with omnibase_core."""

    def test_catalog_root_is_packaged_data(self) -> None:
        assert THEME_CATALOG_ROOT.is_dir()

    def test_light_dark_warm_instances_exist_and_validate(self) -> None:
        catalog = load_packaged_theme_catalog()
        shipped = {entry.theme_id for entry in catalog.entries}
        assert shipped == set(_SHIPPED_THEME_IDS)

    def test_every_shipped_instance_document_validates_against_the_schema(
        self,
    ) -> None:
        """This is the CI validation the ticket requires (C1a)."""
        documents = sorted(THEME_CATALOG_ROOT.rglob("*.yaml"))
        assert documents, "no theme instance documents found"
        for document in documents:
            instance = load_theme_instance(document)
            assert isinstance(instance.tokens, ModelRendererThemeContract)

    def test_shipped_entries_carry_a_digest_and_a_source_path(self) -> None:
        catalog = load_packaged_theme_catalog()
        for entry in catalog.entries:
            assert entry.content_digest.startswith("sha256:")
            assert (THEME_CATALOG_ROOT / entry.source_path).is_file()


# ---------------------------------------------------------------------------
# Three version axes (C1b)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestThreeVersionAxes:
    """schema version, instance revision, and content digest are distinct."""

    def test_instance_declares_schema_version_and_instance_revision_separately(
        self,
    ) -> None:
        instance = _dark_instance(revision=ModelSemVer(major=2, minor=3, patch=1))
        assert instance.schema_version == ModelSemVer(major=1, minor=0, patch=0)
        assert instance.instance_revision == ModelSemVer(major=2, minor=3, patch=1)
        assert instance.schema_version != instance.instance_revision

    def test_declared_schema_version_must_match_the_token_contract_version(
        self,
    ) -> None:
        with pytest.raises(ValidationError):
            ModelThemeInstance(
                theme_id="onex.theme.dark",
                schema_version=ModelSemVer(major=2, minor=0, patch=0),
                instance_revision=ModelSemVer(major=1, minor=0, patch=0),
                summary="mismatched schema version",
                tokens=_dark_tokens(),
            )

    def test_declared_theme_id_must_match_the_token_theme_id(self) -> None:
        with pytest.raises(ValidationError):
            ModelThemeInstance(
                theme_id="onex.theme.light",
                schema_version=ModelSemVer(major=1, minor=0, patch=0),
                instance_revision=ModelSemVer(major=1, minor=0, patch=0),
                summary="mismatched theme id",
                tokens=_dark_tokens(),
            )

    def test_a_value_change_moves_the_digest_but_not_the_schema_version(self) -> None:
        base = _dark_instance(revision=ModelSemVer(major=1, minor=0, patch=0))
        changed = _dark_instance(
            revision=ModelSemVer(major=1, minor=1, patch=0), accent="#a855f7"
        )
        assert base.schema_version == changed.schema_version
        assert compute_theme_content_digest(base) != compute_theme_content_digest(
            changed
        )


# ---------------------------------------------------------------------------
# GC.2 — digest determinism
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestContentDigest:
    """GC.2: two surfaces loading one catalog entry report one digest."""

    def test_digest_is_deterministic_across_independent_loads(self) -> None:
        first = load_packaged_theme_catalog()
        second = load_packaged_theme_catalog()
        assert {(e.theme_id, e.content_digest) for e in first.entries} == {
            (e.theme_id, e.content_digest) for e in second.entries
        }

    def test_digest_is_stable_across_a_serialize_reload_round_trip(
        self, tmp_path: Path
    ) -> None:
        instance = _dark_instance(revision=ModelSemVer(major=1, minor=0, patch=0))
        path = _write_instance(tmp_path, instance)
        reloaded = load_theme_instance(path)
        assert compute_theme_content_digest(reloaded) == compute_theme_content_digest(
            instance
        )

    def test_digest_is_prefixed_and_hex(self) -> None:
        digest = compute_theme_content_digest(
            _dark_instance(revision=ModelSemVer(major=1, minor=0, patch=0))
        )
        algorithm, _, hexdigest = digest.partition(":")
        assert algorithm == "sha256"
        assert len(hexdigest) == 64
        assert set(hexdigest) <= set("0123456789abcdef")


# ---------------------------------------------------------------------------
# Catalog construction
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCatalogConstruction:
    def test_catalog_indexes_every_published_revision(self, tmp_path: Path) -> None:
        _write_instance(
            tmp_path, _dark_instance(revision=ModelSemVer(major=1, minor=0, patch=0))
        )
        _write_instance(
            tmp_path,
            _dark_instance(
                revision=ModelSemVer(major=1, minor=1, patch=0), accent="#a855f7"
            ),
        )
        catalog = build_theme_catalog(tmp_path)
        assert len(catalog.entries) == 2

    def test_duplicate_theme_revision_is_rejected(self) -> None:
        entry = ModelThemeCatalogEntry(
            theme_id="onex.theme.dark",
            schema_version=ModelSemVer(major=1, minor=0, patch=0),
            instance_revision=ModelSemVer(major=1, minor=0, patch=0),
            content_digest="sha256:" + "0" * 64,
            source_path="onex.theme.dark/1.0.0.yaml",
        )
        with pytest.raises(ValidationError):
            ModelThemeCatalog(
                catalog_version=ModelSemVer(major=1, minor=0, patch=0),
                entries=(entry, entry),
            )

    def test_entry_lookup_resolves_a_published_revision(self, tmp_path: Path) -> None:
        instance = _dark_instance(revision=ModelSemVer(major=1, minor=0, patch=0))
        _write_instance(tmp_path, instance)
        catalog = build_theme_catalog(tmp_path)
        entry = catalog.entry_for(
            "onex.theme.dark", ModelSemVer(major=1, minor=0, patch=0)
        )
        assert entry.content_digest == compute_theme_content_digest(instance)

    def test_entry_lookup_fails_closed_on_an_unpublished_revision(
        self, tmp_path: Path
    ) -> None:
        _write_instance(
            tmp_path, _dark_instance(revision=ModelSemVer(major=1, minor=0, patch=0))
        )
        catalog = build_theme_catalog(tmp_path)
        with pytest.raises(ModelOnexError):
            catalog.entry_for("onex.theme.dark", ModelSemVer(major=9, minor=9, patch=9))

    def test_a_document_whose_filename_disagrees_with_its_revision_is_rejected(
        self, tmp_path: Path
    ) -> None:
        instance = _dark_instance(revision=ModelSemVer(major=1, minor=0, patch=0))
        target = tmp_path / instance.theme_id / "9.9.9.yaml"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(serialize_data_to_yaml(instance.model_dump(mode="json")))
        with pytest.raises(ModelOnexError):
            build_theme_catalog(tmp_path)


# ---------------------------------------------------------------------------
# GC.1 — publish / activate / rollback
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPublishActivateRollback:
    """GC.1: a value change is a data edit, and rollback restores the bytes."""

    def test_publishing_a_revision_does_not_change_what_is_activated(
        self, tmp_path: Path
    ) -> None:
        _write_instance(
            tmp_path, _dark_instance(revision=ModelSemVer(major=1, minor=0, patch=0))
        )
        catalog = build_theme_catalog(tmp_path)
        activation = activate_theme(
            catalog=catalog,
            surface_id="omnidash",
            theme_id="onex.theme.dark",
            instance_revision=ModelSemVer(major=1, minor=0, patch=0),
        )

        # Publish a second revision — activation pointer must not move.
        _write_instance(
            tmp_path,
            _dark_instance(
                revision=ModelSemVer(major=1, minor=1, patch=0), accent="#a855f7"
            ),
        )
        republished = build_theme_catalog(tmp_path)
        assert len(republished.entries) == 2
        assert activation.instance_revision == ModelSemVer(major=1, minor=0, patch=0)

    def test_activation_carries_the_digest_of_the_revision_it_points_at(
        self, tmp_path: Path
    ) -> None:
        instance = _dark_instance(revision=ModelSemVer(major=1, minor=0, patch=0))
        _write_instance(tmp_path, instance)
        catalog = build_theme_catalog(tmp_path)
        activation = activate_theme(
            catalog=catalog,
            surface_id="omnidash",
            theme_id="onex.theme.dark",
            instance_revision=ModelSemVer(major=1, minor=0, patch=0),
        )
        assert activation.content_digest == compute_theme_content_digest(instance)
        assert activation.activation_sequence == 1
        assert activation.superseded_revision is None

    def test_a_token_value_changes_without_editing_a_python_class(
        self, tmp_path: Path
    ) -> None:
        """GC.1 proper: publish v1, publish v1.1 with a new value, activate it."""
        original = _dark_instance(revision=ModelSemVer(major=1, minor=0, patch=0))
        updated = _dark_instance(
            revision=ModelSemVer(major=1, minor=1, patch=0), accent="#a855f7"
        )
        _write_instance(tmp_path, original)
        _write_instance(tmp_path, updated)
        catalog = build_theme_catalog(tmp_path)

        first = activate_theme(
            catalog=catalog,
            surface_id="omnidash",
            theme_id="onex.theme.dark",
            instance_revision=ModelSemVer(major=1, minor=0, patch=0),
        )
        second = activate_theme(
            catalog=catalog,
            surface_id="omnidash",
            theme_id="onex.theme.dark",
            instance_revision=ModelSemVer(major=1, minor=1, patch=0),
            current=first,
        )

        assert second.activation_sequence == 2
        assert second.superseded_revision == ModelSemVer(major=1, minor=0, patch=0)
        assert second.content_digest != first.content_digest
        assert (
            load_theme_instance(
                tmp_path
                / (
                    catalog.entry_for("onex.theme.dark", second.instance_revision)
                ).source_path
            ).tokens.color_accent_primary
            == "#a855f7"
        )

    def test_rollback_moves_the_pointer_and_restores_the_original_digest(
        self, tmp_path: Path
    ) -> None:
        original = _dark_instance(revision=ModelSemVer(major=1, minor=0, patch=0))
        updated = _dark_instance(
            revision=ModelSemVer(major=1, minor=1, patch=0), accent="#a855f7"
        )
        _write_instance(tmp_path, original)
        _write_instance(tmp_path, updated)
        catalog = build_theme_catalog(tmp_path)

        first = activate_theme(
            catalog=catalog,
            surface_id="omnidash",
            theme_id="onex.theme.dark",
            instance_revision=ModelSemVer(major=1, minor=0, patch=0),
        )
        second = activate_theme(
            catalog=catalog,
            surface_id="omnidash",
            theme_id="onex.theme.dark",
            instance_revision=ModelSemVer(major=1, minor=1, patch=0),
            current=first,
        )
        rolled_back = roll_back_theme(catalog=catalog, current=second)

        assert rolled_back.instance_revision == first.instance_revision
        # The digest proves the OLD BYTES came back, not a lookalike recompile.
        assert rolled_back.content_digest == first.content_digest
        assert rolled_back.activation_sequence == 3
        assert rolled_back.superseded_revision == ModelSemVer(major=1, minor=1, patch=0)

    def test_rollback_fails_closed_when_there_is_nothing_to_roll_back_to(
        self, tmp_path: Path
    ) -> None:
        _write_instance(
            tmp_path, _dark_instance(revision=ModelSemVer(major=1, minor=0, patch=0))
        )
        catalog = build_theme_catalog(tmp_path)
        first = activate_theme(
            catalog=catalog,
            surface_id="omnidash",
            theme_id="onex.theme.dark",
            instance_revision=ModelSemVer(major=1, minor=0, patch=0),
        )
        with pytest.raises(ModelOnexError):
            roll_back_theme(catalog=catalog, current=first)

    def test_activating_an_unpublished_revision_fails_closed(
        self, tmp_path: Path
    ) -> None:
        _write_instance(
            tmp_path, _dark_instance(revision=ModelSemVer(major=1, minor=0, patch=0))
        )
        catalog = build_theme_catalog(tmp_path)
        with pytest.raises(ModelOnexError):
            activate_theme(
                catalog=catalog,
                surface_id="omnidash",
                theme_id="onex.theme.dark",
                instance_revision=ModelSemVer(major=7, minor=0, patch=0),
            )

    def test_activation_is_frozen(self) -> None:
        activation = ModelThemeActivation(
            surface_id="omnidash",
            theme_id="onex.theme.dark",
            instance_revision=ModelSemVer(major=1, minor=0, patch=0),
            content_digest="sha256:" + "a" * 64,
            activation_sequence=1,
        )
        with pytest.raises(ValidationError):
            activation.surface_id = "other"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# C1d — the TS mirror carries the schema
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestTypeScriptMirrorRegistration:
    """The emitter must carry the theme schema and the instance layer."""

    @staticmethod
    def _emitter_models() -> dict[str, object]:
        path = _REPO_ROOT / "scripts" / "emit_ts_types.py"
        spec = importlib.util.spec_from_file_location("_emit_ts_types_probe", path)
        assert spec is not None
        assert spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        try:
            spec.loader.exec_module(module)
            return dict(module.MODELS)
        finally:
            sys.modules.pop(spec.name, None)

    def test_emitter_registers_the_theme_schema_and_instance_layer(self) -> None:
        models = self._emitter_models()
        for name in (
            "ModelRendererThemeContract",
            "ModelThemeInstance",
            "ModelThemeCatalogEntry",
            "ModelThemeCatalog",
            "ModelThemeActivation",
        ):
            assert name in models, f"{name} missing from emit_ts_types MODELS"

    def test_instance_json_schema_embeds_the_token_schema(self) -> None:
        schema = ModelThemeInstance.model_json_schema()
        defs = schema.get("$defs", {})
        assert "ModelRendererThemeContract" in defs
        assert (
            "color_accent_primary" in defs["ModelRendererThemeContract"]["properties"]
        )
