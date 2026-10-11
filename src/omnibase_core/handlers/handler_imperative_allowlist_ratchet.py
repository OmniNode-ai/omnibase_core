# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Shrink-only ratchet of a repository's imperative-contract allowlist (OMN-20918).

Each consuming repository carries its own ``allowlisted_handlers`` list, so no
repository can widen another's. Within one repository the list only ever shrinks: a
change that adds a path the merge base does not carry is refused, and a change that
removes one is admitted. An allowlist file that is absent at the merge base has nothing
to ratchet against; its first landing is a bootstrap and is admitted, reported as such.
"""

from __future__ import annotations

import yaml

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.nodes.imperative_contract_guard.model_allowlist_ratchet_input import (
    ModelAllowlistRatchetInput,
)
from omnibase_core.models.nodes.imperative_contract_guard.model_allowlist_ratchet_report import (
    ModelAllowlistRatchetReport,
)


def allowlisted_paths(text: str | None) -> list[str]:
    """Return the ``allowlisted_handlers`` paths of an allowlist text, in file order.

    An absent file, an empty file and a file that is not a mapping carry no path. An
    entry that is not a mapping is refused: a list the ratchet cannot read must not
    be read as shorter than it is.
    """
    if text is None:
        return []
    data = yaml.load(
        text, Loader=yaml.SafeLoader
    )  # SafeLoader, as the source's safe_load
    if not isinstance(data, dict):
        return []
    paths: list[str] = []
    for entry in data.get("allowlisted_handlers", []) or []:
        if not isinstance(entry, dict):
            raise ModelOnexError(
                message=f"allowlisted_handlers entry is not a mapping: {entry!r}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )
        path = entry.get("path", "")
        if path:
            paths.append(path)
    return paths


class HandlerImperativeAllowlistRatchet:
    """Decide whether an allowlist change only shrinks the list."""

    def handle(
        self, request: ModelAllowlistRatchetInput
    ) -> ModelAllowlistRatchetReport:
        """Return the paths added and removed against the merge base."""
        head = allowlisted_paths(request.head_text)
        if request.base_text is None:
            return ModelAllowlistRatchetReport(bootstrap=True)
        base = allowlisted_paths(request.base_text)
        base_set = set(base)
        head_set = set(head)
        return ModelAllowlistRatchetReport(
            added=sorted(head_set - base_set),
            removed=sorted(base_set - head_set),
        )
