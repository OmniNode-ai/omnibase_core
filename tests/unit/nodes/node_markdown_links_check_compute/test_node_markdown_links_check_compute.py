# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Direct typed handler parity without filesystem access."""

import pytest

from omnibase_core.models.nodes.markdown_links_check.model_markdown_link_config import (
    ModelMarkdownLinkConfig,
)
from omnibase_core.models.nodes.markdown_links_check.model_markdown_link_inventory_entry import (
    ModelMarkdownLinkInventoryEntry,
)
from omnibase_core.models.nodes.markdown_links_check.model_markdown_links_check_input import (
    ModelMarkdownLinksCheckInput,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile
from omnibase_core.nodes.node_markdown_links_check_compute.handler import (
    NodeMarkdownLinksCheckCompute,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("source", "message"),
    [
        ("[bad](gone.md)", "Target file not found: gone.md"),
        ("[bad](#gone)", "Anchor 'gone' not found in file"),
        ("[bad][ref]", "Reference-style link [ref] has no definition"),
        ("[bad](../gone.md)", "Link points outside repository: /gone.md"),
    ],
)
def test_parity_handler_matching(source: str, message: str) -> None:
    request = ModelMarkdownLinksCheckInput(
        repo_root="/repo",
        files=(ModelSourceFile(path="/repo/README.md", source=source),),
    )
    report = NodeMarkdownLinksCheckCompute().handle(request)
    assert len(report.findings) == 1
    assert report.findings[0].message == message
    assert report.findings[0].location == "/repo/README.md:1"


def test_parity_handler_inventory_anchors() -> None:
    request = ModelMarkdownLinksCheckInput(
        repo_root="/repo",
        files=(
            ModelSourceFile(
                path="/repo/README.md",
                source="[yes](target.md#good) [no](target.md#bad)",
            ),
        ),
        inventory=(
            ModelMarkdownLinkInventoryEntry(
                path="/repo/target.md",
                resolved_path="/repo/target.md",
                exists=True,
                anchors=("good",),
            ),
        ),
    )
    report = NodeMarkdownLinksCheckCompute().handle(request)
    assert [finding.message for finding in report.findings] == [
        "Anchor 'bad' not found in target.md"
    ]


@pytest.mark.parametrize(
    "message",
    [
        "Cannot resolve path (possible circular symlink): test resolution",
        "Cannot check if target exists (permission error?): test permissions",
    ],
)
def test_parity_handler_filesystem_error_inventory(message: str) -> None:
    request = ModelMarkdownLinksCheckInput(
        repo_root="/repo",
        files=(ModelSourceFile(path="/repo/README.md", source="[bad](target.md)"),),
        inventory=(
            ModelMarkdownLinkInventoryEntry(
                path="/repo/target.md",
                resolved_path="/repo/target.md",
                exists=False,
                resolution_error=message,
            ),
        ),
    )
    report = NodeMarkdownLinksCheckCompute().handle(request)
    assert report.findings[0].message == message


def test_parity_handler_external_facts() -> None:
    request = ModelMarkdownLinksCheckInput(
        repo_root="/repo",
        files=(
            ModelSourceFile(
                path="/repo/README.md",
                source="[yes](//example.com/good) [no](https://example.com/bad)",
            ),
        ),
        config=ModelMarkdownLinkConfig(check_external=True),
        external_results={
            "https://example.com/good": None,
            "https://example.com/bad": "HTTP 404",
        },
    )
    report = NodeMarkdownLinksCheckCompute().handle(request)
    assert [
        (finding.message, finding.evidence["target"]) for finding in report.findings
    ] == [("HTTP 404", "https://example.com/bad")]
