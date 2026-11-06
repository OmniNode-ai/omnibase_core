# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Input to the provider import surface check (OMN-22478)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.nodes.no_utcnow_check.model_source_file import (
    ModelSourceFile,
)
from omnibase_core.models.validation.model_provider_module_fact import (
    ModelProviderModuleFact,
)

__all__ = ["ModelProviderImportSurfaceInput"]


class ModelProviderImportSurfaceInput(BaseModel):
    """A provider package at two revisions and the consumer sources that import it.

    Attributes:
        provider_package: The top-level package name the imports are matched on.
        head: The provider's modules at the revision under test.
        base: The provider's modules at the revision it merges onto.
        consumers: Consumer (path, source) pairs.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    provider_package: str = Field(min_length=1)
    head: tuple[ModelProviderModuleFact, ...] = Field(default=())
    base: tuple[ModelProviderModuleFact, ...] = Field(default=())
    consumers: tuple[ModelSourceFile, ...] = Field(default=())
