# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Probe-target assertion (OMN-17312).

The falsifier suite for epic OMN-17306's third leg. The headline case replays
the real 2026-08-31T08:10:54Z probe (correlation
``b9cd305c-8f31-497a-b404-b75b45b98341``): published over the ``.201`` broker,
read as a dev-lane result, executed entirely inside the operator's local venv
on pre-fix ``omnimarket``. It printed a confident answer and proved nothing.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from omnibase_core.enums.enum_execution_locus_kind import EnumExecutionLocusKind
from omnibase_core.enums.enum_package_source_kind import EnumPackageSourceKind
from omnibase_core.enums.enum_probe_target_disagreement import (
    EnumProbeTargetDisagreement,
)
from omnibase_core.models.runtime.model_declared_target_identity import (
    ModelDeclaredTargetIdentity,
)
from omnibase_core.models.runtime.model_package_identity import ModelPackageIdentity
from omnibase_core.models.runtime.model_runtime_identity import ModelRuntimeIdentity
from omnibase_core.validation.validator_probe_target import (
    ProbeTargetMismatchError,
    assert_probe_target,
)

# The pre-fix omnimarket the local venv was pinned to (OMN-17295).
_LOCAL_MARKET_COMMIT = "66b7131a3508" + "0" * 28  # pragma: allowlist secret
# origin/dev's tip, which the dev lane was correctly vendored at.
_LANE_MARKET_COMMIT = "2f123b4c01ea" + "0" * 28  # pragma: allowlist secret


def _local_venv_stamp(
    *, market_commit: str | None = _LOCAL_MARKET_COMMIT
) -> ModelRuntimeIdentity:
    return ModelRuntimeIdentity(
        host="operator-macbook",
        locus_kind=EnumExecutionLocusKind.VENV,
        # The laptop-shaped venv prefix IS the datum under test: this fixture
        # reproduces the OMN-17295 stamp the assertion must reject.
        execution_locus="/Users/example/omni_home/omnibase_infra/.venv",  # local-path-ok
        interpreter="/Users/example/omni_home/omnibase_infra/.venv/bin/python3.12",  # local-path-ok
        packages={
            "omnimarket": ModelPackageIdentity(
                name="omnimarket",
                version="0.4.11",
                commit=market_commit,
                source=(
                    EnumPackageSourceKind.VCS
                    if market_commit
                    else EnumPackageSourceKind.REGISTRY
                ),
            ),
        },
        stamped_at=datetime(2026, 8, 31, 8, 10, 54, tzinfo=UTC),
    )


def _lane_stamp() -> ModelRuntimeIdentity:
    return ModelRuntimeIdentity(
        host="omninode-runtime",
        locus_kind=EnumExecutionLocusKind.CONTAINER,
        execution_locus="9f2c1b0e4a55",  # pragma: allowlist secret
        interpreter="/app/.venv/bin/python3.12",
        packages={
            "omnimarket": ModelPackageIdentity(
                name="omnimarket",
                version="0.4.11",
                commit=_LANE_MARKET_COMMIT,
                source=EnumPackageSourceKind.VCS,
            ),
        },
        stamped_at=datetime(2026, 8, 31, 8, 10, 54, tzinfo=UTC),
    )


def _lane_declaration(**overrides: object) -> ModelDeclaredTargetIdentity:
    base: dict[str, object] = {
        "target_name": "dev lane (.201, omnibase-infra)",
        "declared_by": "docker exec omninode-runtime cat /app/build-provenance.json",
        "host": "omninode-runtime",
        "locus_kind": EnumExecutionLocusKind.CONTAINER,
        "execution_locus": "9f2c1b0e4a55",  # pragma: allowlist secret
        "packages": {"omnimarket": _LANE_MARKET_COMMIT},
    }
    base.update(overrides)
    return ModelDeclaredTargetIdentity(**base)  # type: ignore[arg-type]


