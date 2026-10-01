# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Input snapshot for deterministic OCC merge eligibility."""

from __future__ import annotations

import re
from pathlib import Path, PurePosixPath
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
    field_validator,
    model_validator,
)

from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.utils.util_contract_schema_version import (
    validate_contract_schema_version,
)

_GOAL_TICKET_RE = re.compile(r"^OMN-\d+$")
_REPOSITORY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9][A-Za-z0-9_.-]*$")


class ModelOccEligibilityInput(BaseModel):
    """Immutable PR/OCC snapshot used for deterministic eligibility."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    repo: str = Field(..., min_length=1)
    pr_number: int | None = Field(default=None, ge=1)
    pr_title: str = Field(default="")
    pr_body: str = Field(default="")
    pr_branch: str = Field(default="")
    pr_commit_shas: tuple[str, ...] = Field(default_factory=tuple)
    pr_commit_texts: tuple[str, ...] = Field(default_factory=tuple)
    occ_commit_sha: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    contracts_dir: Path | None = None
    receipts_dir: Path | None = None

    # OR.2 goal admission is a second, explicit input mode on this same
    # resolver. These fields are all absent for the historical ticket/OCC
    # path; once goal_id is present every source and subject binding is
    # required. The resolver never derives these values from PR text.
    goal_id: UUID | None = Field(default=None)
    goal_ticket_id: str | None = Field(  # string-id-ok: external Linear correlation key
        default=None,
        description="Optional Linear correlation for a goal; not goal identity.",
    )
    contract_revision: UUID | None = Field(default=None)
    contract_schema_version: ModelSemVer | None = Field(default=None)
    goal_contract_root: Path | None = Field(default=None)
    goal_contract_path: PurePosixPath | None = Field(default=None)
    goal_contract_source_commit_sha: str | None = Field(default=None)
    goal_contract_sha256: str | None = Field(default=None)
    subject_commit_sha: str | None = Field(default=None)
    subject_tree_sha: str | None = Field(default=None)

    @field_validator(
        "contract_schema_version", mode="before", json_schema_input_type=str
    )
    @classmethod
    def _parse_contract_schema_version(cls, value: object) -> ModelSemVer | None:
        if value is None:
            return None
        if isinstance(value, ModelSemVer):
            validate_contract_schema_version(value.to_string())
            return value
        if not isinstance(value, str):
            raise ValueError("contract_schema_version must be a SemVer string")
        validate_contract_schema_version(value)
        return ModelSemVer.parse(value)

    @field_serializer(
        "contract_schema_version", when_used="json", return_type=str | None
    )
    def _serialize_contract_schema_version(
        self, value: ModelSemVer | None
    ) -> str | None:
        return value.to_string() if value is not None else None

    @model_validator(mode="after")
    def _validate_goal_source_and_subject(self) -> ModelOccEligibilityInput:
        """Require one complete, explicitly typed goal admission identity."""
        goal_fields = (
            self.goal_ticket_id,
            self.contract_revision,
            self.contract_schema_version,
            self.goal_contract_root,
            self.goal_contract_path,
            self.goal_contract_source_commit_sha,
            self.goal_contract_sha256,
            self.subject_commit_sha,
            self.subject_tree_sha,
        )
        if self.goal_id is None:
            if any(value is not None for value in goal_fields):
                raise ValueError("goal admission fields require goal_id")
            if (
                self.occ_commit_sha is None
                or self.contracts_dir is None
                or self.receipts_dir is None
            ):
                raise ValueError(
                    "legacy OCC mode requires occ_commit_sha, contracts_dir, and receipts_dir"
                )
            if self.pr_number is None:
                raise ValueError("legacy OCC mode requires a pull request number")
            return self

        if self.pr_number is None and any(
            (self.pr_title, self.pr_body, self.pr_branch, self.pr_commit_shas)
        ):
            raise ValueError(
                "goal subjects without a pull request cannot carry PR metadata"
            )

        occ_fields = (self.occ_commit_sha, self.contracts_dir, self.receipts_dir)
        if any(value is not None for value in occ_fields) and any(
            value is None for value in occ_fields
        ):
            raise ValueError(
                "goal mode may omit legacy OCC fields, but cannot provide a partial set"
            )

        required = {
            "contract_revision": self.contract_revision,
            "contract_schema_version": self.contract_schema_version,
            "goal_contract_root": self.goal_contract_root,
            "goal_contract_path": self.goal_contract_path,
            "goal_contract_source_commit_sha": self.goal_contract_source_commit_sha,
            "goal_contract_sha256": self.goal_contract_sha256,
            "subject_commit_sha": self.subject_commit_sha,
            "subject_tree_sha": self.subject_tree_sha,
        }
        missing = sorted(name for name, value in required.items() if value is None)
        if missing:
            raise ValueError(
                "goal admission requires explicit source and subject fields: "
                + ", ".join(missing)
            )

        if self.goal_ticket_id is not None and not _GOAL_TICKET_RE.fullmatch(
            self.goal_ticket_id
        ):
            raise ValueError("goal_ticket_id must be an OMN ticket id or None")
        if self.goal_contract_root is None or not self.goal_contract_root.is_absolute():
            raise ValueError("goal_contract_root must be an absolute repository path")
        if self.goal_contract_path is None:
            raise ValueError("goal_contract_path is required in goal mode")
        if (
            self.goal_contract_path.is_absolute()
            or ".." in self.goal_contract_path.parts
            or not self.goal_contract_path.parts
            or self.goal_contract_path.parts[:2] != ("contracts", "goals")
        ):
            raise ValueError(
                "goal_contract_path must be under contracts/goals/ in the repository"
            )
        if self.goal_contract_source_commit_sha is None or not _is_full_git_sha(
            self.goal_contract_source_commit_sha
        ):
            raise ValueError(
                "goal_contract_source_commit_sha must be a full lowercase Git SHA"
            )
        if self.goal_contract_sha256 is None or not _is_sha256(
            self.goal_contract_sha256
        ):
            raise ValueError("goal_contract_sha256 must be a SHA-256 digest")
        if self.subject_commit_sha is None or not _is_full_git_sha(
            self.subject_commit_sha
        ):
            raise ValueError("subject_commit_sha must be a full lowercase Git SHA")
        if self.subject_tree_sha is None or not _is_full_git_sha(self.subject_tree_sha):
            raise ValueError("subject_tree_sha must be a full lowercase Git SHA")
        if not _REPOSITORY_RE.fullmatch(self.repo):
            raise ValueError("goal-mode repo must be the canonical owner/repository")
        return self


def _is_full_git_sha(value: str) -> bool:
    # The existing OCC receipt and repository tooling use SHA-1 object IDs.
    return len(value) == 40 and all(char in "0123456789abcdef" for char in value)


def _is_sha256(value: str) -> bool:
    return (
        value.startswith("sha256:")
        and len(value) == 71
        and all(char in "0123456789abcdef" for char in value[7:])
    )


__all__ = ["ModelOccEligibilityInput"]
