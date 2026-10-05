# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Core link rules evaluated against typed path and anchor inventory."""

import posixpath
import re
from pathlib import PurePosixPath
from urllib.parse import unquote

from omnibase_core.models.nodes.markdown_links_check.model_markdown_link import (
    ModelMarkdownLink,
)
from omnibase_core.models.nodes.markdown_links_check.model_markdown_link_inventory_entry import (
    ModelMarkdownLinkInventoryEntry,
)
from omnibase_core.models.nodes.markdown_links_check.model_markdown_links_check_input import (
    ModelMarkdownLinksCheckInput,
)
from omnibase_core.models.validation.model_validation_finding import (
    ModelValidationFinding,
)

from .matcher_markdown_links import (
    extract_headings_as_anchors,
    extract_links_from_markdown,
    is_external_link,
    is_http_link,
    normalize_url_for_validation,
)

VALIDATOR_ID = "validate-markdown-links"


def target_key(source: str, url: str, root: str) -> str:
    """Preserve dot segments until the runtime resolves symlinks."""
    path = url.split("#", 1)[0]
    parent = (
        PurePosixPath(root) if path.startswith("/") else PurePosixPath(source).parent
    )
    return str(parent / path.lstrip("/"))


def internal_error(
    link: ModelMarkdownLink,
    request: ModelMarkdownLinksCheckInput,
    inventory: dict[str, ModelMarkdownLinkInventoryEntry],
) -> str | None:
    if link.is_missing_reference:
        return f"Reference-style link [{link.missing_reference_name}] has no definition"
    if link.url.startswith("#"):
        anchor = unquote(link.url[1:])
        source = next(
            file.source for file in request.files if file.path == link.source_file
        )
        if anchor not in extract_headings_as_anchors(source):
            return f"Anchor '{anchor}' not found in file"
        return None
    path_part, separator, raw_anchor = link.url.partition("#")
    if not path_part:
        return None
    anchor = unquote(raw_anchor) if separator else ""
    key = target_key(link.source_file, link.url, request.repo_root)
    entry = inventory.get(key)
    if entry is not None and entry.resolution_error is not None:
        return entry.resolution_error
    resolved = entry.resolved_path if entry else posixpath.normpath(key)
    root = request.repo_root.rstrip("/")
    if resolved != root and not resolved.startswith(root + "/"):
        if request.cross_repo_root:
            cross_key = str(PurePosixPath(request.cross_repo_root) / path_part)
            cross = inventory.get(cross_key)
            if cross and cross.exists and cross.resolution_error is None:
                if (
                    anchor
                    and PurePosixPath(cross.resolved_path).suffix.lower() == ".md"
                    and anchor not in cross.anchors
                ):
                    return f"Anchor '{anchor}' not found in {path_part}"
                return None
        return f"Link points outside repository: {resolved}"
    if entry is None or not entry.exists:
        implicit = inventory.get(resolved + ".md")
        if implicit is None or not implicit.exists:
            return f"Target file not found: {path_part}"
        entry = implicit
    if (
        anchor
        and PurePosixPath(entry.resolved_path).suffix.lower() == ".md"
        and anchor not in entry.anchors
    ):
        return f"Anchor '{anchor}' not found in {path_part}"
    return None


def analyze(
    request: ModelMarkdownLinksCheckInput,
) -> tuple[list[ModelValidationFinding], int, int, list[str]]:
    """Return findings, counters and original verbose diagnostics deterministically."""
    inventory = {entry.path: entry for entry in request.inventory}
    patterns = [re.compile(pattern) for pattern in request.config.ignore_patterns]
    findings: list[ModelValidationFinding] = []
    checked = skipped = 0
    verbose: list[str] = []
    for file in request.files:
        relative = str(PurePosixPath(file.path).relative_to(request.repo_root))
        verbose.append(f"Checking: {relative}")
        for link in extract_links_from_markdown(file.source, file.path):
            if any(pattern.search(link.url) for pattern in patterns):
                skipped += 1
                verbose.append(f"  Skipped (ignored): {link.url}")
                continue
            checked += 1
            error: str | None = None
            external = is_external_link(link.url)
            unavailable = False
            if external:
                if not request.config.check_external:
                    skipped += 1
                    verbose.append(f"  Skipped (external): {link.url}")
                elif not is_http_link(link.url):
                    skipped += 1
                    verbose.append(f"  Skipped (non-HTTP scheme): {link.url}")
                else:
                    url = normalize_url_for_validation(link.url)
                    unavailable = url not in request.external_results
                    error = request.external_results.get(url)
                    if unavailable:
                        error = "External HTTP validation requires an external network EFFECT"
                    verbose.append(
                        f"  BROKEN (external): {link.url} - {error}"
                        if error
                        else f"  OK (external): {link.url}"
                    )
            else:
                error = internal_error(link, request, inventory)
                verbose.append(
                    f"  BROKEN: {link.display_link} - {error}"
                    if error
                    else f"  OK: {link.display_link}"
                )
            if error:
                rule = (
                    "external-link"
                    if external
                    else (
                        "missing-reference"
                        if link.is_missing_reference
                        else "internal-link"
                    )
                )
                findings.append(
                    ModelValidationFinding(
                        validator_id=VALIDATOR_ID,
                        severity="ERROR" if unavailable else "FAIL",
                        rule_id=rule,
                        location=f"{file.path}:{link.line_number}",
                        message=error,
                        evidence={
                            "target": link.url,
                            "display_link": link.display_link,
                        },
                    )
                )
    return findings, checked, skipped, verbose
