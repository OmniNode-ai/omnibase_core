# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the typed package-only deploy-gate binding schema."""

from __future__ import annotations

from copy import deepcopy

import pytest
from pydantic import ValidationError

from omnibase_core.enums.ticket import EnumPackageOnlyManifestStatus
from omnibase_core.models.ticket import (
    ModelPackageOnlyDeployBinding,
    ModelPackageOnlyManifestEntry,
    ModelTicketContract,
    compute_package_only_manifest_sha256,
)

_BASE_SHA = "a" * 40
_HEAD_SHA = "b" * 40
_DIFF_BASE_SHA = "d" * 40
_BLOB_SHA = "c" * 40


def _entry_data(**overrides: object) -> dict[str, object]:
    data: dict[str, object] = {
        "filename": "src/omnibase_core/example.py",
        "status": "modified",
        "previous_filename": None,
        "blob_sha": _BLOB_SHA,
        "old_mode": "100644",
        "new_mode": "100644",
        "old_object_type": "blob",
        "new_object_type": "blob",
        "is_binary": False,
        "is_submodule": False,
    }
    data.update(overrides)
    return data


def _binding_data(**overrides: object) -> dict[str, object]:
    entry = ModelPackageOnlyManifestEntry(**_entry_data())
    data: dict[str, object] = {
        "repository": "OmniNode-ai/omnibase_core",
        "base_sha": _BASE_SHA,
        "head_sha": _HEAD_SHA,
        "diff_base_sha": _DIFF_BASE_SHA,
        "policy_id": "package-only-core",
        "policy_version": "1.0.0",
        "manifest_sha256": compute_package_only_manifest_sha256((entry,)),
        "changed_files": (entry,),
    }
    data.update(overrides)
    return data


class TestModelPackageOnlyManifestEntry:
    """Entry validation keeps GitHub diff metadata complete and closed."""

    def test_accepts_explicit_null_metadata_for_added_file(self) -> None:
        entry = ModelPackageOnlyManifestEntry(
            **_entry_data(
                status=EnumPackageOnlyManifestStatus.ADDED,
                old_mode=None,
                old_object_type=None,
            )
        )

        assert entry.status is EnumPackageOnlyManifestStatus.ADDED
        assert entry.old_mode is None
        assert entry.old_object_type is None

    def test_accepts_explicit_null_metadata_for_removed_file(self) -> None:
        entry = ModelPackageOnlyManifestEntry(
            **_entry_data(
                status=EnumPackageOnlyManifestStatus.REMOVED,
                new_mode=None,
                new_object_type=None,
            )
        )

        assert entry.status is EnumPackageOnlyManifestStatus.REMOVED
        assert entry.new_mode is None
        assert entry.new_object_type is None

    @pytest.mark.parametrize(
        "status",
        [
            EnumPackageOnlyManifestStatus.RENAMED,
            EnumPackageOnlyManifestStatus.COPIED,
        ],
    )
    def test_rename_and_copy_require_a_distinct_previous_filename(
        self, status: EnumPackageOnlyManifestStatus
    ) -> None:
        with pytest.raises(ValidationError, match="require previous_filename"):
            ModelPackageOnlyManifestEntry(**_entry_data(status=status))

        entry = ModelPackageOnlyManifestEntry(
            **_entry_data(
                status=status,
                previous_filename="src/omnibase_core/previous.py",
            )
        )
        assert entry.previous_filename == "src/omnibase_core/previous.py"

        with pytest.raises(ValidationError, match="must differ"):
            ModelPackageOnlyManifestEntry(
                **_entry_data(
                    status=status,
                    previous_filename="src/omnibase_core/example.py",
                )
            )

    def test_rejects_previous_filename_for_non_rename_status(self) -> None:
        with pytest.raises(ValidationError, match="allowed only"):
            ModelPackageOnlyManifestEntry(
                **_entry_data(previous_filename="src/omnibase_core/previous.py")
            )

    @pytest.mark.parametrize(
        "path",
        [
            "/absolute.py",
            "src//duplicate.py",
            "src/./dot.py",
            "src/../parent.py",
            r"src\\windows.py",
            "src/control\x00.py",
        ],
    )
    def test_rejects_noncanonical_filename(self, path: str) -> None:
        with pytest.raises(ValidationError, match="path must"):
            ModelPackageOnlyManifestEntry(**_entry_data(filename=path))

    def test_rejects_noncanonical_previous_filename(self) -> None:
        with pytest.raises(ValidationError, match="path must"):
            ModelPackageOnlyManifestEntry(
                **_entry_data(
                    status=EnumPackageOnlyManifestStatus.RENAMED,
                    previous_filename="src/../prior.py",
                )
            )

    @pytest.mark.parametrize(
        "field",
        [
            "old_mode",
            "new_mode",
            "old_object_type",
            "new_object_type",
            "is_binary",
            "is_submodule",
        ],
    )
    def test_rejects_absent_required_diff_metadata(self, field: str) -> None:
        data = _entry_data()
        del data[field]

        with pytest.raises(ValidationError):
            ModelPackageOnlyManifestEntry(**data)

    @pytest.mark.parametrize(
        ("field", "value"),
        [
            ("blob_sha", "C" * 40),
            ("blob_sha", "c" * 39),
            ("old_mode", "10064"),
            ("new_mode", "1006447"),
        ],
    )
    def test_rejects_malformed_git_identifiers(self, field: str, value: str) -> None:
        with pytest.raises(ValidationError):
            ModelPackageOnlyManifestEntry(**_entry_data(**{field: value}))

    @pytest.mark.parametrize(
        "overrides",
        [
            {"status": "added", "old_mode": "100644", "old_object_type": "blob"},
            {"status": "removed", "new_mode": "100644", "new_object_type": "blob"},
            {"old_mode": None},
            {"old_object_type": None},
            {"old_mode": "100644", "old_object_type": "commit"},
            {"old_mode": "160000", "is_submodule": False},
            {"old_mode": "160000", "old_object_type": "commit", "is_submodule": False},
        ],
    )
    def test_rejects_inconsistent_object_metadata(
        self, overrides: dict[str, object]
    ) -> None:
        with pytest.raises(ValidationError):
            ModelPackageOnlyManifestEntry(**_entry_data(**overrides))

    def test_accepts_submodule_metadata_when_commit_modes_match(self) -> None:
        entry = ModelPackageOnlyManifestEntry(
            **_entry_data(
                old_mode="160000",
                new_mode="160000",
                old_object_type="commit",
                new_object_type="commit",
                is_submodule=True,
            )
        )

        assert entry.is_submodule is True

    def test_rejects_unknown_fields_and_is_frozen(self) -> None:
        with pytest.raises(ValidationError):
            ModelPackageOnlyManifestEntry(**_entry_data(unapproved=True))

        entry = ModelPackageOnlyManifestEntry(**_entry_data())
        with pytest.raises(ValidationError):
            entry.filename = "changed.py"  # type: ignore[misc]


