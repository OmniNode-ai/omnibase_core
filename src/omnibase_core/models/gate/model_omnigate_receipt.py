# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OmniGate receipt model."""

from __future__ import annotations

import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

from omnibase_core.enums.ticket.enum_receipt_status import EnumReceiptStatus
from omnibase_core.models.gate.model_omnigate_check_result import (
    ModelOmniGateCheckResult,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer

_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_GIT_SHA_RE = re.compile(r"^[0-9a-fA-F]{40}$")
_BLOCKING_STATUSES = frozenset(
    {
        EnumReceiptStatus.FAIL,
        EnumReceiptStatus.PENDING,
    }
)


class ModelOmniGateReceipt(BaseModel):
    """Signed OmniGate proof bound to repository authority fields and diff state."""

    model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)

    schema_version: ModelSemVer
    project_name: str
    project_url: HttpUrl
    repository_identifier: str = Field(
        min_length=1,
        alias="repository_id",
    )
    base_sha: str
    head_sha: str
    commit_sha: str
    diff_hash: str
    config_hash: str
    receipt_schema_fingerprint: str
    branch: str
    timestamp: datetime
    checks: tuple[ModelOmniGateCheckResult, ...] = Field(default=())
    signer_identity: str | None = None
    signer_issuer: str | None = None
    sigstore_bundle_json: str | None = None

    @property
    def repository_id(self) -> str:
        """Return the serialized repository authority identifier."""
        return self.repository_identifier

    @field_validator("diff_hash", "config_hash", "receipt_schema_fingerprint")
    @classmethod
    def _validate_sha256_prefixed(cls, value: str) -> str:
        if not _SHA256_RE.match(value):
            msg = f"hash fields must match sha256:<64 hex chars>, got: {value}"
            raise ValueError(msg)
        return value

    @field_validator("base_sha", "head_sha", "commit_sha")
    @classmethod
    def _validate_git_sha(cls, value: str) -> str:
        if not _GIT_SHA_RE.match(value):
            msg = f"git SHA fields must be exactly 40 hex chars, got: {value}"
            raise ValueError(msg)
        return value

    def no_blocking_checks_failed(self, *, advisory_blocks: bool) -> bool:
        """Return whether trusted policy allows this receipt's check outcomes."""
        blocking_statuses = set(_BLOCKING_STATUSES)
        if advisory_blocks:
            blocking_statuses.add(EnumReceiptStatus.ADVISORY)
        return all(check.status not in blocking_statuses for check in self.checks)


__all__ = ["ModelOmniGateReceipt"]
