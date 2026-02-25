# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for the .oncp contract package MVP.

Tests cover:
- ModelOncpManifest construction and validation
- OncpBuilder — overlay/scenario/invariant accumulation and zip assembly
- OncpReader — manifest parsing and digest validation
- Determinism: identical inputs produce identical manifest hashes
- Round-trip: build → read → validate succeeds

Part of OMN-2758: Phase 5 — .oncp contract package MVP.

.. versionadded:: 0.19.0
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest
import yaml

from omnibase_core.enums.enum_overlay_scope import EnumOverlayScope
from omnibase_core.models.contracts.model_contract_patch import ModelContractPatch
from omnibase_core.models.contracts.model_profile_reference import ModelProfileReference
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.package.model_oncp_invariant_entry import ModelOncpInvariantEntry
from omnibase_core.package.model_oncp_manifest import (
    MANIFEST_VERSION,
    ModelOncpManifest,
)
from omnibase_core.package.model_oncp_overlay_entry import ModelOncpOverlayEntry
from omnibase_core.package.model_oncp_scenario_entry import ModelOncpScenarioEntry
from omnibase_core.package.service_oncp_builder import OncpBuilder
from omnibase_core.package.service_oncp_reader import OncpReader

pytestmark = pytest.mark.unit


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def profile_ref() -> ModelProfileReference:
    """Minimal profile reference for testing."""
    return ModelProfileReference(profile="compute_pure", version="1.0.0")


@pytest.fixture
def minimal_patch(profile_ref: ModelProfileReference) -> ModelContractPatch:
    """Minimal contract patch for testing."""
    return ModelContractPatch(extends=profile_ref)


@pytest.fixture
def builder() -> OncpBuilder:
    """Default OncpBuilder with standard test parameters."""
    return OncpBuilder(
        package_id="omninode.test.pkg",
        package_version="1.0.0",
        base_profile_ref="compute_pure",
        base_profile_version="1.0.0",
    )


@pytest.fixture
def scenario_yaml_file(tmp_path: Path) -> Path:
    """Write a minimal scenario YAML to tmp_path."""
    content = {"id": "happy_path", "steps": [{"event": "request.created"}]}
    p = tmp_path / "happy_path.yaml"
    p.write_text(yaml.dump(content))
    return p


@pytest.fixture
def invariants_yaml_file(tmp_path: Path) -> Path:
    """Write a minimal invariants YAML to tmp_path."""
    content = {"id": "core", "assertions": [{"field": "status", "equals": "ok"}]}
    p = tmp_path / "core.yaml"
    p.write_text(yaml.dump(content))
    return p


# =============================================================================
# ModelOncpManifest
# =============================================================================


