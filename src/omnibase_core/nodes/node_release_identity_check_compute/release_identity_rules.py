# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure version parsing, tag selection and legacy CLI text."""

from typing import Final

from packaging.version import InvalidVersion, Version

from omnibase_core.models.nodes.release_identity_check.model_release_identity_check_input import (
    ModelReleaseIdentityCheckInput,
)

VALIDATOR_ID: Final[str] = "check-release-identity"


def version_error(request: ModelReleaseIdentityCheckInput) -> str | None:
    """Return the core script's configuration diagnostic verbatim."""
    raw = request.pyproject_version_raw
    if not raw:
        return f"ERROR: no project.version in {request.pyproject_path}"
    try:
        Version(str(raw))
    except InvalidVersion as exc:
        display = request.pyproject_version_repr or repr(raw)
        return f"ERROR: malformed project.version {display}: {exc}"
    return None


def latest_published_version(tags: tuple[str, ...]) -> Version | None:
    """Skip non-version tags and choose the maximum PEP 440 version."""
    best: Version | None = None
    for line in tags:
        tag = line.strip()
        candidate = tag[1:] if tag.startswith("v") else tag
        try:
            version = Version(candidate)
        except InvalidVersion:
            continue
        if best is None or version > best:
            best = version
    return best


def packaged_source_changed(paths: tuple[str, ...] | None) -> bool:
    """Undetermined changes enforce the invariant; known empty changes exempt."""
    return paths is None or any(path.startswith("src/") for path in paths)


def success_message(request: ModelReleaseIdentityCheckInput) -> str:
    """Render an already validated PASS using the original core text."""
    latest = latest_published_version(request.published_tags)
    if latest is None:
        return "OK: no published tag yet — release-identity bump not required."
    version = Version(str(request.pyproject_version_raw))
    if not packaged_source_changed(request.changed_files):
        return (
            "OK: no packaged src/** change in this diff — version bump not required "
            f"(pyproject {version}, latest published {latest})."
        )
    return f"OK: version {version} is ahead of latest published {latest}."
