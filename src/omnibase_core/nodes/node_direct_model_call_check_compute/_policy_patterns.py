# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Compiled policy patterns, the sanctioned-package test and name labels (OMN-20295)."""

from __future__ import annotations

import posixpath
import re
from dataclasses import dataclass
from functools import lru_cache

from omnibase_core.models.nodes.direct_model_call_check.model_direct_model_call_policy import (
    ModelDirectModelCallPolicy,
)


@dataclass(frozen=True)
class _Compiled:
    model_api_path: re.Pattern[str]
    provider_host: re.Pattern[str]
    base_url_identifier: re.Pattern[str]
    generic_base_url_identifier: re.Pattern[str]
    model_env_key: re.Pattern[str]


def _compile(policy: ModelDirectModelCallPolicy) -> _Compiled:
    return _compile_patterns(
        policy.model_api_path_pattern,
        policy.provider_host_pattern,
        policy.base_url_identifier_pattern,
        policy.generic_base_url_identifier_pattern,
        policy.model_env_key_pattern,
    )


@lru_cache(maxsize=8)
def _compile_patterns(
    model_api_path: str,
    provider_host: str,
    base_url_identifier: str,
    generic_base_url_identifier: str,
    model_env_key: str,
) -> _Compiled:
    return _Compiled(
        model_api_path=re.compile(model_api_path),
        provider_host=re.compile(provider_host),
        base_url_identifier=re.compile(base_url_identifier),
        generic_base_url_identifier=re.compile(generic_base_url_identifier),
        model_env_key=re.compile(model_env_key),
    )


@lru_cache(maxsize=256)
def _glob_regex(glob: str) -> re.Pattern[str]:
    out: list[str] = []
    i = 0
    while i < len(glob):
        if glob.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif glob.startswith("**", i):
            out.append(".*")
            i += 2
        elif glob[i] == "*":
            out.append("[^/]*")
            i += 1
        elif glob[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(glob[i]))
            i += 1
    return re.compile("^" + "".join(out) + "$")


def is_sanctioned(policy: ModelDirectModelCallPolicy, repo: str, path: str) -> bool:
    """True when ``path`` sits inside one of ``repo``'s sanctioned packages."""
    return any(
        _glob_regex(glob).match(path)
        for glob in policy.sanctioned_packages.get(repo, ())
    )


def _name_labels(
    compiled: _Compiled, name: str, env_key: bool = False
) -> frozenset[str]:
    """``base_url`` for a name of a model endpoint, ``base_url_weak`` for a
    plain base URL, nothing otherwise."""
    if compiled.base_url_identifier.search(name) or (
        env_key and compiled.model_env_key.search(name)
    ):
        return frozenset({"base_url"})
    if compiled.generic_base_url_identifier.search(name):
        return frozenset({"base_url_weak"})
    return frozenset()


def _program_name(text: str) -> str:
    stripped = text.strip().strip("'\"")
    return posixpath.basename(stripped)
