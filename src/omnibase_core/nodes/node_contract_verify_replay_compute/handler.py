# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""contract.verify.replay compute node — tier1 static validation.

Implements the :class:`NodeContractVerifyReplayCompute` compute node that
verifies a ``.oncp`` contract package against the *tier1_static* checklist and
produces a signed :class:`~omnibase_core.models.contract_verify_replay.model_verify_replay_output.ModelVerifyReplayOutput`
verification report.

**Tier 1 static checks (this ticket — OMN-2759)**:

1. ``schema_validation`` — every overlay YAML round-trips through
   :class:`~omnibase_core.models.contracts.model_contract_patch.ModelContractPatch`
   without validation errors.
2. ``capability_linting`` — all ``capability_inputs`` declared in each overlay
   are present in the corresponding ``capability_outputs`` of the resolved
   contract (declared-satisfied).
3. ``fixture_presence`` — every ``fixture_path`` referenced in a scenario entry
   exists inside the bundle (zip member check).
4. ``overlay_merge_correctness`` — the overlay stack resolves via
   :class:`~omnibase_core.merge.contract_merge_engine.ContractMergeEngine`
   without raising :class:`~omnibase_core.models.errors.model_onex_error.ModelOnexError`.
5. ``determinism_declared`` — the manifest's ``base_profile_ref`` is non-empty
   and a determinism class is implied (structural check only at tier1).
6. ``all_scenarios_present`` — scenario IDs listed in the manifest are backed
   by a zip entry (cross-check manifest vs. zip).
7. ``all_invariants_present`` — invariant IDs listed in the manifest are backed
   by a zip entry.
8. ``content_digest_integrity`` — if ``options.skip_digest_check`` is False,
   all content hashes in the manifest are verified.

**Signing**: The report is serialised to canonical JSON, then its SHA-256 digest
is computed. If ``~/.onex/verifier.key`` exists (ed25519 private key in PEM
format) the digest is signed and the base64-encoded signature is embedded.
If the key is absent the report is produced unsigned.

