# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Bounded git tag inventory EFFECT; every external dependency is request data."""

from __future__ import annotations

import re
import subprocess

from omnibase_core.models.validation.model_first_party_tag_inventory_request import (
    ModelFirstPartyTagInventoryRequest,
)
from omnibase_core.models.validation.model_first_party_tag_inventory_result import (
    ModelFirstPartyTagInventoryResult,
)
from omnibase_core.validators.no_unguarded_git_subprocess import scrub_git_location_env


class NodeFirstPartyTagInventoryEffect:
    """Read tags from a remote repository or a caller-supplied local clone URL."""

    def handle(
        self, request: ModelFirstPartyTagInventoryRequest
    ) -> ModelFirstPartyTagInventoryResult:
        """List matching tags, ignoring duplicates and annotated-tag peel rows."""
        policy = request.policy
        url = policy.url_template.format(org=policy.github_org, repo=request.repo)
        result = subprocess.run(
            [policy.git_binary, *(arg.format(url=url) for arg in policy.tag_arguments)],
            check=True,
            capture_output=True,
            text=True,
            timeout=policy.timeout_seconds,
            env=scrub_git_location_env(),
        )
        tags: set[str] = set()
        for line in result.stdout.splitlines():
            fields = line.split()
            if len(fields) != 2:
                continue
            name = fields[1]
            if name.startswith(policy.tag_prefix) and not name.endswith(
                policy.peeled_suffix
            ):
                tag = name.removeprefix(policy.tag_prefix)
                if re.fullmatch(policy.tag_pattern, tag):
                    tags.add(tag)
        return ModelFirstPartyTagInventoryResult(
            repo=request.repo, tags=tuple(sorted(tags))
        )
