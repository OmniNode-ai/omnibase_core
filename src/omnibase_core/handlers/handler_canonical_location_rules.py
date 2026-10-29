# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure Python, TypeScript/React and shell location rules for canonical file shape."""

from __future__ import annotations

import re
from collections.abc import Iterable
from pathlib import PurePosixPath

CANONICAL_SRC_DIRS: frozenset[str] = frozenset(
    ("nodes", "handlers", "models", "protocols", "contracts", "enums")
)
VALIDATION_DIR = "validation"
GENERIC_VALIDATOR_FILE = re.compile(r"^(checker|validator)_[a-z0-9_]+\.py$")

# The generic validator format (OMN-21498): a pure checker and a ValidatorBase entry sit
# directly in src/<pkg>/validation/, beside the contract that carries their rule data.
GENERIC_VALIDATOR_PREFIXES: tuple[str, ...] = ("checker_", "validator_")


def is_python_canonical_src_location(parts: tuple[str, ...]) -> bool:
    """True for src/<pkg>/<canonical dir>/... and the generic validator format files."""
    if len(parts) < 4 or parts[0] != "src":
        return False
    if parts[2] in CANONICAL_SRC_DIRS:
        return True
    return (
        len(parts) == 4
        and parts[2] == "validation"
        and parts[3].startswith(GENERIC_VALIDATOR_PREFIXES)
    )


# OMN-21332: knowledge_base_internal/
# beta/plans/2026-10-23-canonical-shape-typescript-react-swift.md, rules T1-T17.
TYPESCRIPT_EXTENSIONS: frozenset[str] = frozenset(
    (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs")
)
TYPESCRIPT_SRC_EXTENSIONS: frozenset[str] = frozenset((".ts", ".tsx"))
TYPESCRIPT_TEST_DIRS: frozenset[str] = frozenset(("tests", "test", "__tests__", "e2e"))
TYPESCRIPT_SRC_DIRS: frozenset[str] = frozenset(
    (
        "components",
        "pages",
        "models",
        "api",
        "generated",
        "contracts",
        "handlers",
        "store",
        "theme",
    )
)
TYPESCRIPT_ENTRYPOINTS: frozenset[str] = frozenset(
    (
        "index",
        "main",
        "App",
        "middleware",
        "proxy",
        "instrumentation",
        "instrumentation-client",
    )
)
TYPESCRIPT_APP_NAMES: frozenset[str] = frozenset(
    (
        "page",
        "layout",
        "loading",
        "error",
        "not-found",
        "forbidden",
        "unauthorized",
        "route",
        "template",
        "default",
        "global-error",
        "global-not-found",
        "sitemap",
        "robots",
        "manifest",
        "icon",
        "apple-icon",
        "opengraph-image",
        "twitter-image",
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


def is_python_src_location(parts: tuple[str, ...]) -> bool:
    """A canonical src/<pkg>/ directory, or a generic-format validator file.

    The generic validator format (RULING 2026-10-28T13:48:11Z) is
    ``src/<pkg>/validation/checker_<id>.py`` and ``validator_<id>.py``.
    """
    if len(parts) == 4 and parts[0] == "src" and parts[2] == VALIDATION_DIR:
        return GENERIC_VALIDATOR_FILE.fullmatch(parts[3]) is not None
    return len(parts) >= 4 and parts[0] == "src" and parts[2] in CANONICAL_SRC_DIRS


def _suffix(path: str) -> str:
    return PurePosixPath(path).suffix.lower()


def is_shell_script(path: str, head_bytes: bytes | None) -> bool:
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


def typescript_workspace_roots(files: Iterable[str]) -> frozenset[str]:
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


def is_typescript_canonical_location(
    path: str, workspace_roots: frozenset[str] = frozenset()
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


def typescript_noncanonical_file_reason() -> str:
    """Explain the permitted TypeScript/React locations."""
    return (
        "new TypeScript/React code file outside a canonical location: "
        "tests/, test/, __tests__/, e2e/, docs/; workspace root config/setup "
        "files, next-env.d.ts and direct .storybook/ files (non-root workspaces "
        "require a tracked package.json); .ts/.tsx under workspace src/: "
        "test/spec files, root {index,main,App,middleware,proxy,instrumentation,"
        "instrumentation-client} or *.d.ts, "
        "app/**/{page,layout,loading,error,not-found,forbidden,unauthorized,route,"
        "template,default,global-error,global-not-found,sitemap,robots,manifest,"
        "icon,apple-icon,opengraph-image,twitter-image}, "
        "hooks/{use[A-Z]*,index}, "
        "{components,pages,models,api,generated,contracts,handlers,store,theme}/** "
        "(OMN-21332)."
    )
