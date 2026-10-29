# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One enabled surface row of the ``no_io_outside_effects`` contract, read and compiled (OMN-21532)."""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict

from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)

__all__ = ["ModelNoIoOutsideEffectsMatcher"]


class ModelNoIoOutsideEffectsMatcher(BaseModel):
    """The matcher parameters of a rule row, typed; patterns are compiled once."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
        arbitrary_types_allowed=True,
    )

    rule: ModelValidatorRule
    import_roots: frozenset[str]
    import_modules: tuple[str, ...]
    callees: tuple[re.Pattern[str], ...]
    methods: frozenset[str]
    classes: tuple[re.Pattern[str], ...]
    executables: tuple[str, ...]
    command_callees: tuple[re.Pattern[str], ...]
    subscripts: frozenset[str]
    url_substrings: tuple[str, ...]
    open_names: frozenset[str]
    open_mode_chars: str
    open_when: str
