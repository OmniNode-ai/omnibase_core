# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Repository detector adapters used by the shared finding-baseline runtime."""

from pydantic import BaseModel, ConfigDict


class ModelLegacyRatchetRule(BaseModel):
    """Scope and adapter binding; predicates remain in their existing checkers."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    hook: str
    module: str = ""
    checker: str = ""
    exclude_parts: tuple[str, ...] = ()
    exclude_prefixes: tuple[str, ...] = ()
    diagnostic_rules: tuple[str, ...] = ()
