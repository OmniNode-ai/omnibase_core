# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Per-repository closure settings for the packaged test selector (OMN-14206).

The ``closure:`` block of a repository's selector policy YAML. It names the
trees the import-graph closure narrows within, the test-file name patterns it
collects, and the separately-gated prefixes it ignores, so omnibase_infra and
omnimarket set them in their own policy file instead of in code.

The defaults equal ``closure_selector.DEFAULT_*`` (pinned by
``test_config_defaults_match_the_packaged_selector_defaults``); this
module cannot import them, because models must not import from ``nodes``
(``.importlinter`` ``core-models-no-upward``).
"""

from __future__ import annotations

from pathlib import PurePosixPath

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_core import PydanticCustomError

__all__ = ["ModelClosureConfig"]


def _invalid(message: str) -> PydanticCustomError:
    # Pydantic reports this as a ValidationError, like a ValueError would be.
    return PydanticCustomError("closure_config", message)


def _normalize_dir(raw: str, *, what: str) -> str:
    """Repo-relative ``dir/`` form; a validation error for an empty/absolute/``..`` path."""
    if not raw or not raw.strip("/"):
        raise _invalid(f"{what} must be a non-empty relative path: {raw!r}")
    path = PurePosixPath(raw)
    if path.is_absolute() or ".." in path.parts:
        raise _invalid(f"{what} must be repo-relative with no '..': {raw!r}")
    normalized = path.as_posix().rstrip("/") + "/"
    return normalized[2:] if normalized.startswith("./") else normalized


def _dedup(items: list[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(items))


class ModelClosureConfig(BaseModel):
    """Where the closure looks for candidate tests in one repository."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    candidate_roots: tuple[str, ...] = Field(default=("tests/unit/",))
    test_file_patterns: tuple[str, ...] = Field(default=("test_*.py",))
    ignored_prefixes: tuple[str, ...] = Field(default=("tests/integration/",))

    @field_validator("candidate_roots")
    @classmethod
    def _check_roots(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        # An empty or malformed root must fail at load, never become an empty
        # candidate universe that "proves" no test is affected.
        roots = _dedup([_normalize_dir(r, what="candidate root") for r in value])
        if not roots:
            raise _invalid("at least one candidate root is required")
        for outer in roots:
            for inner in roots:
                if outer != inner and inner.startswith(outer):
                    raise _invalid(
                        f"candidate roots must not be nested: {inner!r} is inside {outer!r}"
                    )
        return roots

    @field_validator("test_file_patterns")
    @classmethod
    def _check_patterns(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value or any(not pattern for pattern in value):
            raise _invalid("test_file_patterns must be non-empty patterns")
        return _dedup(list(value))

    @field_validator("ignored_prefixes")
    @classmethod
    def _check_ignored(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return _dedup([_normalize_dir(p, what="ignored prefix") for p in value])

    @model_validator(mode="after")
    def _ignored_outside_roots(self) -> ModelClosureConfig:
        # The selector checks candidate roots first, so an ignored prefix
        # inside (or equal to) a root would silently never apply.
        for prefix in self.ignored_prefixes:
            for root in self.candidate_roots:
                if prefix.startswith(root) or root.startswith(prefix):
                    raise _invalid(
                        f"ignored prefix {prefix!r} overlaps candidate root {root!r}"
                    )
        return self