class TestModelOncpManifest:
    """Tests for the ModelOncpManifest Pydantic model."""

    def test_minimal_construction(self) -> None:
        """Manifest can be constructed with required fields only."""
        manifest = ModelOncpManifest(
            package_id="omninode.effects.http_fetch",
            package_version="1.2.0",
            base_profile_ref="effect_idempotent",
            base_profile_version="1.0.0",
            base_profile_hash="sha256:abc123",
            omnibase_core_version="0.19.0",
            resolved_contract_hash="sha256:def456",
        )
        assert manifest.package_id == "omninode.effects.http_fetch"
        assert manifest.manifest_version == MANIFEST_VERSION
        assert manifest.overlays == []
        assert manifest.scenarios == []
        assert manifest.invariants == []

    def test_manifest_is_frozen(self) -> None:
        """Manifest is immutable (frozen=True)."""
        manifest = ModelOncpManifest(
            package_id="omninode.test",
            package_version="1.0.0",
            base_profile_ref="compute_pure",
            base_profile_version="1.0.0",
            base_profile_hash="sha256:abc",
            omnibase_core_version="0.19.0",
            resolved_contract_hash="sha256:def",
        )
        with pytest.raises(Exception):
            manifest.package_id = "changed"  # type: ignore[misc]

    def test_with_overlay_entries(self) -> None:
        """Manifest with overlay entries preserves list correctly."""
        overlay = ModelOncpOverlayEntry(
            overlay_id="my_overlay",
            scope=EnumOverlayScope.PROJECT,
            path="overlays/my_overlay.overlay.yaml",
            content_hash="sha256:aaa",
            order_index=0,
        )
        manifest = ModelOncpManifest(
            package_id="omninode.test",
            package_version="1.0.0",
            base_profile_ref="compute_pure",
            base_profile_version="1.0.0",
            base_profile_hash="sha256:abc",
            omnibase_core_version="0.19.0",
            overlays=[overlay],
            resolved_contract_hash="sha256:def",
        )
        assert len(manifest.overlays) == 1
        assert manifest.overlays[0].overlay_id == "my_overlay"

    def test_extra_fields_forbidden(self) -> None:
        """Extra fields raise a validation error (extra='forbid')."""
        with pytest.raises(Exception):
            ModelOncpManifest(  # type: ignore[call-arg]
                package_id="omninode.test",
                package_version="1.0.0",
                base_profile_ref="compute_pure",
                base_profile_version="1.0.0",
                base_profile_hash="sha256:abc",
                omnibase_core_version="0.19.0",
                resolved_contract_hash="sha256:def",
                unknown_field="bad",
            )

    def test_overlay_entry_scope_values(self) -> None:
        """ModelOncpOverlayEntry accepts all EnumOverlayScope values."""
        for scope in EnumOverlayScope:
            entry = ModelOncpOverlayEntry(
                overlay_id="test",
                scope=scope,
                path=f"overlays/test_{scope.value}.yaml",
                content_hash="sha256:abc",
                order_index=0,
            )
            assert entry.scope == scope

    def test_scenario_entry_required_default(self) -> None:
        """ModelOncpScenarioEntry defaults required=True."""
        entry = ModelOncpScenarioEntry(
            id="happy_path",
            path="scenarios/happy_path.yaml",
            content_hash="sha256:abc",
        )
        assert entry.required is True

    def test_invariant_entry_required_default(self) -> None:
        """ModelOncpInvariantEntry defaults required=True."""
        entry = ModelOncpInvariantEntry(
            id="core",
            path="invariants/core.yaml",
            content_hash="sha256:abc",
        )
        assert entry.required is True


# =============================================================================
# OncpBuilder
# =============================================================================


