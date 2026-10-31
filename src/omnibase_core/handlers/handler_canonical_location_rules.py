# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure TypeScript/React and shell location rules for canonical file shape."""

from __future__ import annotations

import re
from collections.abc import Iterable
from pathlib import PurePosixPath

from omnibase_core.models.validation.model_canonical_location_request import (
    ModelCanonicalLocationRequest,
)
from omnibase_core.models.validation.model_canonical_location_verdict import (
    ModelCanonicalLocationVerdict,
)

__all__ = ["HandlerCanonicalLocationRules", "TYPESCRIPT_EXTENSIONS"]

_WORDS = re.compile(r"\S+")

# OMN-21332: knowledge_base_internal/
# beta/plans/2026-10-23-canonical-shape-typescript-react-swift.md, rules T1-T17.
TYPESCRIPT_EXTENSIONS: frozenset[str] = frozenset(
    (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs")
)
TYPESCRIPT_SRC_EXTENSIONS: frozenset[str] = frozenset((".ts", ".tsx"))
TYPESCRIPT_TEST_DIRS: frozenset[str] = frozenset(("tests", "test", "__tests__", "e2e"))
TYPESCRIPT_SRC_DIRS: frozenset[str] = frozenset(
    _WORDS.findall(
        "components pages models api generated contracts handlers store theme"
    )
)
TYPESCRIPT_ENTRYPOINTS: frozenset[str] = frozenset(
    _WORDS.findall(
        "index main App middleware proxy instrumentation instrumentation-client"
    )
)
TYPESCRIPT_APP_NAMES: frozenset[str] = frozenset(
    _WORDS.findall(
        "page layout loading error not-found forbidden unauthorized route template default global-error global-not-found sitemap robots manifest icon apple-icon opengraph-image twitter-image"
    )
)
TYPESCRIPT_CONFIG_NAME = re.compile(r"^[^/]+\.(config|setup)\.(ts|js|mjs|cjs)$")
TYPESCRIPT_TEST_NAME = re.compile(r"\.(test|spec)\.(ts|tsx)$")
TYPESCRIPT_HOOK_NAME = re.compile(r"^(use[A-Z][A-Za-z0-9]*|index)\.(ts|tsx)$")
SHELL_EXTENSIONS: frozenset[str] = frozenset((".sh", ".bash", ".zsh"))
SHELL_SHEBANG = re.compile(
    rb"^#![ \t]*(?:\S*/)?(?:env[ \t]+(?:-S[ \t]+)?(?:\S*/)?)?"
    rb"(?:sh|bash|zsh|dash|ksh)(?:[ \t]|$)"
)


def _suffix(path: str) -> str:
    return PurePosixPath(path).suffix.lower()


def _is_shell_script(path: str, head_bytes: bytes | None) -> bool:
    """A shell suffix, or an extensionless file with a shell interpreter shebang."""
    suffix = _suffix(path)
    if suffix in SHELL_EXTENSIONS:
        return True
    if suffix or not head_bytes:
        return False
    first_line = head_bytes.split(b"\n", 1)[0].rstrip(b"\r")
    return SHELL_SHEBANG.match(first_line) is not None


def _is_typescript_src_location(parts: tuple[str, ...]) -> bool:
    """Check a path relative to a workspace's src directory."""
    name = parts[-1]
    if TYPESCRIPT_TEST_NAME.search(name):
        return True
    stem = PurePosixPath(name).stem
    if len(parts) == 1:
        return stem in TYPESCRIPT_ENTRYPOINTS or name.endswith(".d.ts")
    if parts[0] == "app":
        return stem in TYPESCRIPT_APP_NAMES
    if parts[0] == "hooks":
        return len(parts) == 2 and TYPESCRIPT_HOOK_NAME.fullmatch(name) is not None
    return parts[0] in TYPESCRIPT_SRC_DIRS


def _typescript_workspace_roots(files: Iterable[str]) -> frozenset[str]:
    """Workspace directories with tracked package.json files at permitted depths."""
    roots = set[str]()
    for path in files:
        parts = PurePosixPath(path).parts
        if not parts or parts[-1] != "package.json":
            continue
        if (
            (len(parts) == 2 and parts[0] != "src")
            or (
                len(parts) == 3
                and parts[0] == "packages"
                and not parts[1].startswith("@")
            )
            or (
                len(parts) == 4
                and parts[0] == "packages"
                and parts[1].startswith("@")
                and len(parts[1]) > 1
            )
        ):
            roots.add("/".join(parts[:-1]))
    return frozenset(roots)


def _is_typescript_canonical_location(
    path: str, workspace_roots: frozenset[str]
) -> bool:
    """TypeScript/React locations, trying each permitted workspace prefix."""
    parts = PurePosixPath(path).parts
    if not parts or _suffix(path) not in TYPESCRIPT_EXTENSIONS:
        return False
    if parts[0] == "docs" or any(part in TYPESCRIPT_TEST_DIRS for part in parts[:-1]):
        return True
    prefix_lengths = [0]
    if parts[0] != "src":
        prefix_lengths.append(1)
    if len(parts) >= 3 and parts[0] == "packages":
        prefix_lengths.append(3 if parts[1].startswith("@") else 2)
    for length in prefix_lengths:
        if length and "/".join(parts[:length]) not in workspace_roots:
            continue
        relative = parts[length:]
        if len(relative) == 1 and (
            TYPESCRIPT_CONFIG_NAME.fullmatch(relative[0])
            or relative[0] == "next-env.d.ts"
        ):
            return True
        if len(relative) == 2 and relative[0] == ".storybook":
            return True
        if (
            len(relative) >= 2
            and relative[0] == "src"
            and _suffix(path) in TYPESCRIPT_SRC_EXTENSIONS
            and _is_typescript_src_location(relative[1:])
        ):
            return True
    return False


class HandlerCanonicalLocationRules:
    """Answers the canonical-location questions about one path from the request alone."""

    def handle(
        self, request: ModelCanonicalLocationRequest
    ) -> ModelCanonicalLocationVerdict:
        """Derive the workspace roots, then judge the request's path, if it names one."""
        roots = request.workspace_roots | _typescript_workspace_roots(
            request.tracked_files
        )
        path = request.path
        if path is None:
            return ModelCanonicalLocationVerdict(workspace_roots=roots)
        return ModelCanonicalLocationVerdict(
            workspace_roots=roots,
            is_shell_script=_is_shell_script(path, request.head_bytes),
            is_typescript_canonical_location=_is_typescript_canonical_location(
                path, roots
            ),
        )
