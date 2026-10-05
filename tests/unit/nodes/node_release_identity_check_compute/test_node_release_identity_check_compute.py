# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Direct typed-fact coverage of the core script's release invariant."""

import pytest

from omnibase_core.models.nodes.release_identity_check.model_release_identity_check_input import (
    ModelReleaseIdentityCheckInput,
)
from omnibase_core.nodes.node_release_identity_check_compute.handler import (
    NodeReleaseIdentityCheckCompute,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("version", "tags", "changed", "status"),
    [
        ("0.46.0", ("v0.45.0",), None, "PASS"),
        ("0.45.0", ("v0.45.0",), None, "FAIL"),
        ("0.44.0", ("v0.45.0",), None, "FAIL"),
        ("0.45.0", ("v0.45.0",), ("docs/foo.md",), "PASS"),
        ("0.45.0", ("v0.45.0",), ("src/foo.py",), "FAIL"),
        ("0.45.0", ("v0.45.0",), (), "PASS"),
        ("0.1.0", (), None, "PASS"),
        ("0.1.0", ("invalid",), None, "PASS"),
        ("1.2.9", ("v1.2.8", "1.2.10", "bad"), None, "FAIL"),
        ("1.2.0rc1", ("v1.2.0",), None, "FAIL"),
        (None, (), None, "ERROR"),
        ("", (), None, "ERROR"),
        ("banana", (), None, "ERROR"),
    ],
)
def test_parity_typed_facts(version, tags, changed, status):
    request = ModelReleaseIdentityCheckInput(
        pyproject_version_raw=version, published_tags=tags, changed_files=changed
    )
    report = NodeReleaseIdentityCheckCompute().handle(request)
    assert report.overall_status == status
    assert report.provenance.validators_run == ("check-release-identity",)
    if report.findings:
        assert report.findings[0].location == "pyproject.toml:1"
        assert report.findings[0].rule_id is not None


@pytest.mark.parametrize("version", ["0.1.0", "0.1.1", "0.1.1.post1", "1!0.1.1"])
def test_parity_core_tagless_tree(version):
    report = NodeReleaseIdentityCheckCompute().handle(
        ModelReleaseIdentityCheckInput(
            pyproject_version_raw=version,
        )
    )
    assert report.overall_status == "PASS"
    assert not report.findings


def test_parity_version_ahead_of_published_version():
    request = ModelReleaseIdentityCheckInput(
        pyproject_version_raw="0.1.2",
        published_tags=("v0.1.1",),
    )
    assert NodeReleaseIdentityCheckCompute().handle(request).overall_status == "PASS"


def test_parity_handler_is_deterministic():
    request = ModelReleaseIdentityCheckInput(
        pyproject_version_raw="0.45.0", published_tags=("v0.45.0",)
    )
    handler = NodeReleaseIdentityCheckCompute()
    first = handler.handle(request)
    second = handler.handle(request)
    assert first.findings == second.findings
    assert first.overall_status == second.overall_status
    assert first.metrics == second.metrics