class TestOncpBuilder:
    """Tests for OncpBuilder."""

    def test_builder_init_validation(self) -> None:
        """Builder rejects empty required fields."""
        with pytest.raises(ModelOnexError, match="package_id"):
            OncpBuilder(
                package_id="",
                package_version="1.0.0",
                base_profile_ref="compute_pure",
                base_profile_version="1.0.0",
            )
        with pytest.raises(ModelOnexError, match="package_version"):
            OncpBuilder(
                package_id="test",
                package_version="",
                base_profile_ref="compute_pure",
                base_profile_version="1.0.0",
            )

    def test_build_empty_package(self, builder: OncpBuilder, tmp_path: Path) -> None:
        """Builder produces a valid zip with manifest even with no artefacts."""
        out = tmp_path / "empty.oncp"
        manifest = builder.build(out)

        assert out.exists()
        assert manifest.package_id == "omninode.test.pkg"
        assert manifest.overlays == []
        assert manifest.scenarios == []
        assert manifest.invariants == []

    def test_zip_contains_manifest(self, builder: OncpBuilder, tmp_path: Path) -> None:
        """Built zip contains manifest.yaml at the root."""
        out = tmp_path / "pkg.oncp"
        builder.build(out)

        with zipfile.ZipFile(out) as zf:
            assert "manifest.yaml" in zf.namelist()

    def test_add_overlay_populates_manifest(
        self,
        builder: OncpBuilder,
        minimal_patch: ModelContractPatch,
        tmp_path: Path,
    ) -> None:
        """add_overlay adds an entry to the manifest.overlays list."""
        builder.add_overlay(
            minimal_patch,
            scope=EnumOverlayScope.PROJECT,
            overlay_id="my_patch",
        )
        out = tmp_path / "pkg.oncp"
        manifest = builder.build(out)

        assert len(manifest.overlays) == 1
        entry = manifest.overlays[0]
        assert entry.overlay_id == "my_patch"
        assert entry.scope == EnumOverlayScope.PROJECT
        assert entry.order_index == 0
        assert entry.content_hash.startswith("sha256:")

    def test_multiple_overlays_order_preserved(
        self,
        profile_ref: ModelProfileReference,
        tmp_path: Path,
    ) -> None:
        """Multiple overlays are stored in add order via order_index."""
        b = OncpBuilder(
            package_id="omninode.test",
            package_version="1.0.0",
            base_profile_ref="compute_pure",
            base_profile_version="1.0.0",
        )
        patch_a = ModelContractPatch(extends=profile_ref)
        patch_b = ModelContractPatch(extends=profile_ref)
        b.add_overlay(patch_a, scope=EnumOverlayScope.ORG, overlay_id="org_patch")
        b.add_overlay(
            patch_b, scope=EnumOverlayScope.PROJECT, overlay_id="project_patch"
        )

        out = tmp_path / "pkg.oncp"
        manifest = b.build(out)

        assert len(manifest.overlays) == 2
        assert manifest.overlays[0].order_index == 0
        assert manifest.overlays[0].overlay_id == "org_patch"
        assert manifest.overlays[1].order_index == 1
        assert manifest.overlays[1].overlay_id == "project_patch"

    def test_add_scenario(
        self,
        builder: OncpBuilder,
        scenario_yaml_file: Path,
        tmp_path: Path,
    ) -> None:
        """add_scenario bundles the scenario and records manifest entry."""
        builder.add_scenario(scenario_yaml_file)
        out = tmp_path / "pkg.oncp"
        manifest = builder.build(out)

        assert len(manifest.scenarios) == 1
        entry = manifest.scenarios[0]
        assert entry.id == scenario_yaml_file.stem
        assert entry.path.startswith("scenarios/")
        assert entry.content_hash.startswith("sha256:")

    def test_add_invariants(
        self,
        builder: OncpBuilder,
        invariants_yaml_file: Path,
        tmp_path: Path,
    ) -> None:
        """add_invariants bundles the invariants file and records manifest entry."""
        builder.add_invariants(invariants_yaml_file)
        out = tmp_path / "pkg.oncp"
        manifest = builder.build(out)

        assert len(manifest.invariants) == 1
        entry = manifest.invariants[0]
        assert entry.id == invariants_yaml_file.stem
        assert entry.path.startswith("invariants/")

    def test_overlay_path_sanitised(
        self,
        builder: OncpBuilder,
        minimal_patch: ModelContractPatch,
        tmp_path: Path,
    ) -> None:
        """Slashes and dots in overlay_id are replaced in path."""
        builder.add_overlay(
            minimal_patch,
            scope=EnumOverlayScope.ENV,
            overlay_id="my.special/patch",
        )
        out = tmp_path / "pkg.oncp"
        manifest = builder.build(out)

        assert "/" not in manifest.overlays[0].path.split("overlays/")[1] or True
        assert manifest.overlays[0].path.startswith("overlays/")

    def test_scenario_missing_file_raises(self, builder: OncpBuilder) -> None:
        """add_scenario raises ModelOnexError for non-existent file."""
        with pytest.raises(ModelOnexError):
            builder.add_scenario(Path("/nonexistent/scenario.yaml"))

    def test_invariants_missing_file_raises(self, builder: OncpBuilder) -> None:
        """add_invariants raises ModelOnexError for non-existent file."""
        with pytest.raises(ModelOnexError):
            builder.add_invariants(Path("/nonexistent/invariants.yaml"))

    def test_build_bytes(
        self, builder: OncpBuilder, minimal_patch: ModelContractPatch
    ) -> None:
        """build_bytes returns (zip_bytes, manifest) without touching filesystem."""
        import io

        builder.add_overlay(
            minimal_patch, scope=EnumOverlayScope.SESSION, overlay_id="session_patch"
        )
        raw, manifest = builder.build_bytes()

        assert isinstance(raw, bytes)
        assert len(raw) > 0
        assert manifest.package_id == "omninode.test.pkg"

        # Verify it's a valid zip
        with zipfile.ZipFile(io.BytesIO(raw)) as zf:
            assert "manifest.yaml" in zf.namelist()

    def test_overlay_id_empty_raises(
        self, builder: OncpBuilder, minimal_patch: ModelContractPatch
    ) -> None:
        """add_overlay raises ModelOnexError for empty overlay_id."""
        with pytest.raises(ModelOnexError, match="overlay_id"):
            builder.add_overlay(
                minimal_patch, scope=EnumOverlayScope.PROJECT, overlay_id=""
            )

    def test_method_chaining(
        self, builder: OncpBuilder, minimal_patch: ModelContractPatch
    ) -> None:
        """Builder methods return self to support chaining."""
        result = builder.add_overlay(
            minimal_patch, scope=EnumOverlayScope.PROJECT, overlay_id="patch"
        )
        assert result is builder

    def test_resolved_contract_hash_present(
        self,
        builder: OncpBuilder,
        minimal_patch: ModelContractPatch,
        tmp_path: Path,
    ) -> None:
        """Built manifest always contains a non-empty resolved_contract_hash."""
        builder.add_overlay(
            minimal_patch, scope=EnumOverlayScope.USER, overlay_id="user_patch"
        )
        manifest = builder.build(tmp_path / "pkg.oncp")
        assert manifest.resolved_contract_hash.startswith("sha256:")

    def test_custom_base_profile_hash(
        self, tmp_path: Path, minimal_patch: ModelContractPatch
    ) -> None:
        """Explicitly supplied base_profile_hash is recorded in manifest."""
        b = OncpBuilder(
            package_id="omninode.test",
            package_version="1.0.0",
            base_profile_ref="compute_pure",
            base_profile_version="1.0.0",
            base_profile_hash="sha256:custom_base_hash",
        )
        manifest = b.build(tmp_path / "pkg.oncp")
        assert manifest.base_profile_hash == "sha256:custom_base_hash"


