# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ThemeCatalogEntry — one published theme revision (OMN-16882, Phase C1).

A catalog entry is the *published* record of one immutable theme instance
revision: which theme, which revision, which schema version it validates
against, the SHA-256 of its published bytes, and where those bytes live.

The digest lives here rather than on ``ModelThemeInstance`` because an object
cannot contain its own hash without the hash covering itself. It is the only
one of the three version axes a machine can compare across two surfaces, which
is exactly what gate GC.2 asks for.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.models.primitives.model_semver import ModelSemVer

__all__ = ["ModelThemeCatalogEntry", "THEME_CONTENT_DIGEST_PATTERN"]

#: Published-byte digests are ``sha256:<64 lowercase hex chars>``.
THEME_CONTENT_DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")


class ModelThemeCatalogEntry(BaseModel):
    """One immutable, digested theme revision in the catalog."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    theme_id: str = Field(  # string-id-ok: namespaced theme label, not a UUID
        ...,
        description="Namespaced theme identifier (e.g. 'onex.theme.dark')",
        min_length=1,
    )
    schema_version: ModelSemVer = Field(
        ...,
        description="ModelRendererThemeContract version this revision validates against",
    )
    instance_revision: ModelSemVer = Field(
        ...,
        description="Revision of the theme instance document",
    )
    content_digest: str = Field(
        ...,
        description="SHA-256 over the published bytes, as 'sha256:<hex>'",
    )
    source_path: str = Field(
        ...,
        description="Catalog-root-relative path of the instance document",
        min_length=1,
    )

    @field_validator("content_digest")
    @classmethod
    def validate_content_digest(cls, value: str) -> str:
        """Reject anything that is not a ``sha256:<hex>`` digest.

        Raises:
            ValueError: If ``value`` does not match the digest pattern.
        """
        if not THEME_CONTENT_DIGEST_PATTERN.match(value):
            raise ValueError(
                f"content_digest must match 'sha256:<64 hex chars>', got '{value}'"
            )
        return value
