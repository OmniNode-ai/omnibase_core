# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Facts for one check_bindings run."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from omnibase_core.models.binding_conformance.model_binding_protocol_table import (
    ModelBindingProtocolTable,
)
from omnibase_core.models.binding_conformance.model_binding_source import (
    ModelBindingSource,
)
from omnibase_core.models.binding_conformance.model_concrete_binding import (
    ModelConcreteBinding,
)
from omnibase_core.models.binding_conformance.model_private_name import (
    ModelPrivateName,
)


class ModelBindingConformanceRequest(BaseModel):
    """Contracts and sources as text, plus the table, the bindings and the names as data."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    checked_nodes: tuple[str, ...]
    protocol_table: ModelBindingProtocolTable
    concrete_bindings: tuple[ModelConcreteBinding, ...] = ()
    pure_forbidden_modules: tuple[str, ...] = ()
    private_names: tuple[ModelPrivateName, ...] = ()
    sources: tuple[ModelBindingSource, ...]