class TestModelPackageOnlyDeployBinding:
    """Binding validation proves the manifest and source identities agree."""

    def test_accepts_complete_binding_through_ticket_contract_parsing(self) -> None:
        binding_data = _binding_data()
        ticket = ModelTicketContract.model_validate(
            {
                "ticket_id": "OMN-18156",
                "title": "typed package-only binding",
                "package_only_deploy_binding": binding_data,
            }
        )

        assert ticket.package_only_deploy_binding is not None
        assert ticket.package_only_deploy_binding == ModelPackageOnlyDeployBinding(
            **binding_data
        )
        dumped_binding = ticket.model_dump(mode="json")["package_only_deploy_binding"]
        assert isinstance(dumped_binding, dict)
        assert dumped_binding["manifest_sha256"] == binding_data["manifest_sha256"]
        assert (
            dumped_binding["changed_files"][0]["filename"] == _entry_data()["filename"]
        )

    def test_digest_is_deterministic_for_the_same_typed_entry_set(self) -> None:
        first = ModelPackageOnlyManifestEntry(**_entry_data(filename="a.py"))
        second = ModelPackageOnlyManifestEntry(**_entry_data(filename="b.py"))

        first_order = compute_package_only_manifest_sha256((first, second))
        second_order = compute_package_only_manifest_sha256((second, first))

        assert first_order == second_order
        binding = ModelPackageOnlyDeployBinding(
            **_binding_data(
                changed_files=(second, first),
                manifest_sha256=second_order,
            )
        )
        assert binding.manifest_sha256 == first_order

    def test_binding_identity_retains_the_compare_base(self) -> None:
        binding = ModelPackageOnlyDeployBinding(**_binding_data())

        assert binding.diff_base_sha == _DIFF_BASE_SHA
        assert binding.model_dump(mode="json")["diff_base_sha"] == _DIFF_BASE_SHA

    def test_rejects_diff_base_equal_to_head(self) -> None:
        with pytest.raises(ValidationError, match="diff_base_sha and head_sha"):
            ModelPackageOnlyDeployBinding(**_binding_data(diff_base_sha=_HEAD_SHA))

    def test_rejects_stale_digest_and_duplicate_filenames(self) -> None:
        stale = deepcopy(_binding_data())
        stale["manifest_sha256"] = "sha256:" + "0" * 64
        with pytest.raises(ValidationError, match="does not match"):
            ModelPackageOnlyDeployBinding(**stale)

        first = ModelPackageOnlyManifestEntry(**_entry_data())
        duplicate = ModelPackageOnlyManifestEntry(**_entry_data(blob_sha="d" * 40))
        duplicate_data = _binding_data(changed_files=(first, duplicate))
        duplicate_data["manifest_sha256"] = compute_package_only_manifest_sha256(
            (first, duplicate)
        )
        with pytest.raises(ValidationError, match="duplicate filenames"):
            ModelPackageOnlyDeployBinding(**duplicate_data)

    @pytest.mark.parametrize(
        ("field", "value"),
        [
            ("repository", "OmniNode-ai/other"),
            ("base_sha", "A" * 40),
            ("head_sha", "b" * 39),
            ("diff_base_sha", "D" * 40),
            ("policy_version", "1.0"),
            ("manifest_sha256", "sha256:" + "A" * 64),
        ],
    )
    def test_rejects_noncanonical_source_identity(self, field: str, value: str) -> None:
        with pytest.raises(ValidationError):
            ModelPackageOnlyDeployBinding(**_binding_data(**{field: value}))

    def test_rejects_identical_base_and_head(self) -> None:
        data = _binding_data(head_sha=_BASE_SHA)
        with pytest.raises(ValidationError, match="different commits"):
            ModelPackageOnlyDeployBinding(**data)

    def test_rejects_unknown_fields_and_empty_manifest(self) -> None:
        with pytest.raises(ValidationError):
            ModelPackageOnlyDeployBinding(**_binding_data(unapproved=True))

        with pytest.raises(ValidationError):
            ModelPackageOnlyDeployBinding(
                **_binding_data(
                    changed_files=(),
                    manifest_sha256=compute_package_only_manifest_sha256(()),
                )
            )
