# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelRuntimeOpsVerbAllowlist — governed RUNTIME_OPS mutation-verb allowlist (OMN-18038).

Typed contract boundary for ``omnibase_core/contracts/runtime_ops_verb_allowlist.yaml``,
the single source of truth for ``ModelDodReceipt.mutation_verb`` (OMN-14168). The
document is closed: it declares exactly a schema version and the bounded verb list,
so the model forbids extras and rejects a blank or empty list at the boundary rather
than letting a malformed governed file degrade the class silently.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ModelRuntimeOpsVerbAllowlist(BaseModel):
    """Parsed ``runtime_ops_verb_allowlist.yaml`` document."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: int = Field(
        description="Governed-data schema version of the allowlist document",
    )
    runtime_ops_verbs: list[str] = Field(
        min_length=1,
        description="Bounded set of live-runtime mutation verbs (never source edits)",
    )

    @field_validator("runtime_ops_verbs")
    @classmethod
    def _verbs_are_non_blank(cls, verbs: list[str]) -> list[str]:
        """Reject blank entries — a blank verb can never match and hides a typo."""
        for verb in verbs:
            if not verb.strip():
                raise ValueError(  # error-ok: governed allowlist entry is blank
                    "runtime_ops_verbs entries must be non-blank strings, "
                    f"got: {verb!r}"
                )
        return verbs

    @property
    def normalized_verbs(self) -> frozenset[str]:
        """Whitespace-stripped verb set, the form every enforcement surface compares."""
        return frozenset(verb.strip() for verb in self.runtime_ops_verbs)


__all__ = ["ModelRuntimeOpsVerbAllowlist"]
