# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Runtime-identity stamp (OMN-17308, epic OMN-17306).

The block every evidence-producing execution attaches to its own output so the
output is a statement about a knowable process rather than an unattributed
claim.

## Why this exists

Four stale-surface incidents in the week of 2026-08-24, one defect class:

* **OMN-16932 / OMN-17295** — a probe issued as ``onex delegate ... --bus
  kafka`` was read as a statement about the ``.201`` dev lane. ``--bus``
  selects the transport; it does not relocate execution. The orchestrator
  resolved out of the local ``omnibase_infra/.venv`` (``omnimarket 0.4.11`` at
  ``66b7131a3``, pre-fix), and the lane's own logs had zero hits for the
  correlation id. The receipt was byte-indistinguishable from a real lane
  receipt.
* **OMN-17291** — a lane container advertised registry ``0.38.16`` over
  ``omnimarket`` content 11 commits behind ``origin/dev``.
* **OMN-17190** — a stale ``onex`` binary on PATH executed silently in place of
  the one under test.
* **OMN-17291 (defect 1)** — a clone sync reported success without moving
  (``core.bare=true`` makes ``fetch`` exit 0 while ``checkout`` exits 128).

Each was caught by a human comparing install metadata against ``origin/dev`` by
hand. The stamp makes that comparison possible from the artifact alone.

## Shape

Deliberately small and cheap: a handful of ``importlib.metadata`` lookups and
one ``gethostname()``, collected once per process. It answers exactly four
questions — *what code*, *on what host*, *out of what venv or container*,
*against what config* — and nothing else. It is not telemetry and not a
dependency inventory.

## Placement

Pure data in core because :class:`~omnibase_core.models.dispatch.model_skill_result.ModelSkillResult`
carries it and lives in core (repo layering: compat → core → spi → infra, so a
field of a core model may not live in infra). Collection is I/O and lives in
``omnibase_infra`` (OMN-17310).
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.enums.enum_execution_locus_kind import EnumExecutionLocusKind
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.models.runtime.model_package_identity import ModelPackageIdentity

__all__ = ["RUNTIME_IDENTITY_SCHEMA_VERSION", "ModelRuntimeIdentity"]

# Schema version of the identity block itself, independent of the receipt
# envelope's own version.
RUNTIME_IDENTITY_SCHEMA_VERSION = ModelSemVer(major=1, minor=0, patch=0)


class ModelRuntimeIdentity(BaseModel):
    """Self-identification of the process that produced an artifact."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    host: str = Field(
        ...,
        min_length=1,
        description=(
            "Hostname of the machine the process ran on. The coarsest answer "
            "to 'was this my laptop or the lane', and the one that would have "
            "settled OMN-17295 on sight."
        ),
    )
    locus_kind: EnumExecutionLocusKind = Field(
        ...,
        description="Whether the process ran in a venv, a container, or a "
        "bare system interpreter.",
    )
    execution_locus: str = Field(
        ...,
        min_length=1,
        description=(
            "The locus itself: the venv prefix, or the container id. A venv "
            "path distinguishes the CLI venv from the daemon venv from a "
            "worktree venv (OMN-17190); a container id binds the receipt to a "
            "running container rather than to a mutable image tag."
        ),
    )
    interpreter: str = Field(
        ...,
        min_length=1,
        description=(
            "Absolute path of the interpreter that executed (sys.executable). "
            "Makes the OMN-17190 stale-PATH-binary case visible in the "
            "artifact instead of requiring a `which` at the terminal."
        ),
    )
    packages: dict[str, ModelPackageIdentity] = Field(
        ...,
        min_length=1,
        description=(
            "Per-distribution identity, keyed by distribution name. Includes "
            "distributions that are ABSENT, because absence is an identity "
            "fact. An empty map is refused: a stamp that names no code is not "
            "a stamp."
        ),
    )
    config_source: str | None = Field(
        default=None,
        description=(
            "Resolved config/contract source this execution ran against (e.g. "
            "the packaged contract path). None when the execution resolved no "
            "contract. Never a secret value — a location only."
        ),
    )
    stamped_at: datetime = Field(
        ...,
        description=(
            "When the stamp was collected. Caller-supplied rather than "
            "defaulted so a replayed or copied stamp cannot silently "
            "re-date itself."
        ),
    )
    schema_version: ModelSemVer = Field(
        default_factory=lambda: RUNTIME_IDENTITY_SCHEMA_VERSION,
        description="Identity-block schema version, for format evolution.",
    )

    @field_validator("packages")
    @classmethod
    def _keys_match_names(
        cls, value: dict[str, ModelPackageIdentity]
    ) -> dict[str, ModelPackageIdentity]:
        """Refuse a map whose key disagrees with the entry's own name.

        A key/name split is how a stamp starts describing one package under
        another's label — the same substitution the whole epic exists to
        prevent, in miniature.
        """
        mismatched = sorted(key for key, entry in value.items() if key != entry.name)
        if mismatched:
            msg = (
                "packages keys must equal each entry's own name; mismatched "
                f"keys: {mismatched}"
            )
            raise ValueError(msg)
        return value

    def package(self, name: str) -> ModelPackageIdentity | None:
        """Return the identity for ``name``, or ``None`` when unstamped.

        ``None`` here means "this stamp is silent about that package" — which
        is distinct from an entry whose ``source`` is ABSENT ("that package is
        not installed"). Callers that conflate the two reintroduce the
        fail-open path this model exists to close.
        """
        return self.packages.get(name)
