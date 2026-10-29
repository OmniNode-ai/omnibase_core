# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The checkout itself passes the canonical-file-shape ratchet (OMN-21515)."""

from __future__ import annotations

from pathlib import Path

from omnibase_core.nodes.node_canonical_file_shape_check_compute.runtime_canonical_file_shape_check import (
    main,
)
from omnibase_core.validators.no_unguarded_git_subprocess import (
    scrub_git_location_env,
)

REPO_ROOT = Path(__file__).resolve().parents[4]


def test_the_checkout_passes_the_file_shape_ratchet_with_no_handler_outside_a_node() -> (
    None
):
    """A handler no node contract binds is refused; the checkout must hold none outside the baseline."""
    assert main(["--repo-root", str(REPO_ROOT)], env=scrub_git_location_env()) == 0
