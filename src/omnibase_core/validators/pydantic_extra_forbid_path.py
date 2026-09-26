# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Path-to-module resolution for the Pydantic ``extra=forbid`` gate."""

from pathlib import Path


def module_for_path(path: Path) -> tuple[str, Path]:
    """Return the dotted module name and import root for ``path``."""
    resolved = path.resolve()
    parts_list = resolved.parts
    src_indices = [i for i, part in enumerate(parts_list) if part == "src"]

    if src_indices:
        root = Path(*parts_list[: src_indices[-1] + 1])
        parts = list(parts_list[src_indices[-1] + 1 : -1])
    else:
        parts = []
        directory = resolved.parent
        while (directory / "__init__.py").exists():
            parts.insert(0, directory.name)
            directory = directory.parent
        root = directory

    if resolved.stem != "__init__":
        parts.append(resolved.stem)
    return ".".join(parts), root


__all__ = ["module_for_path"]
