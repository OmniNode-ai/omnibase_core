# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed, fail-closed changed-file record for a package-only deploy binding."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from omnibase_core.enums.ticket.enum_package_only_manifest_status import (
    EnumPackageOnlyManifestStatus,
)

_GIT_SHA_PATTERN = r"^[0-9a-f]{40}$"
_GIT_MODE_PATTERN = r"^[0-7]{6}$"
_MAX_PATH_LENGTH = 4096
_OBJECT_TYPES = Literal["blob", "tree", "commit"]
_MODE_BY_OBJECT_TYPE: dict[str, frozenset[str]] = {
    "blob": frozenset({"100644", "100755", "120000"}),
    "tree": frozenset({"040000"}),
    "commit": frozenset({"160000"}),
}


class ModelPackageOnlyManifestEntry(BaseModel):
    """One GitHub/Git changed-file record with explicit diff metadata."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    filename: str = Field(
        ...,
        min_length=1,
        max_length=_MAX_PATH_LENGTH,
        description="Repository-relative filename at the binding head.",
    )
    status: EnumPackageOnlyManifestStatus = Field(
        ...,
        description="Closed GitHub diff status for the file.",
    )
    previous_filename: str | None = Field(
        ...,
        min_length=1,
        max_length=_MAX_PATH_LENGTH,
        description="Prior repository-relative filename for renamed or copied files.",
    )
    blob_sha: str = Field(
        ...,
        pattern=_GIT_SHA_PATTERN,
        description="Exact 40-character Git blob identifier reported for the file.",
    )
    old_mode: str | None = Field(
        ...,
        pattern=_GIT_MODE_PATTERN,
        description="Prior Git mode, or explicit null when no prior object exists.",
    )
    new_mode: str | None = Field(
        ...,
        pattern=_GIT_MODE_PATTERN,
        description="Head Git mode, or explicit null when no head object exists.",
    )
    old_object_type: _OBJECT_TYPES | None = Field(
        ...,
        description="Prior Git object type, or explicit null when absent.",
    )
    new_object_type: _OBJECT_TYPES | None = Field(
        ...,
        description="Head Git object type, or explicit null when absent.",
    )
    is_binary: bool = Field(
        ...,
        description="Whether the changed file has binary content.",
    )
    is_submodule: bool = Field(
        ...,
        description="Whether the changed path is a Git submodule.",
    )

    @field_validator("filename", "previous_filename")
    @classmethod
    def validate_repository_relative_path(cls, value: str | None) -> str | None:
        """Reject noncanonical path spellings instead of normalizing them."""
        if value is None:
            return None
        if value.startswith("/"):
            msg = "path must be a canonical repository-relative POSIX path"
            raise ValueError(msg)
        if "\\" in value:
            msg = "path must be a canonical repository-relative POSIX path"
            raise ValueError(msg)
        if "//" in value:
            msg = "path must be a canonical repository-relative POSIX path"
            raise ValueError(msg)
        if any(ord(character) < 32 or ord(character) == 127 for character in value):
            msg = "path must be a canonical repository-relative POSIX path"
            raise ValueError(msg)
        if any(segment in {"", ".", ".."} for segment in value.split("/")):
            msg = "path must not contain empty, dot, or parent segments"
            raise ValueError(msg)
        return value

    @model_validator(mode="after")
    def validate_diff_metadata(self) -> ModelPackageOnlyManifestEntry:
        """Require coherent status, Git-object, and submodule metadata."""
        requires_previous = self.status in {
            EnumPackageOnlyManifestStatus.RENAMED,
            EnumPackageOnlyManifestStatus.COPIED,
        }
        if requires_previous:
            if self.previous_filename is None:
                msg = "renamed or copied entries require previous_filename"
                raise ValueError(msg)
            if self.previous_filename == self.filename:
                msg = "previous_filename must differ from filename"
                raise ValueError(msg)
        elif self.previous_filename is not None:
            msg = "previous_filename is allowed only for renamed or copied entries"
            raise ValueError(msg)

        self._validate_object_side("old", self.old_mode, self.old_object_type)
        self._validate_object_side("new", self.new_mode, self.new_object_type)

        expected_old, expected_new = self._expected_object_presence()
        if (self.old_mode is not None) != expected_old:
            msg = f"{self.status.value} entries have invalid old-object metadata"
            raise ValueError(msg)
        if (self.new_mode is not None) != expected_new:
            msg = f"{self.status.value} entries have invalid new-object metadata"
            raise ValueError(msg)

        has_submodule_object = "commit" in {
            object_type
            for object_type in (self.old_object_type, self.new_object_type)
            if object_type is not None
        }
        if self.is_submodule != has_submodule_object:
            msg = "is_submodule must match commit object metadata"
            raise ValueError(msg)
        return self

    def _expected_object_presence(self) -> tuple[bool, bool]:
        """Return required old/new object presence for the closed diff status."""
        if self.status is EnumPackageOnlyManifestStatus.ADDED:
            return False, True
        if self.status is EnumPackageOnlyManifestStatus.REMOVED:
            return True, False
        return True, True

    @staticmethod
    def _validate_object_side(
        side: str,
        mode: str | None,
        object_type: _OBJECT_TYPES | None,
    ) -> None:
        """Require a complete and internally valid Git object side."""
        if (mode is None) != (object_type is None):
            msg = f"{side}_mode and {side}_object_type must both be null or present"
            raise ValueError(msg)  # error-ok: Pydantic validator input boundary
        if mode is None or object_type is None:
            return
        if mode not in _MODE_BY_OBJECT_TYPE[object_type]:
            msg = f"{side}_mode is incompatible with {side}_object_type"
            raise ValueError(msg)  # error-ok: Pydantic validator input boundary


__all__ = ["ModelPackageOnlyManifestEntry"]
