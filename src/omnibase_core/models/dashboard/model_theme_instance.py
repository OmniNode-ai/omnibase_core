# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ThemeInstance — a published set of design-token VALUES (OMN-16882, Phase C1).

``ModelRendererThemeContract`` is a **schema**: every token field is required
and the class holds no values. It answers *what a theme must contain*. It
cannot answer *what this theme's accent colour is*, because there is nothing in
the class to read.

``ModelThemeInstance`` is the missing half — an instance document that carries a
complete, schema-validated token set plus the header a lifecycle needs. Instance
documents are **data**: serialized YAML under
``omnibase_core/contracts/themes/<theme_id>/<instance_revision>.yaml``. Changing
a token value edits a document; it never edits a Python class. A class edit is a
*schema* change and moves a different version axis entirely.

Three version axes, deliberately three fields:

* ``schema_version`` — the ``ModelRendererThemeContract`` version this document
  was authored against. Moves when a token *field* is added, removed, or
  renamed.
* ``instance_revision`` — this document's own revision. Moves when a token
  *value* changes.
* content digest — SHA-256 over the published bytes. Moves on any byte change
  from either source above. Materialised on ``ModelThemeCatalogEntry``, never
  stored inside the instance it digests.

Conflating any two of them is how a stale artifact passes on a matching version
number, so ``schema_version`` and ``theme_id`` are declared in the document
header **and** cross-checked against the embedded token set: a document whose
header disagrees with its body is rejected, not reconciled.
"""

from __future__ import annotations

from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.models.dashboard.model_renderer_theme_contract import (
    ModelRendererThemeContract,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer

__all__ = ["ModelThemeInstance"]


class ModelThemeInstance(BaseModel):
    """A versioned, schema-validated set of design-token values.

    The unit a surface activates and a catalog entry points at. Immutable:
    a published revision is never edited in place, because rollback is only
    meaningful if the bytes behind a revision cannot move.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    theme_id: str = Field(  # string-id-ok: namespaced theme label, not a UUID
        ...,
        description=(
            "Stable, namespaced theme identifier (e.g. 'onex.theme.dark'). "
            "Must equal the embedded token set's theme_id."
        ),
        min_length=1,
    )
    schema_version: ModelSemVer = Field(
        ...,
        description=(
            "ModelRendererThemeContract version this document was authored "
            "against. Must equal tokens.contract_version."
        ),
    )
    instance_revision: ModelSemVer = Field(
        ...,
        description=(
            "This document's own revision. Bump when a token VALUE changes; "
            "distinct from schema_version, which tracks token FIELDS."
        ),
    )
    summary: str = Field(
        ...,
        description="Human-readable description of what this theme revision is for",
        min_length=1,
    )
    tokens: ModelRendererThemeContract = Field(
        ...,
        description="The complete, schema-validated token value set",
    )

    @model_validator(mode="after")
    def validate_header_matches_tokens(self) -> Self:
        """Fail closed when the document header disagrees with its token body.

        The header exists so the three version axes are legible without parsing
        the whole token set. A header that can drift from the body is worse than
        no header at all, so a mismatch is an error rather than a reconciliation.

        Raises:
            ValueError: If ``theme_id`` or ``schema_version`` disagrees with the
                embedded ``tokens``.
        """
        if self.theme_id != self.tokens.theme_id:
            raise ValueError(
                f"theme_id '{self.theme_id}' does not match tokens.theme_id "
                f"'{self.tokens.theme_id}'"
            )
        if self.schema_version != self.tokens.contract_version:
            raise ValueError(
                f"schema_version '{self.schema_version}' does not match "
                f"tokens.contract_version '{self.tokens.contract_version}'"
            )
        return self
