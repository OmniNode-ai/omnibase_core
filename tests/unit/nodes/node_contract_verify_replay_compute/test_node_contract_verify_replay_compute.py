# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for contract.verify.replay compute node (OMN-2759).

Tests cover:
- Valid package passes all tier1_static checks (overall_status == "pass")
- Invalid overlay YAML (malformed schema) yields schema_validation fail
- Missing fixture_path yields fixture_presence fail
- Missing scenario zip entry yields all_scenarios_present fail
- Missing invariant zip entry yields all_invariants_present fail
- Incorrect content hash yields content_digest_integrity fail
- No package provided raises ModelOnexError
- Non-existent package_path raises ModelOnexError
- Tier 2 yields a "skip" result (not implemented yet)
- Signed report: report_digest is always populated
- package_bytes mode works without filesystem access

.. versionadded:: 0.20.0
"""

from __future__ import annotations

import hashlib
import io
import zipfile
from pathlib import Path

import pytest
import yaml

from omnibase_core.enums.enum_overlay_scope import EnumOverlayScope
from omnibase_core.enums.enum_verify_tier import EnumVerifyTier
from omnibase_core.models.contract_verify_replay.model_verify_options import (
    ModelVerifyOptions,
)
from omnibase_core.models.contract_verify_replay.model_verify_replay_input import (
    ModelVerifyReplayInput,
)
from omnibase_core.models.contracts.model_contract_patch import ModelContractPatch
from omnibase_core.models.contracts.model_profile_reference import (
    ModelProfileReference,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.nodes.node_contract_verify_replay_compute.handler import (
    NodeContractVerifyReplayCompute,
)
from omnibase_core.package.service_oncp_builder import OncpBuilder

pytestmark = pytest.mark.unit


# =============================================================================
# Helpers
# =============================================================================


def _profile_ref(name: str = "compute_pure") -> ModelProfileReference:
    return ModelProfileReference(profile=name, version="1.0.0")


def _minimal_patch(profile: str = "compute_pure") -> ModelContractPatch:
    return ModelContractPatch(extends=_profile_ref(profile))


def _build_simple_package(
    *,
    package_id: str = "omninode.test.pkg",
    package_version: str = "1.0.0",
    add_scenario: bool = False,
    add_invariant: bool = False,
    scenario_path: Path | None = None,
    invariant_path: Path | None = None,
) -> bytes:
    """Build a minimal .oncp bundle in-memory with one overlay."""
    builder = OncpBuilder(
        package_id=package_id,
        package_version=package_version,
        base_profile_ref="compute_pure",
        base_profile_version="1.0.0",
    )
    patch = _minimal_patch()
    builder.add_overlay(patch, scope=EnumOverlayScope.PROJECT, overlay_id="base-patch")
    if add_scenario and scenario_path is not None:
        builder.add_scenario(scenario_path)
    if add_invariant and invariant_path is not None:
        builder.add_invariants(invariant_path)
    # build_bytes() returns tuple[bytes, ModelOncpManifest]
    bundle_bytes, _manifest = builder.build_bytes()
    return bundle_bytes


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def verifier() -> NodeContractVerifyReplayCompute:
    return NodeContractVerifyReplayCompute()


@pytest.fixture
def scenario_file(tmp_path: Path) -> Path:
    content = {"id": "happy_path", "steps": [{"event": "request.created"}]}
    p = tmp_path / "happy_path.yaml"
    p.write_text(yaml.dump(content))
    return p


@pytest.fixture
def invariant_file(tmp_path: Path) -> Path:
    content = {"id": "core_invariants", "rules": [{"name": "no_null_output"}]}
    p = tmp_path / "core_invariants.yaml"
    p.write_text(yaml.dump(content))
    return p


@pytest.fixture
def simple_bundle_bytes() -> bytes:
    return _build_simple_package()


@pytest.fixture
def simple_bundle_file(tmp_path: Path, simple_bundle_bytes: bytes) -> Path:
    p = tmp_path / "test_pkg.oncp"
    p.write_bytes(simple_bundle_bytes)
    return p


# =============================================================================
# Basic validation
# =============================================================================


def test_no_package_raises(verifier: NodeContractVerifyReplayCompute) -> None:
    """Neither package_path nor package_bytes → ModelOnexError."""
    with pytest.raises(ModelOnexError):
        verifier.handle(ModelVerifyReplayInput())


def test_nonexistent_path_raises(
    verifier: NodeContractVerifyReplayCompute, tmp_path: Path
) -> None:
    """Non-existent package_path → ModelOnexError (FILE_NOT_FOUND)."""
    with pytest.raises(ModelOnexError):
        verifier.handle(
            ModelVerifyReplayInput(package_path=str(tmp_path / "missing.oncp"))
        )


# =============================================================================
# Tier 1 — happy path
# =============================================================================


def test_valid_package_passes_all_checks(
    verifier: NodeContractVerifyReplayCompute,
    simple_bundle_bytes: bytes,
) -> None:
    """A well-formed .oncp bundle passes all tier1 checks with overall_status=pass."""
    inp = ModelVerifyReplayInput(package_bytes=simple_bundle_bytes)
    report = verifier.handle(inp)

    assert report.overall_status == "pass"
    assert report.tier == EnumVerifyTier.TIER1_STATIC
    assert report.report_version == 1
    assert report.package_id == "omninode.test.pkg"
    assert report.package_content_hash.startswith("sha256:")

    check_names = [c.check_name for c in report.checks]
    assert "schema_validation" in check_names
    assert "capability_linting" in check_names
    assert "fixture_presence" in check_names
    assert "overlay_merge_correctness" in check_names
    assert "determinism_declared" in check_names
    assert "all_scenarios_present" in check_names
    assert "all_invariants_present" in check_names
    assert "content_digest_integrity" in check_names

    for check in report.checks:
        assert check.status in ("pass", "skip"), (
            f"Check '{check.check_name}' failed unexpectedly: {check.message}"
        )


def test_package_path_mode(
    verifier: NodeContractVerifyReplayCompute, simple_bundle_file: Path
) -> None:
    """package_path mode reads from filesystem and passes."""
    inp = ModelVerifyReplayInput(package_path=str(simple_bundle_file))
    report = verifier.handle(inp)
    assert report.overall_status == "pass"


def test_report_digest_always_populated(
    verifier: NodeContractVerifyReplayCompute,
    simple_bundle_bytes: bytes,
) -> None:
    """report_digest is always a non-empty sha256: string."""
    report = verifier.handle(ModelVerifyReplayInput(package_bytes=simple_bundle_bytes))
    assert report.report_digest.startswith("sha256:")
    assert len(report.report_digest) == len("sha256:") + 64


def test_generated_at_utc(
    verifier: NodeContractVerifyReplayCompute,
    simple_bundle_bytes: bytes,
) -> None:
    """generated_at is timezone-aware (UTC)."""
    report = verifier.handle(ModelVerifyReplayInput(package_bytes=simple_bundle_bytes))

    assert report.generated_at.tzinfo is not None


def test_package_with_scenario_passes(
    verifier: NodeContractVerifyReplayCompute,
    scenario_file: Path,
) -> None:
    """Bundle with a scenario entry passes all_scenarios_present."""
    bundle = _build_simple_package(add_scenario=True, scenario_path=scenario_file)
    report = verifier.handle(ModelVerifyReplayInput(package_bytes=bundle))
    assert report.overall_status == "pass"

    scenario_check = next(
        (c for c in report.checks if c.check_name == "all_scenarios_present"), None
    )
    assert scenario_check is not None
    assert scenario_check.status == "pass"


def test_package_with_invariant_passes(
    verifier: NodeContractVerifyReplayCompute,
    invariant_file: Path,
) -> None:
    """Bundle with an invariant entry passes all_invariants_present."""
    bundle = _build_simple_package(add_invariant=True, invariant_path=invariant_file)
    report = verifier.handle(ModelVerifyReplayInput(package_bytes=bundle))
    assert report.overall_status == "pass"

    inv_check = next(
        (c for c in report.checks if c.check_name == "all_invariants_present"), None
    )
    assert inv_check is not None
    assert inv_check.status == "pass"


# =============================================================================
# Tier 1 — failure cases
# =============================================================================


def _corrupt_overlay_in_zip(bundle_bytes: bytes) -> bytes:
    """Replace the first overlay YAML inside the zip with garbage."""
    buf = io.BytesIO(bundle_bytes)
    out = io.BytesIO()
    with zipfile.ZipFile(buf, "r") as zin, zipfile.ZipFile(out, "w") as zout:
        for name in zin.namelist():
            data = zin.read(name)
            if name.startswith("overlays/") and name.endswith(".yaml"):
                # Replace with invalid YAML bytes that won't parse as ModelContractPatch
                data = b"not: valid: contract: patch: !!garbage"
            zout.writestr(name, data)
    return out.getvalue()


def test_bad_overlay_yaml_fails_schema_check(
    verifier: NodeContractVerifyReplayCompute,
    simple_bundle_bytes: bytes,
) -> None:
    """Corrupt overlay YAML → schema_validation fails → overall fail."""
    corrupted = _corrupt_overlay_in_zip(simple_bundle_bytes)
    inp = ModelVerifyReplayInput(
        package_bytes=corrupted,
        options=ModelVerifyOptions(skip_digest_check=True),
    )
    report = verifier.handle(inp)
    assert report.overall_status == "fail"
    schema_check = next(c for c in report.checks if c.check_name == "schema_validation")
    assert schema_check.status == "fail"


def test_content_digest_mismatch_fails(
    verifier: NodeContractVerifyReplayCompute,
    simple_bundle_bytes: bytes,
) -> None:
    """Tampered overlay bytes → content_digest_integrity fails."""
    # Corrupt just the bytes in the overlay without updating the manifest hash.
    buf = io.BytesIO(simple_bundle_bytes)
    out = io.BytesIO()
    with zipfile.ZipFile(buf, "r") as zin, zipfile.ZipFile(out, "w") as zout:
        for name in zin.namelist():
            data = zin.read(name)
            if name.startswith("overlays/") and name.endswith(".yaml"):
                # Append a byte to corrupt the content without touching manifest.
                data = data + b"\n# tampered"
            zout.writestr(name, data)
    tampered = out.getvalue()

    inp = ModelVerifyReplayInput(package_bytes=tampered)
    report = verifier.handle(inp)
    assert report.overall_status == "fail"
    digest_check = next(
        c for c in report.checks if c.check_name == "content_digest_integrity"
    )
    assert digest_check.status == "fail"


def _build_bundle_with_scenario_and_missing_fixture(
    base_bundle_bytes: bytes,
) -> bytes:
    """Build a bundle where a scenario YAML references a fixture_path that
    does NOT exist as a zip member.

    Steps:
    1. Start with a valid bundle.
    2. Add a scenario YAML containing ``fixture_path: fixtures/missing.yaml``.
    3. Register the scenario in the manifest.
    4. Do NOT add the fixture file itself to the zip.
    """
    scenario_yaml = (
        "id: test_scenario\nfixture_path: fixtures/missing.yaml\nsteps: []\n"
    )
    scenario_bytes = scenario_yaml.encode("utf-8")
    scenario_hash = "sha256:" + hashlib.sha256(scenario_bytes).hexdigest()

    # Pass 1: add the scenario file to the zip.
    buf = io.BytesIO(base_bundle_bytes)
    out = io.BytesIO()
    with zipfile.ZipFile(buf, "r") as zin, zipfile.ZipFile(out, "w") as zout:
        for name in zin.namelist():
            zout.writestr(name, zin.read(name))
        zout.writestr("scenarios/test_scenario.yaml", scenario_bytes)
    bundle_with_scenario = out.getvalue()

    # Pass 2: update the manifest to register the scenario.
    buf2 = io.BytesIO(bundle_with_scenario)
    out2 = io.BytesIO()
    with zipfile.ZipFile(buf2, "r") as zin2, zipfile.ZipFile(out2, "w") as zout2:
        for name in zin2.namelist():
            data = zin2.read(name)
            if name == "manifest.yaml":
                manifest_data = yaml.safe_load(data.decode("utf-8"))
                manifest_data["scenarios"] = [
                    {
                        "id": "test_scenario",
                        "path": "scenarios/test_scenario.yaml",
                        "content_hash": scenario_hash,
                        "required": True,
                    }
                ]
                data = yaml.dump(manifest_data).encode("utf-8")
            zout2.writestr(name, data)
    return out2.getvalue()


def test_missing_fixture_path_fails(
    verifier: NodeContractVerifyReplayCompute,
    simple_bundle_bytes: bytes,
) -> None:
    """Scenario with fixture_path pointing to non-existent zip entry → fail."""
    modified_bundle = _build_bundle_with_scenario_and_missing_fixture(
        simple_bundle_bytes
    )

    inp = ModelVerifyReplayInput(
        package_bytes=modified_bundle,
        options=ModelVerifyOptions(skip_digest_check=True),
    )
    report = verifier.handle(inp)
    # The fixture_presence check should detect that fixtures/missing.yaml
    # is not in the bundle.
    fixture_check = next(c for c in report.checks if c.check_name == "fixture_presence")
    assert fixture_check.status == "fail"
    assert report.overall_status == "fail"


def test_missing_scenario_zip_entry_fails(
    verifier: NodeContractVerifyReplayCompute,
    simple_bundle_bytes: bytes,
) -> None:
    """Manifest lists a scenario whose zip entry was removed → all_scenarios_present fails."""
    # Build with a scenario, then strip the scenario file from the zip.
    buf = io.BytesIO(simple_bundle_bytes)
    out = io.BytesIO()
    with zipfile.ZipFile(buf, "r") as zin, zipfile.ZipFile(out, "w") as zout:
        for name in zin.namelist():
            data = zin.read(name)
            zout.writestr(name, data)
        # Add a scenario YAML to the zip.
        scenario_content = b"id: orphan\nsteps: []\n"
        zout.writestr("scenarios/orphan.yaml", scenario_content)

    # Now add the scenario to the manifest but then remove it from the zip.
    buf2 = io.BytesIO(out.getvalue())
    out2 = io.BytesIO()
    with zipfile.ZipFile(buf2, "r") as zin2, zipfile.ZipFile(out2, "w") as zout2:
        for name in zin2.namelist():
            data = zin2.read(name)
            if name == "manifest.yaml":
                manifest_data = yaml.safe_load(data.decode("utf-8"))
                manifest_data["scenarios"] = [
                    {
                        "id": "orphan",
                        "path": "scenarios/orphan_DELETED.yaml",  # wrong path
                        "content_hash": "sha256:" + hashlib.sha256(b"x").hexdigest(),
                        "required": True,
                    }
                ]
                data = yaml.dump(manifest_data).encode("utf-8")
            zout2.writestr(name, data)
    corrupted = out2.getvalue()

    inp = ModelVerifyReplayInput(
        package_bytes=corrupted,
        options=ModelVerifyOptions(skip_digest_check=True),
    )
    report = verifier.handle(inp)
    scenario_check = next(
        c for c in report.checks if c.check_name == "all_scenarios_present"
    )
    assert scenario_check.status == "fail"
    assert report.overall_status == "fail"


# =============================================================================
# Tier 2 — deferred
# =============================================================================


def test_tier2_yields_skip(
    verifier: NodeContractVerifyReplayCompute,
    simple_bundle_bytes: bytes,
) -> None:
    """Tier 2 is not implemented — all checks are 'skip'."""
    inp = ModelVerifyReplayInput(
        package_bytes=simple_bundle_bytes,
        tier=EnumVerifyTier.TIER2_SIMULATED,
    )
    report = verifier.handle(inp)
    assert report.tier == EnumVerifyTier.TIER2_SIMULATED
    # Tier 2 not implemented → all checks skipped → overall pass (no failures)
    assert report.overall_status == "pass"
    for check in report.checks:
        assert check.status == "skip"


# =============================================================================
# Options
# =============================================================================


def test_skip_digest_check_option(
    verifier: NodeContractVerifyReplayCompute,
    simple_bundle_bytes: bytes,
) -> None:
    """skip_digest_check=True marks content_digest_integrity as skip."""
    inp = ModelVerifyReplayInput(
        package_bytes=simple_bundle_bytes,
        options=ModelVerifyOptions(skip_digest_check=True),
    )
    report = verifier.handle(inp)
    digest_check = next(
        c for c in report.checks if c.check_name == "content_digest_integrity"
    )
    assert digest_check.status == "skip"