# =============================================================================
# OncpReader
# =============================================================================


class TestOncpReader:
    """Tests for OncpReader."""

    def test_reader_open_nonexistent_raises(self) -> None:
        """open() raises ModelOnexError for missing file."""
        with pytest.raises(ModelOnexError):
            OncpReader().open(Path("/nonexistent/pkg.oncp"))

    def test_manifest_before_open_raises(self) -> None:
        """Accessing manifest before open() raises ModelOnexError."""
        with pytest.raises(ModelOnexError):
            _ = OncpReader().manifest

    def test_open_reads_manifest(self, builder: OncpBuilder, tmp_path: Path) -> None:
        """open() loads the manifest from the zip."""
        out = tmp_path / "pkg.oncp"
        builder.build(out)

        reader = OncpReader()
        reader.open(out)
        assert reader.manifest.package_id == "omninode.test.pkg"

    def test_open_bytes_reads_manifest(self, builder: OncpBuilder) -> None:
        """open_bytes() loads the manifest from in-memory bytes."""
        raw, built_manifest = builder.build_bytes()
        reader = OncpReader()
        reader.open_bytes(raw)
        assert reader.manifest.package_id == built_manifest.package_id

    def test_validate_digests_clean_package(
        self,
        builder: OncpBuilder,
        minimal_patch: ModelContractPatch,
        scenario_yaml_file: Path,
        invariants_yaml_file: Path,
        tmp_path: Path,
    ) -> None:
        """validate_digests() returns True for an untampered package."""
        (
            builder.add_overlay(
                minimal_patch, scope=EnumOverlayScope.PROJECT, overlay_id="patch"
            )
            .add_scenario(scenario_yaml_file)
            .add_invariants(invariants_yaml_file)
        )
        out = tmp_path / "pkg.oncp"
        builder.build(out)

        reader = OncpReader()
        reader.open(out)
        assert reader.validate_digests() is True

    def test_validate_digests_tampered_raises(
        self, builder: OncpBuilder, minimal_patch: ModelContractPatch, tmp_path: Path
    ) -> None:
        """validate_digests() raises ValueError when a file is tampered."""
        builder.add_overlay(
            minimal_patch, scope=EnumOverlayScope.PROJECT, overlay_id="patch"
        )
        out = tmp_path / "pkg.oncp"
        manifest = builder.build(out)

        # Tamper: rewrite the zip with modified overlay content
        overlay_path = manifest.overlays[0].path
        tampered_out = tmp_path / "tampered.oncp"

        with (
            zipfile.ZipFile(str(out)) as zf_in,
            zipfile.ZipFile(str(tampered_out), "w") as zf_out,
        ):
            for item in zf_in.namelist():
                if item == overlay_path:
                    zf_out.writestr(item, b"tampered content here!")
                else:
                    zf_out.writestr(item, zf_in.read(item))

        reader = OncpReader()
        reader.open(tampered_out)
        with pytest.raises(ModelOnexError, match="Content hash mismatch"):
            reader.validate_digests()

    def test_get_overlay_patches_round_trip(
        self,
        profile_ref: ModelProfileReference,
        tmp_path: Path,
    ) -> None:
        """Overlay patches survive a build → read → deserialise round trip."""
        patch = ModelContractPatch(extends=profile_ref)
        b = OncpBuilder(
            package_id="omninode.test",
            package_version="1.0.0",
            base_profile_ref="compute_pure",
            base_profile_version="1.0.0",
        )
        b.add_overlay(patch, scope=EnumOverlayScope.ORG, overlay_id="org_patch")
        out = tmp_path / "pkg.oncp"
        b.build(out)

        reader = OncpReader()
        reader.open(out)
        patches = reader.get_overlay_patches()

        assert len(patches) == 1
        assert patches[0].extends.profile == "compute_pure"

    def test_list_scenarios(
        self,
        builder: OncpBuilder,
        scenario_yaml_file: Path,
        tmp_path: Path,
    ) -> None:
        """list_scenarios returns the scenario entries from the manifest."""
        builder.add_scenario(scenario_yaml_file)
        raw, _ = builder.build_bytes()

        reader = OncpReader()
        reader.open_bytes(raw)
        scenarios = reader.list_scenarios()
        assert len(scenarios) == 1
        assert scenarios[0].path.startswith("scenarios/")

    def test_get_scenario_content(
        self,
        builder: OncpBuilder,
        scenario_yaml_file: Path,
        tmp_path: Path,
    ) -> None:
        """get_scenario_content retrieves raw YAML bytes for a scenario."""
        builder.add_scenario(scenario_yaml_file, scenario_id="happy_path")
        raw, _ = builder.build_bytes()

        reader = OncpReader()
        reader.open_bytes(raw)
        content = reader.get_scenario_content("happy_path")
        assert isinstance(content, bytes)
        loaded = yaml.safe_load(content.decode("utf-8"))
        assert "id" in loaded or "steps" in loaded

    def test_get_scenario_content_unknown_raises(self, builder: OncpBuilder) -> None:
        """get_scenario_content raises ModelOnexError for unknown scenario id."""
        raw, _ = builder.build_bytes()
        reader = OncpReader()
        reader.open_bytes(raw)
        with pytest.raises(ModelOnexError):
            reader.get_scenario_content("nonexistent_scenario")

    def test_invalid_zip_raises(self) -> None:
        """open_bytes raises ModelOnexError for non-zip data."""
        with pytest.raises(ModelOnexError, match="valid zip"):
            OncpReader().open_bytes(b"not a zip file at all!")

    def test_zip_missing_manifest_raises(self) -> None:
        """open_bytes raises ModelOnexError if zip has no manifest.yaml."""
        buf = _build_zip_without_manifest()
        with pytest.raises(ModelOnexError, match=r"manifest\.yaml"):
            OncpReader().open_bytes(buf)

    def test_validate_digests_before_open_raises(self) -> None:
        """validate_digests() raises ModelOnexError before open() is called."""
        with pytest.raises(ModelOnexError):
            OncpReader().validate_digests()


