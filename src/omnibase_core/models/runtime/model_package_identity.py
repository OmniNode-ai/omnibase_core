# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Per-distribution identity for the runtime-identity stamp (OMN-17308).

One entry of :class:`~omnibase_core.models.runtime.model_runtime_identity.ModelRuntimeIdentity`
``packages``: what a single installed distribution actually is, at content
granularity rather than at label granularity.

Why both fields. ``version`` comes from ``importlib.metadata`` and is a label
the packaging system prints; ``commit`` names the content. The two are
routinely inconsistent, and every incident in the OMN-17306 class turned on
reading the first as though it were the second — most starkly OMN-17291, where
a lane advertised registry ``0.38.16`` while its vendored ``omnimarket`` sat 11
commits behind ``origin/dev`` at ``05e3882f9``.

This model is pure data. Collecting it needs ``importlib.metadata``, PEP 610
``direct_url.json`` and (inside a container) the RT-1 build-provenance
manifest, none of which belongs in core — that lives in omnibase_infra
(OMN-17310).
"""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from omnibase_core.enums.enum_package_source_kind import EnumPackageSourceKind

__all__ = ["ModelPackageIdentity"]

_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")


class ModelPackageIdentity(BaseModel):
    """What one installed distribution is, by label AND by content."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    name: str = Field(
        ...,
        min_length=1,
        description="Distribution name as importlib.metadata knows it.",
    )
    version: str | None = Field(
        default=None,
        description=(
            "Installed version string, or None when the distribution is "
            "ABSENT. A version alone is a label, never proof of content."
        ),
    )
    commit: str | None = Field(
        default=None,
        description=(
            "Full 40-character git commit the distribution was built from, "
            "when it is recoverable (PEP 610 vcs_info, or a build-time "
            "provenance manifest for a workspace install). None is an honest "
            "'not recoverable', never a placeholder."
        ),
    )
    source: EnumPackageSourceKind = Field(
        ...,
        description="How the distribution was sourced. Decides whether a "
        "missing commit is expected (REGISTRY) or a violation (VCS).",
    )
    import_path: str | None = Field(
        default=None,
        description=(
            "Directory the interpreter actually imports this package's "
            "top-level module from, when it differs from the location the "
            "install metadata claims. None means the two agree, or the "
            "package is ABSENT. Required whenever source is SHADOWED: the "
            "whole content of that verdict is 'the code that runs is over "
            "there', so a SHADOWED entry that cannot say where is an "
            "unsupported claim."
        ),
    )

    @field_validator("commit")
    @classmethod
    def _validate_commit(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        if not _COMMIT_RE.match(normalized):
            msg = (
                "commit must be a full 40-character lowercase hex git SHA "
                f"(abbreviations are not identity), got: {value!r}"
            )
            raise ValueError(msg)
        return normalized

    @model_validator(mode="after")
    def _absent_carries_nothing(self) -> ModelPackageIdentity:
        """An ABSENT distribution cannot carry a version or a commit.

        Recorded as a hard rule rather than a convention because "absent" was
        repeatedly indistinguishable from "stale" in the OMN-14060 →
        OMN-14531 recurrence: the guard's fail-open path treated a missing
        install and an unreadable one identically.
        """
        if self.source is EnumPackageSourceKind.ABSENT and (
            self.version is not None or self.commit is not None
        ):
            msg = (
                f"package {self.name!r} is ABSENT but carries "
                f"version={self.version!r} commit={self.commit!r}; an absent "
                "distribution has neither"
            )
            raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def _shadowed_names_the_winner(self) -> ModelPackageIdentity:
        """A SHADOWED entry must say where the code that actually runs lives.

        SHADOWED means "the metadata describes a tree the interpreter did not
        import". An entry that asserts that and cannot name the winning path
        states the problem without giving anyone the means to check it, which
        is the vacuous-verdict failure class of OMN-14531. It must also carry
        no commit: the metadata's commit identifies the tree that lost, so
        reporting it here would attribute a SHA to code that never ran --
        exactly the substitution this whole model exists to prevent.
        """
        if self.source is not EnumPackageSourceKind.SHADOWED:
            return self
        if self.import_path is None:
            msg = (
                f"package {self.name!r} is SHADOWED but names no import_path; "
                "a shadowing claim that cannot say which tree won is "
                "unverifiable"
            )
            raise ValueError(msg)
        if self.commit is not None:
            msg = (
                f"package {self.name!r} is SHADOWED but carries "
                f"commit={self.commit!r}; that commit identifies the tree the "
                "interpreter did NOT import"
            )
            raise ValueError(msg)
        return self
