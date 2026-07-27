# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelExtraForbidFinding — finding from the ``extra="forbid"`` ratchet (OMN-14515)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

# Resolution statuses. Only EXPLICIT_FORBID is compliant; everything else — including
# IMPLICIT_DEFAULT (no model_config at all) — is a violation, because Pydantic's own
# default for an undeclared `extra` is "ignore", i.e. silent field-dropping.
STATUS_EXPLICIT_FORBID = "EXPLICIT_FORBID"
STATUS_EXPLICIT_IGNORE = "EXPLICIT_IGNORE"
STATUS_EXPLICIT_ALLOW = "EXPLICIT_ALLOW"
STATUS_IMPLICIT_DEFAULT = "IMPLICIT_DEFAULT"
STATUS_UNRESOLVED = "UNRESOLVED"

# Which engine produced the verdict. Runtime introspection reads the real, MRO-merged
# `cls.model_config` and is authoritative; static AST is the fallback for files that
# cannot be imported.
ENGINE_RUNTIME = "runtime"
ENGINE_STATIC = "static"

_STATUS_EXPLANATION: dict[str, str] = {
    STATUS_EXPLICIT_IGNORE: 'declares extra="ignore" (unknown fields are silently dropped)',
    STATUS_EXPLICIT_ALLOW: 'declares extra="allow" (unknown fields land untyped in model_extra)',
    STATUS_IMPLICIT_DEFAULT: (
        "declares no extra= anywhere in its own config or any base — Pydantic's "
        'default is extra="ignore", so unknown fields are silently dropped'
    ),
    STATUS_UNRESOLVED: (
        "effective extra= could not be resolved (unresolvable base class); declare "
        'extra="forbid" explicitly on the model itself'
    ),
}


@dataclass(frozen=True, slots=True)
class ModelExtraForbidFinding:
    """A Pydantic model whose effective ``extra`` does not resolve to ``"forbid"``."""

    path: Path
    line: int
    column: int
    class_name: str
    module: str
    status: str
    effective_extra: str | None
    engine: str

    @property
    def fqn(self) -> str:
        """Fully-qualified ``module:ClassName`` identity used by the baseline."""
        return f"{self.module}:{self.class_name}"

    @property
    def is_violation(self) -> bool:
        return self.status != STATUS_EXPLICIT_FORBID

    def format(self) -> str:
        reason = _STATUS_EXPLANATION.get(self.status, self.status)
        return (
            f"{self.path}:{self.line}:{self.column + 1}: {self.class_name} "
            f"{reason} [{self.status}, via {self.engine}]; fqn: {self.fqn}"
        )
