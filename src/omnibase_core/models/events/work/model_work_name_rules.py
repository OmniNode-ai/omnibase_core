# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One spelling per lane and per proof surface (OMN-16177, S6 of the second review).

Repository names are lower-cased and pattern-checked (``REPO_NAME_PATTERN``), so
every spelling of one repository is one value. Lane and surface names get the
same rule: strip surrounding whitespace, lower-case, then check a pattern. The
patterns are the widest that still admit every name the ledger grammar allows
and the rolling ledger holds today, so a rule here never refuses a legal row:

* A lane is the grammar's lane token, lower-cased: it starts with a letter or
  digit and continues with letters, digits and ``_ . : -`` (live lane names
  carry colons and dots, e.g. ``codex:handoff-auto-merge-guard``).
* A surface has no grammar rule, so it takes the lane characters and may also
  begin with a dot, because ``.201-dev-deploy-agent`` is a surface a live lease
  named.

Both are at most 128 characters, the limit the fields carried before this rule.
"""

from __future__ import annotations

from typing import Final

__all__ = [
    "LANE_NAME_PATTERN",
    "SURFACE_NAME_PATTERN",
    "normalize_work_name",
    "normalize_work_names",
]

LANE_NAME_PATTERN: Final[str] = r"^[a-z0-9][a-z0-9_.:-]{0,127}$"
"""A lane name after normalisation."""

SURFACE_NAME_PATTERN: Final[str] = r"^[a-z0-9.][a-z0-9_.:-]{0,127}$"
"""A proof-surface name after normalisation."""


def normalize_work_name(name: str) -> str:
    """The one spelling of a lane or surface name: stripped and lower-cased."""
    return name.strip().lower()


def normalize_work_names(raw: object) -> object:
    """Normalise every string in a collection of names, before the pattern check.

    Anything that is not a collection is returned unchanged, so pydantic
    reports the type error itself.
    """
    if isinstance(raw, (set, frozenset, list, tuple)):
        return frozenset(
            normalize_work_name(name) if isinstance(name, str) else name for name in raw
        )
    return raw
