# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelRuntimeIdentity / ModelPackageIdentity invariants (OMN-17308)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_execution_locus_kind import EnumExecutionLocusKind
from omnibase_core.enums.enum_package_source_kind import EnumPackageSourceKind
from omnibase_core.models.runtime.model_package_identity import ModelPackageIdentity
from omnibase_core.models.runtime.model_runtime_identity import ModelRuntimeIdentity

_SHA = "66b7131a3508" + "0" * 28  # pragma: allowlist secret


def _identity(**overrides: object) -> ModelRuntimeIdentity:
    base: dict[str, object] = {
        "host": "runtime-host",
        "locus_kind": EnumExecutionLocusKind.CONTAINER,
        "execution_locus": "9f2c1b0e4a55",  # pragma: allowlist secret
        "interpreter": "/app/.venv/bin/python3.12",
        "packages": {
            "omnimarket": ModelPackageIdentity(
                name="omnimarket",
                version="0.4.11",
                commit=_SHA,
                source=EnumPackageSourceKind.VCS,
            )
        },
        "stamped_at": datetime(2026, 8, 31, tzinfo=UTC),
    }
    base.update(overrides)
    return ModelRuntimeIdentity(**base)  # type: ignore[arg-type]


@pytest.mark.unit
class TestPackageIdentity:
    def test_commit_is_normalised_to_lowercase(self) -> None:
        entry = ModelPackageIdentity(
            name="omnimarket",
            version="0.4.11",
            commit=_SHA.upper(),
            source=EnumPackageSourceKind.VCS,
        )
        assert entry.commit == _SHA

    def test_abbreviated_commit_is_refused(self) -> None:
        """An abbreviation is not identity — it cannot be compared for equality."""
        with pytest.raises(ValidationError, match="40-character"):
            ModelPackageIdentity(
                name="omnimarket",
                version="0.4.11",
                commit="66b7131",
                source=EnumPackageSourceKind.VCS,
            )

    def test_registry_install_may_carry_no_commit(self) -> None:
        entry = ModelPackageIdentity(
            name="omnibase_core",
            version="0.47.1",
            commit=None,
            source=EnumPackageSourceKind.REGISTRY,
        )
        assert entry.commit is None

    def test_absent_package_cannot_carry_a_version(self) -> None:
        """'Absent' and 'stale' were indistinguishable in OMN-14060 → OMN-14531."""
        with pytest.raises(ValidationError, match="ABSENT"):
            ModelPackageIdentity(
                name="omnimarket",
                version="0.4.11",
                commit=None,
                source=EnumPackageSourceKind.ABSENT,
            )


@pytest.mark.unit
class TestRuntimeIdentity:
    def test_packages_key_must_match_entry_name(self) -> None:
        with pytest.raises(ValidationError, match="mismatched"):
            _identity(
                packages={
                    "omnibase_core": ModelPackageIdentity(
                        name="omnimarket",
                        version="0.4.11",
                        commit=_SHA,
                        source=EnumPackageSourceKind.VCS,
                    )
                }
            )

    def test_empty_package_map_is_refused(self) -> None:
        """A stamp that names no code is not a stamp."""
        with pytest.raises(ValidationError):
            _identity(packages={})

    def test_package_lookup_distinguishes_silence_from_absence(self) -> None:
        identity = _identity()
        assert identity.package("omnimarket") is not None
        assert identity.package("omnibase_infra") is None

    def test_frozen(self) -> None:
        identity = _identity()
        with pytest.raises(ValidationError):
            identity.host = "other"  # type: ignore[misc]

    def test_json_round_trip(self) -> None:
        identity = _identity()
        assert (
            ModelRuntimeIdentity.model_validate_json(identity.model_dump_json())
            == identity
        )


class TestShadowedImport:
    """A SHADOWED entry must name the tree that actually ran (OMN-17308).

    Reproduced live 2026-08-31 while verifying OMN-17310: a stamp collected
    under ``PYTHONPATH=<core-worktree>/src`` reported
    ``omnibase_core=0.47.1@registry`` while executing 0.47.2 worktree source.
    Every field was individually true and the block as a whole was false.
    """

    def test_shadowed_without_import_path_is_refused(self) -> None:
        """A shadowing claim that cannot say which tree won is unverifiable."""
        with pytest.raises(ValidationError, match="names no import_path"):
            ModelPackageIdentity(
                name="omnibase_core",
                version="0.47.1",
                commit=None,
                source=EnumPackageSourceKind.SHADOWED,
            )

    def test_shadowed_carrying_a_commit_is_refused(self) -> None:
        """That commit identifies the tree the interpreter did NOT import."""
        with pytest.raises(ValidationError, match="did NOT import"):
            ModelPackageIdentity(
                name="omnibase_core",
                version="0.47.1",
                commit=_SHA,
                source=EnumPackageSourceKind.SHADOWED,
                import_path="/w/core/src",
            )

    def test_shadowed_naming_the_winner_is_accepted(self) -> None:
        entry = ModelPackageIdentity(
            name="omnibase_core",
            version="0.47.1",
            commit=None,
            source=EnumPackageSourceKind.SHADOWED,
            import_path="/w/core/src/omnibase_core",
        )
        assert entry.import_path == "/w/core/src/omnibase_core"
        assert entry.commit is None

    def test_import_path_defaults_to_none_when_metadata_and_import_agree(
        self,
    ) -> None:
        entry = ModelPackageIdentity(
            name="omnibase_core",
            version="0.47.1",
            commit=_SHA,
            source=EnumPackageSourceKind.VCS,
        )
        assert entry.import_path is None