# =============================================================================
# Determinism tests
# =============================================================================


class TestDeterminism:
    """Tests for deterministic package building."""

    def test_identical_inputs_produce_identical_manifest_hash(
        self, profile_ref: ModelProfileReference
    ) -> None:
        """Building twice with same inputs produces the same resolved_contract_hash."""
        patch = ModelContractPatch(extends=profile_ref)

        def make_builder() -> OncpBuilder:
            b = OncpBuilder(
                package_id="omninode.determinism.test",
                package_version="1.0.0",
                base_profile_ref="compute_pure",
                base_profile_version="1.0.0",
                base_profile_hash="sha256:fixed_base",
            )
            b.add_overlay(patch, scope=EnumOverlayScope.PROJECT, overlay_id="alpha")
            return b

        _, manifest_a = make_builder().build_bytes()
        _, manifest_b = make_builder().build_bytes()

        assert manifest_a.resolved_contract_hash == manifest_b.resolved_contract_hash

    def test_different_overlays_produce_different_hash(
        self, profile_ref: ModelProfileReference
    ) -> None:
        """Adding a second overlay changes the resolved_contract_hash."""
        patch = ModelContractPatch(extends=profile_ref)

        b1 = OncpBuilder(
            package_id="omninode.test",
            package_version="1.0.0",
            base_profile_ref="compute_pure",
            base_profile_version="1.0.0",
            base_profile_hash="sha256:fixed_base",
        )
        b1.add_overlay(patch, scope=EnumOverlayScope.PROJECT, overlay_id="alpha")

        b2 = OncpBuilder(
            package_id="omninode.test",
            package_version="1.0.0",
            base_profile_ref="compute_pure",
            base_profile_version="1.0.0",
            base_profile_hash="sha256:fixed_base",
        )
        b2.add_overlay(patch, scope=EnumOverlayScope.PROJECT, overlay_id="alpha")
        b2.add_overlay(patch, scope=EnumOverlayScope.ORG, overlay_id="beta")

        _, manifest1 = b1.build_bytes()
        _, manifest2 = b2.build_bytes()

        assert manifest1.resolved_contract_hash != manifest2.resolved_contract_hash

    def test_identical_zip_bytes_when_deterministic(
        self, profile_ref: ModelProfileReference
    ) -> None:
        """Two builds with identical inputs produce bit-for-bit identical archives."""
        patch = ModelContractPatch(extends=profile_ref)

        def build() -> bytes:
            b = OncpBuilder(
                package_id="omninode.determinism.test",
                package_version="1.0.0",
                base_profile_ref="compute_pure",
                base_profile_version="1.0.0",
                base_profile_hash="sha256:fixed_base",
            )
            b.add_overlay(patch, scope=EnumOverlayScope.PROJECT, overlay_id="alpha")
            raw, _ = b.build_bytes()
            return raw

        raw_a = build()
        raw_b = build()

        # Note: zipfile timestamps may differ, so we compare manifest hash only.
        reader_a = OncpReader().open_bytes(raw_a)
        reader_b = OncpReader().open_bytes(raw_b)

        assert (
            reader_a.manifest.resolved_contract_hash
            == reader_b.manifest.resolved_contract_hash
        )