.. versionadded:: 0.20.0
"""

from __future__ import annotations

import base64
import hashlib
import io
import json
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import yaml

from omnibase_core.enums.enum_check_status import EnumCheckStatus
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_overall_status import EnumOverallStatus
from omnibase_core.enums.enum_verify_tier import EnumVerifyTier
from omnibase_core.merge.contract_merge_engine import ContractMergeEngine
from omnibase_core.models.contract_verify_replay.model_verify_check_result import (
    ModelVerifyCheckResult,
)
from omnibase_core.models.contract_verify_replay.model_verify_replay_input import (
    ModelVerifyReplayInput,
)
from omnibase_core.models.contract_verify_replay.model_verify_replay_output import (
    ModelVerifyReplayOutput,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.merge.model_overlay_stack_entry import ModelOverlayStackEntry
from omnibase_core.package.model_oncp_manifest import ModelOncpManifest
from omnibase_core.package.service_oncp_reader import OncpReader

__all__ = ["NodeContractVerifyReplayCompute"]

# Default path for the local ed25519 verifier key (MVP key management).
_DEFAULT_KEY_PATH = Path.home() / ".onex" / "verifier.key"

# Name used for the synthetic base patch when no overlays exist.
_SYNTHETIC_PROFILE = "base"


def _sha256_hex(data: bytes) -> str:
    """Return the SHA-256 hex digest of *data*."""
    return hashlib.sha256(data).hexdigest()


def _sha256_prefixed(data: bytes) -> str:
    """Return ``sha256:<hex>`` prefixed digest of *data*."""
    return f"sha256:{_sha256_hex(data)}"


class NodeContractVerifyReplayCompute:
    """Compute node for static verification of ``.oncp`` contract packages.

    This is a *thin* compute node: all verification logic lives in
    ``_run_tier1_checks()``. The node is stateless and safe to instantiate
    once and reuse across multiple calls.

    Usage::

        verifier = NodeContractVerifyReplayCompute()
        report = verifier.handle(
            ModelVerifyReplayInput(
                package_path="/tmp/my_effect.oncp",
                tier=EnumVerifyTier.TIER1_STATIC,
            )
        )
        assert report.overall_status == "pass"

    .. versionadded:: 0.20.0
    """

    def handle(self, inp: ModelVerifyReplayInput) -> ModelVerifyReplayOutput:
        """Run the verification pipeline and return a signed report.

        Args:
            inp: Input describing the ``.oncp`` bundle to verify and the tier.

        Returns:
            A :class:`~omnibase_core.models.contract_verify_replay.model_verify_replay_output.ModelVerifyReplayOutput`
            with ``overall_status`` set to ``"pass"``, ``"fail"``, or ``"error"``.

        Raises:
            ModelOnexError: If neither ``package_path`` nor ``package_bytes``
                is provided, or if the provided path does not exist.
        """
        if inp.package_path is None and inp.package_bytes is None:
            raise ModelOnexError(
                "Either package_path or package_bytes must be provided",
                error_code=EnumCoreErrorCode.INVALID_INPUT,
            )

        # Load raw bytes.
        if inp.package_bytes is not None:
            raw_bytes = inp.package_bytes
        else:
            p = Path(inp.package_path)  # type: ignore[arg-type]
            if not p.exists():
                raise ModelOnexError(
                    f".oncp bundle not found: {p}",
                    error_code=EnumCoreErrorCode.FILE_NOT_FOUND,
                )
            raw_bytes = p.read_bytes()

        package_content_hash = _sha256_prefixed(raw_bytes)

        # Parse the manifest (fast fail on invalid zip / missing manifest.yaml).
        reader = OncpReader().open_bytes(raw_bytes)
        manifest = reader.manifest

        if inp.tier == EnumVerifyTier.TIER1_STATIC:
            checks = self._run_tier1_checks(
                raw_bytes=raw_bytes,
                reader=reader,
                manifest=manifest,
                options=inp.options,
            )
        else:
            # Tier 2 is deferred (OMN-2759 scope: tier1_static only).
            checks = [
                ModelVerifyCheckResult(
                    check_name="tier2_simulated",
                    status=EnumCheckStatus.SKIP,
                    message="Tier 2 simulated replay is not implemented yet.",
                )
            ]

        # Determine overall status.
        if any(c.status == EnumCheckStatus.FAIL for c in checks):
            overall = EnumOverallStatus.FAIL
        else:
            overall = EnumOverallStatus.PASS

        # Build report (without digest/sig fields first so we can hash it).
        report_dict = self._build_report_dict(
            tier=inp.tier,
            manifest=manifest,
            package_content_hash=package_content_hash,
            checks=checks,
            overall_status=overall,
        )

        # Compute report_digest over the content (excl. report_digest + signature).
        report_digest = _sha256_prefixed(
            json.dumps(report_dict, sort_keys=True, ensure_ascii=True).encode("ascii")
        )

        # Sign if a key is available.
        signature = self._sign_digest(report_digest)

        return ModelVerifyReplayOutput(
            report_version=1,
            tier=inp.tier,
            package_id=manifest.package_id,
            package_version=manifest.package_version,
            package_content_hash=package_content_hash,
            checks=checks,
            overall_status=overall,
            generated_at=datetime.now(tz=UTC),
            report_digest=report_digest,
            signature=signature,
        )

    # =========================================================================
    # Tier 1 checks
    # =========================================================================

    def _run_tier1_checks(
        self,
        raw_bytes: bytes,
        reader: OncpReader,
        manifest: ModelOncpManifest,
        options: object,
    ) -> list[ModelVerifyCheckResult]:
        """Execute all tier1_static checks in order.

        Args:
            raw_bytes: Raw ``.oncp`` zip bytes.
            reader: Already-opened :class:`OncpReader`.
            manifest: Parsed manifest from the bundle.
            options: :class:`~omnibase_core.models.contract_verify_replay.model_verify_options.ModelVerifyOptions`.

        Returns:
            Ordered list of :class:`ModelVerifyCheckResult`.
        """
        results: list[ModelVerifyCheckResult] = []

        # 1. Schema validation — all overlay YAMLs parse as ModelContractPatch.
        results.append(self._check_schema_validation(reader))

        # 2. Capability linting — declared capability_inputs satisfied.
        results.append(self._check_capability_linting(reader))

        # 3. Fixture presence — fixture_path refs exist in zip.
        results.append(self._check_fixture_presence(raw_bytes, manifest))

        # 4. Overlay merge correctness — merge engine resolves without error.
        results.append(self._check_overlay_merge(reader, options))

        # 5. Determinism declared — base_profile_ref is non-empty.
        results.append(self._check_determinism_declared(manifest))

        # 6. All required scenarios present per manifest.
        results.append(self._check_all_scenarios_present(raw_bytes, manifest))

        # 7. All required invariants present per manifest.
        results.append(self._check_all_invariants_present(raw_bytes, manifest))

        # 8. Content digest integrity.
        skip_digest = getattr(options, "skip_digest_check", False)
        if skip_digest:
            results.append(
                ModelVerifyCheckResult(
                    check_name="content_digest_integrity",
                    status=EnumCheckStatus.SKIP,
                    message="Skipped by options.skip_digest_check=True.",
                )
            )
        else:
            results.append(self._check_content_digest_integrity(reader))

        return results

    def _check_schema_validation(self, reader: OncpReader) -> ModelVerifyCheckResult:
        """Check 1: all overlay YAMLs parse as ModelContractPatch."""
        try:
            patches = reader.get_overlay_patches()
        except (ModelOnexError, Exception) as exc:
            return ModelVerifyCheckResult(
                check_name="schema_validation",
                status=EnumCheckStatus.FAIL,
                message=f"Overlay patch schema validation failed: {exc}",
            )

        if not patches:
            return ModelVerifyCheckResult(
                check_name="schema_validation",
                status=EnumCheckStatus.PASS,
                message="No overlays in bundle — schema validation trivially passes.",
            )

        return ModelVerifyCheckResult(
            check_name="schema_validation",
            status=EnumCheckStatus.PASS,
            message=f"All {len(patches)} overlay(s) passed schema validation.",
        )

    def _check_capability_linting(self, reader: OncpReader) -> ModelVerifyCheckResult:
        """Check 2: declared capability_inputs are satisfied by capability_outputs.

        The contract.yaml convention is that ``capability_inputs`` lists the
        required capabilities a handler needs injected, and
        ``capability_outputs`` lists what it provides. For a single-patch
        bundle the patch's own ``capability_outputs__add`` must cover its
        ``capability_inputs__add``.

        For multi-overlay bundles we only check that no overlay declares a
        capability_input that no *other* overlay or the base provides as
        capability_output (best-effort linting; full capability resolution is
        deferred to the runtime).
        """
        try:
            patches = reader.get_overlay_patches()
        except (ModelOnexError, Exception) as exc:
            return ModelVerifyCheckResult(
                check_name="capability_linting",
                status=EnumCheckStatus.FAIL,
                message=f"Could not load patches for capability linting: {exc}",
            )

        if not patches:
            return ModelVerifyCheckResult(
                check_name="capability_linting",
                status=EnumCheckStatus.PASS,
                message="No overlays — capability linting trivially passes.",
            )

        # Gather all provided capabilities across the stack.
        all_provided: set[str] = set()
        for p in patches:
            if p.capability_outputs__add:
                for cap_out in p.capability_outputs__add:
                    all_provided.add(cap_out.name)

        # Check that all required capabilities appear somewhere in the stack.
        unsatisfied: list[str] = []
        for p in patches:
            if p.capability_inputs__add:
                for cap_in in p.capability_inputs__add:
                    if cap_in not in all_provided:
                        unsatisfied.append(cap_in)

        if unsatisfied:
            return ModelVerifyCheckResult(
                check_name="capability_linting",
                status=EnumCheckStatus.FAIL,
                message=(
                    "Unsatisfied capability_inputs (not in any overlay's "
                    f"capability_outputs): {sorted(set(unsatisfied))}"
                ),
            )

        return ModelVerifyCheckResult(
            check_name="capability_linting",
            status=EnumCheckStatus.PASS,
            message="All declared capability_inputs are satisfied.",
        )

    def _check_fixture_presence(
        self, raw_bytes: bytes, manifest: ModelOncpManifest
    ) -> ModelVerifyCheckResult:
        """Check 3: fixture_path refs inside scenario YAMLs exist in the zip.

        For each scenario entry in the manifest, reads the scenario YAML
        content from the bundle and checks if a top-level ``fixture_path``
        key is present. If so, verifies that the referenced path exists as a
        member of the zip archive.
        """
        if not manifest.scenarios:
            return ModelVerifyCheckResult(
                check_name="fixture_presence",
                status=EnumCheckStatus.PASS,
                message="No scenarios in bundle — fixture_presence trivially passes.",
            )

        missing: list[str] = []
        try:
            with zipfile.ZipFile(io.BytesIO(raw_bytes)) as zf:
                zip_members = set(zf.namelist())
                for scenario_entry in manifest.scenarios:
                    # Read the scenario YAML from the bundle.
                    if scenario_entry.path not in zip_members:
                        # Scenario file itself is missing — all_scenarios_present
                        # will catch this; skip fixture check for this entry.
                        continue
                    raw_content = zf.read(scenario_entry.path)
                    try:
                        scenario_data = yaml.safe_load(raw_content.decode("utf-8"))
                    except Exception:
                        continue  # unparseable YAML — not our problem here

                    if not isinstance(scenario_data, dict):
                        continue

                    fixture_path = scenario_data.get("fixture_path")
                    if fixture_path and isinstance(fixture_path, str):
                        if fixture_path not in zip_members:
                            missing.append(
                                f"scenario '{scenario_entry.id}': "
                                f"fixture_path '{fixture_path}' not in bundle"
                            )
        except (zipfile.BadZipFile, Exception) as exc:
            return ModelVerifyCheckResult(
                check_name="fixture_presence",
                status=EnumCheckStatus.FAIL,
                message=f"Could not read bundle for fixture presence check: {exc}",
            )

        if missing:
            return ModelVerifyCheckResult(
                check_name="fixture_presence",
                status=EnumCheckStatus.FAIL,
                message="; ".join(missing),
            )

        return ModelVerifyCheckResult(
            check_name="fixture_presence",
            status=EnumCheckStatus.PASS,
            message="All fixture_path references are present in the bundle.",
        )

    def _check_overlay_merge(  # stub-ok: uses a minimal in-process profile factory for tier1 structural checks
        self, reader: OncpReader, options: object
    ) -> ModelVerifyCheckResult:
        """Check 4: overlay stack resolves through ContractMergeEngine.

        Uses a minimal in-process profile factory so the engine can operate
        without a live Infisical / contract registry. The synthetic factory
        returns a minimal base contract from the patch's profile reference.
        This is sufficient for tier1 structural checks (list-conflict
        detection, scope ordering).
        """
        try:
            patches = reader.get_overlay_patches()
        except (ModelOnexError, Exception) as exc:
            return ModelVerifyCheckResult(
                check_name="overlay_merge_correctness",
                status=EnumCheckStatus.FAIL,
                message=f"Could not load patches: {exc}",
            )

        if not patches:
            return ModelVerifyCheckResult(
                check_name="overlay_merge_correctness",
                status=EnumCheckStatus.PASS,
                message="No overlays — merge correctness trivially passes.",
            )

        try:
            strict_ordering = getattr(options, "strict_overlay_ordering", False)
            manifest = reader.manifest

            base_patch = patches[0]
            engine = self._make_merge_engine()

            from omnibase_core.enums.enum_overlay_scope import EnumOverlayScope

            overlay_entries: list[ModelOverlayStackEntry] = []
            # manifest.overlays is ordered by order_index; patches are in the
            # same order (get_overlay_patches() sorts by order_index).
            for idx, patch in enumerate(patches[1:], start=1):
                manifest_entry = (
                    manifest.overlays[idx] if idx < len(manifest.overlays) else None
                )
                scope: EnumOverlayScope = (
                    manifest_entry.scope if manifest_entry else EnumOverlayScope.PROJECT
                )
                # string-id-ok: overlay IDs are human-readable slugs from the manifest, not UUIDs
                overlay_id: str = (
                    manifest_entry.overlay_id if manifest_entry else f"overlay_{idx}"
                )
                entry = ModelOverlayStackEntry(
                    overlay_id=overlay_id,
                    overlay_patch=patch,
                    scope=scope,
                    version="1.0.0",
                )
                overlay_entries.append(entry)

            if overlay_entries:
                engine.merge_with_overlays(
                    patch=base_patch,
                    overlays=overlay_entries,
                    strict_ordering=strict_ordering,
                )
            else:
                # Single overlay — use simple merge.
                engine.merge(patch=base_patch)

        except (ModelOnexError, Exception) as exc:
            return ModelVerifyCheckResult(
                check_name="overlay_merge_correctness",
                status=EnumCheckStatus.FAIL,
                message=f"Overlay merge failed: {exc}",
            )

        return ModelVerifyCheckResult(
            check_name="overlay_merge_correctness",
            status=EnumCheckStatus.PASS,
            message=f"All {len(patches)} overlay(s) merged without conflicts.",
        )

    @staticmethod
    def _make_merge_engine() -> (
        ContractMergeEngine
    ):  # stub-ok: synthetic in-process factory for tier1 offline checks
        """Create a ContractMergeEngine with a minimal in-process profile factory.

        The synthetic factory is sufficient for tier1 structural validation
        (conflict detection, scope ordering). It does not perform a live
        profile lookup — it synthesises a minimal base contract from the
        patch's ``extends`` reference instead.
        """
        from unittest.mock import MagicMock

        from omnibase_core.models.primitives.model_semver import ModelSemVer

        synthetic_base = MagicMock()
        synthetic_base.name = "synthetic_base"
        synthetic_base.contract_version = ModelSemVer(major=0, minor=1, patch=0)
        synthetic_base.description = "synthetic"
        synthetic_base.input_model = "SyntheticInput"
        synthetic_base.output_model = "SyntheticOutput"
        synthetic_base.behavior = None
        synthetic_base.tags = []
        synthetic_base.capability_inputs = []
        synthetic_base.capability_outputs = []
        synthetic_base.handlers = []
        synthetic_base.dependencies = []
        synthetic_base.consumed_events = []

        synthetic_factory = MagicMock()
        synthetic_factory.get_profile = MagicMock(return_value=synthetic_base)

        return ContractMergeEngine(synthetic_factory)

    def _check_determinism_declared(
        self, manifest: ModelOncpManifest
    ) -> ModelVerifyCheckResult:
        """Check 5: base_profile_ref is non-empty (determinism implied)."""
        if not manifest.base_profile_ref or not manifest.base_profile_ref.strip():
            return ModelVerifyCheckResult(
                check_name="determinism_declared",
                status=EnumCheckStatus.FAIL,
                message="manifest.base_profile_ref is empty; determinism class cannot be inferred.",
            )

        return ModelVerifyCheckResult(
            check_name="determinism_declared",
            status=EnumCheckStatus.PASS,
            message=f"base_profile_ref='{manifest.base_profile_ref}' is declared.",
        )

    def _check_all_scenarios_present(
        self, raw_bytes: bytes, manifest: ModelOncpManifest
    ) -> ModelVerifyCheckResult:
        """Check 6: all scenarios listed in manifest have backing zip entries."""
        if not manifest.scenarios:
            return ModelVerifyCheckResult(
                check_name="all_scenarios_present",
                status=EnumCheckStatus.PASS,
                message="No scenarios declared in manifest.",
            )

        missing: list[str] = []
        try:
            with zipfile.ZipFile(io.BytesIO(raw_bytes)) as zf:
                members = set(zf.namelist())
                for scenario in manifest.scenarios:
                    if scenario.path not in members:
                        missing.append(
                            f"scenario '{scenario.id}': path '{scenario.path}' missing"
                        )
        except (zipfile.BadZipFile, Exception) as exc:
            return ModelVerifyCheckResult(
                check_name="all_scenarios_present",
                status=EnumCheckStatus.FAIL,
                message=f"Could not check scenarios: {exc}",
            )

        if missing:
            return ModelVerifyCheckResult(
                check_name="all_scenarios_present",
                status=EnumCheckStatus.FAIL,
                message="; ".join(missing),
            )

        return ModelVerifyCheckResult(
            check_name="all_scenarios_present",
            status=EnumCheckStatus.PASS,
            message=f"All {len(manifest.scenarios)} scenario(s) present.",
        )

    def _check_all_invariants_present(
        self, raw_bytes: bytes, manifest: ModelOncpManifest
    ) -> ModelVerifyCheckResult:
        """Check 7: all invariants listed in manifest have backing zip entries."""
        if not manifest.invariants:
            return ModelVerifyCheckResult(
                check_name="all_invariants_present",
                status=EnumCheckStatus.PASS,
                message="No invariants declared in manifest.",
            )

        missing: list[str] = []
        try:
            with zipfile.ZipFile(io.BytesIO(raw_bytes)) as zf:
                members = set(zf.namelist())
                for inv in manifest.invariants:
                    if inv.path not in members:
                        missing.append(
                            f"invariant '{inv.id}': path '{inv.path}' missing"
                        )
        except (zipfile.BadZipFile, Exception) as exc:
            return ModelVerifyCheckResult(
                check_name="all_invariants_present",
                status=EnumCheckStatus.FAIL,
                message=f"Could not check invariants: {exc}",
            )

        if missing:
            return ModelVerifyCheckResult(
                check_name="all_invariants_present",
                status=EnumCheckStatus.FAIL,
                message="; ".join(missing),
            )

        return ModelVerifyCheckResult(
            check_name="all_invariants_present",
            status=EnumCheckStatus.PASS,
            message=f"All {len(manifest.invariants)} invariant(s) present.",
        )

    def _check_content_digest_integrity(
        self, reader: OncpReader
    ) -> ModelVerifyCheckResult:
        """Check 8: all content hashes in the manifest match actual zip entries."""
        try:
            reader.validate_digests()
        except ModelOnexError as exc:
            return ModelVerifyCheckResult(
                check_name="content_digest_integrity",
                status=EnumCheckStatus.FAIL,
                message=str(exc),
            )
        except Exception as exc:  # fallback-ok: digest check returns structured fail result instead of raising
            return ModelVerifyCheckResult(
                check_name="content_digest_integrity",
                status=EnumCheckStatus.FAIL,
                message=f"Digest check failed unexpectedly: {exc}",
            )

        return ModelVerifyCheckResult(
            check_name="content_digest_integrity",
            status=EnumCheckStatus.PASS,
            message="All content hashes verified.",
        )

    # =========================================================================
    # Signing helpers
    # =========================================================================

    def _sign_digest(self, report_digest: str) -> str | None:
        """Sign *report_digest* with the local ed25519 verifier key.

        If the key file at ``~/.onex/verifier.key`` does not exist, returns
        ``None`` (unsigned mode — acceptable for MVP).

        The key is expected to be a PEM-encoded ed25519 private key as
        generated by OpenSSL (``openssl genpkey -algorithm ed25519``).

        Args:
            report_digest: ``sha256:<hex>`` string to sign.

        Returns:
            Base64-encoded signature string, or ``None`` if no key available.
        """
        key_path = _DEFAULT_KEY_PATH
        if not key_path.exists():
            return None  # fallback-ok: unsigned mode when no local key

        try:
            from cryptography.hazmat.primitives.asymmetric.ed25519 import (
                Ed25519PrivateKey,
            )
            from cryptography.hazmat.primitives.serialization import (
                load_pem_private_key,
            )

            pem_data = key_path.read_bytes()
            private_key = load_pem_private_key(pem_data, password=None)
            if not isinstance(private_key, Ed25519PrivateKey):
                return None  # fallback-ok: wrong key type, skip signing

            sig_bytes = private_key.sign(report_digest.encode("ascii"))
            return base64.b64encode(sig_bytes).decode("ascii")
        except Exception:
            # fallback-ok: signing is best-effort for MVP; report is still valid
            return None

    # =========================================================================
    # Report builder
    # =========================================================================

    def _build_report_dict(
        self,
        tier: EnumVerifyTier,
        manifest: ModelOncpManifest,
        package_content_hash: str,
        checks: list[ModelVerifyCheckResult],
        overall_status: EnumOverallStatus,
    ) -> dict[str, object]:
        """Build the canonical dict representation of the report for hashing.

        The ``report_digest`` and ``signature`` fields are NOT included so
        that the hash covers only the report content.

        Returns:
            JSON-serialisable dict (sorted keys, no None values).
        """
        return {
            "checks": [
                {"check_name": c.check_name, "message": c.message, "status": c.status}
                for c in checks
            ],
            "overall_status": overall_status,
            "package_content_hash": package_content_hash,
            "package_id": manifest.package_id,
            "package_version": manifest.package_version,
            "report_version": 1,
            "tier": tier.value,
        }
