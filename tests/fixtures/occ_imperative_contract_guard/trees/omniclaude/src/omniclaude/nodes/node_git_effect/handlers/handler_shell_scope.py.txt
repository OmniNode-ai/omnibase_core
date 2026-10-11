# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Command environment scope split out of handler_shell_words for OMN-20685."""

from __future__ import annotations

from collections.abc import Iterator, Mapping


class Scope(Mapping[str, str | None]):
    """Environment overlaid by the command's own assignments."""

    def __init__(self, env: Mapping[str, str], local: Mapping[str, str | None]):
        self._env, self._local = env, local

    def __getitem__(self, key: str) -> str | None:
        return self._local[key] if key in self._local else self._env[key]

    def __iter__(self) -> Iterator[str]:
        yield from self._local
        yield from (k for k in self._env if k not in self._local)

    def __len__(self) -> int:
        return len(set(self._env) | set(self._local))