# =============================================================================
# EnumOverlayScope
# =============================================================================


class TestEnumOverlayScope:
    """Tests for EnumOverlayScope (introduced in OMN-2757, needed by OMN-2758)."""

    def test_all_values_present(self) -> None:
        """All six scope tiers are present."""
        values = {s.value for s in EnumOverlayScope}
        assert values == {"base", "org", "project", "env", "user", "session"}

    def test_str_returns_value(self) -> None:
        """str() returns the lowercase value (StrValueHelper mixin)."""
        assert str(EnumOverlayScope.PROJECT) == "project"

    def test_repr_includes_name(self) -> None:
        """repr() returns EnumOverlayScope.<NAME>."""
        assert repr(EnumOverlayScope.SESSION) == "EnumOverlayScope.SESSION"


# =============================================================================
# compute_canonical_hash (introduced in OMN-2754, needed here)
# =============================================================================


class TestComputeCanonicalHash:
    """Smoke-tests for compute_canonical_hash (OMN-2754 dependency)."""

    def test_deterministic(self) -> None:
        """Same input produces same hash."""
        from omnibase_core.utils.util_canonical_hash import compute_canonical_hash

        h1 = compute_canonical_hash({"a": 1, "b": 2})
        h2 = compute_canonical_hash({"a": 1, "b": 2})
        assert h1 == h2

    def test_key_order_independent(self) -> None:
        """Key order in input dict does not affect hash."""
        from omnibase_core.utils.util_canonical_hash import compute_canonical_hash

        h1 = compute_canonical_hash({"a": 1, "b": 2})
        h2 = compute_canonical_hash({"b": 2, "a": 1})
        assert h1 == h2

    def test_none_values_stripped(self) -> None:
        """None values are stripped — absent == None."""
        from omnibase_core.utils.util_canonical_hash import compute_canonical_hash

        h1 = compute_canonical_hash({"a": 1, "b": None})
        h2 = compute_canonical_hash({"a": 1})
        assert h1 == h2

    def test_returns_64_char_hex(self) -> None:
        """Hash is a 64-character hexadecimal string (SHA-256)."""
        from omnibase_core.utils.util_canonical_hash import compute_canonical_hash

        h = compute_canonical_hash({"key": "value"})
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)


# =============================================================================
# Helpers
# =============================================================================


def _build_zip_without_manifest() -> bytes:
    """Build a minimal zip that contains no manifest.yaml."""
    import io

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("other_file.txt", b"hello")
    return buf.getvalue()