@pytest.mark.unit
class TestRefusals:
    def test_local_venv_stamp_against_lane_declaration_is_refused(self) -> None:
        """THE case: a laptop-local run claiming to prove the .201 dev lane."""
        with pytest.raises(ProbeTargetMismatchError) as excinfo:
            assert_probe_target(
                stamped=_local_venv_stamp(), declared=_lane_declaration()
            )
        assert excinfo.value.kind is EnumProbeTargetDisagreement.MISMATCH
        assert "host" in excinfo.value.detail

    def test_stale_package_commit_is_refused(self) -> None:
        """Right host, right container, wrong code — the OMN-17291 shape."""
        stamped = ModelRuntimeIdentity(
            host="omninode-runtime",
            locus_kind=EnumExecutionLocusKind.CONTAINER,
            execution_locus="9f2c1b0e4a55",  # pragma: allowlist secret
            interpreter="/app/.venv/bin/python3.12",
            packages={
                "omnimarket": ModelPackageIdentity(
                    name="omnimarket",
                    version="0.4.11",
                    commit="05e3882f9e2a" + "0" * 28,  # pragma: allowlist secret
                    source=EnumPackageSourceKind.VCS,
                ),
            },
            stamped_at=datetime(2026, 8, 31, 5, 38, 22, tzinfo=UTC),
        )
        with pytest.raises(ProbeTargetMismatchError) as excinfo:
            assert_probe_target(stamped=stamped, declared=_lane_declaration())
        assert excinfo.value.kind is EnumProbeTargetDisagreement.MISMATCH
        assert "omnimarket" in excinfo.value.detail

    def test_unresolvable_commit_is_refused_as_unknown(self) -> None:
        """'I cannot tell' fails on the same terms as 'it ran elsewhere'."""
        stamped = ModelRuntimeIdentity(
            host="omninode-runtime",
            locus_kind=EnumExecutionLocusKind.CONTAINER,
            execution_locus="9f2c1b0e4a55",  # pragma: allowlist secret
            interpreter="/app/.venv/bin/python3.12",
            packages={
                "omnimarket": ModelPackageIdentity(
                    name="omnimarket",
                    version="0.4.11",
                    commit=None,
                    source=EnumPackageSourceKind.REGISTRY,
                ),
            },
            stamped_at=datetime(2026, 8, 31, tzinfo=UTC),
        )
        with pytest.raises(ProbeTargetMismatchError) as excinfo:
            assert_probe_target(stamped=stamped, declared=_lane_declaration())
        assert excinfo.value.kind is EnumProbeTargetDisagreement.UNKNOWN
        assert "not evidence of content" in excinfo.value.detail

    def test_package_absent_from_stamp_is_unknown_not_pass(self) -> None:
        stamped = ModelRuntimeIdentity(
            host="omninode-runtime",
            locus_kind=EnumExecutionLocusKind.CONTAINER,
            execution_locus="9f2c1b0e4a55",  # pragma: allowlist secret
            interpreter="/app/.venv/bin/python3.12",
            packages={
                "omnibase_core": ModelPackageIdentity(
                    name="omnibase_core",
                    version="0.47.1",
                    commit=None,
                    source=EnumPackageSourceKind.REGISTRY,
                ),
            },
            stamped_at=datetime(2026, 8, 31, tzinfo=UTC),
        )
        with pytest.raises(ProbeTargetMismatchError) as excinfo:
            assert_probe_target(stamped=stamped, declared=_lane_declaration())
        assert excinfo.value.kind is EnumProbeTargetDisagreement.UNKNOWN

    def test_empty_declaration_is_refused(self) -> None:
        """A comparison of zero fields must never report success."""
        declaration = ModelDeclaredTargetIdentity(
            target_name="dev lane",
            declared_by="operator intent",
        )
        with pytest.raises(ProbeTargetMismatchError) as excinfo:
            assert_probe_target(stamped=_lane_stamp(), declared=declaration)
        assert excinfo.value.kind is EnumProbeTargetDisagreement.EMPTY_DECLARATION

    def test_locus_kind_mismatch_is_refused(self) -> None:
        with pytest.raises(ProbeTargetMismatchError) as excinfo:
            assert_probe_target(
                stamped=_local_venv_stamp(),
                declared=_lane_declaration(host=None, execution_locus=None),
            )
        assert excinfo.value.kind is EnumProbeTargetDisagreement.MISMATCH
        assert "does not relocate execution" in excinfo.value.detail


@pytest.mark.unit
class TestAcceptance:
    def test_matching_stamp_returns_a_non_vacuous_verdict(self) -> None:
        verdict = assert_probe_target(
            stamped=_lane_stamp(), declared=_lane_declaration()
        )
        assert verdict.target_name == "dev lane (.201, omnibase-infra)"
        assert verdict.compared_fields == [
            "host",
            "locus_kind",
            "execution_locus",
            "package:omnimarket",
        ]

    def test_verdict_records_the_declaring_surface(self) -> None:
        verdict = assert_probe_target(
            stamped=_lane_stamp(), declared=_lane_declaration()
        )
        assert "build-provenance.json" in verdict.declared_by


@pytest.mark.unit
class TestDeclarationValidation:
    def test_abbreviated_commit_is_refused_at_the_model_boundary(self) -> None:
        with pytest.raises(ValueError, match="40-character"):
            ModelDeclaredTargetIdentity(
                target_name="dev lane",
                declared_by="build-provenance.json",
                packages={"omnimarket": "2f123b4"},
            )
