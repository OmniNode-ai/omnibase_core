# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""CI guard: omnibase-core must not hard-depend on other OmniNode repos.

Internal packages belong in [project.optional-dependencies] so that
omnibase-core can be installed as a standalone SDK.

Exception -- ``omnibase-compat``: per ``omni_home/CLAUDE.md`` section 7 (repo
layering ``compat -> core -> spi -> infra``), ``omnibase_compat`` is the
designated shared substrate every OmniNode repo is allowed to hard-depend on.
It is the ONLY OmniNode package ``omnibase_core`` may list in
``[project.dependencies]``. All other OmniNode packages (spi, infra,
intelligence, memory, claude, change-control, onex-change-control,
omninode-infra) must remain in optional-dependencies so core stays
installable as a standalone SDK.
"""

import tomllib
from pathlib import Path

import pytest

OMNINODE_PACKAGES = {
    "omnibase-spi",
    "omnibase-infra",
    "omninode-intelligence",
    "omninode-memory",
    "omninode-claude",
    "onex-change-control",
    "omninode-infra",
}


@pytest.mark.unit
def test_no_internal_repo_hard_dependencies() -> None:
    """Ensure no OmniNode packages appear in [project.dependencies]."""
    pyproject = Path(__file__).parents[2] / "pyproject.toml"
    with open(pyproject, "rb") as f:
        data = tomllib.load(f)
    deps = data["project"]["dependencies"]
    dep_names = {
        d.split(">=")[0].split("==")[0].split("<")[0].split("[")[0].strip().lower()
        for d in deps
    }
    violations = dep_names & {p.lower() for p in OMNINODE_PACKAGES}
    assert not violations, (
        f"omnibase-core hard-depends on internal OmniNode packages: {violations}. "
        f"Move to [project.optional-dependencies]."
    )


@pytest.mark.unit
def test_optional_deps_are_documented() -> None:
    """Every internal optional dep must appear in the 'full' extra."""
    pyproject = Path(__file__).parents[2] / "pyproject.toml"
    with open(pyproject, "rb") as f:
        data = tomllib.load(f)
    optional = data["project"].get("optional-dependencies", {})
    full_deps = {
        d.split(">=")[0].split("==")[0].strip().lower()
        for d in optional.get("full", [])
    }
    for group_name, group_deps in optional.items():
        if group_name == "full":
            continue
        for dep in group_deps:
            dep_name = dep.split(">=")[0].split("==")[0].split("<")[0].strip().lower()
            if dep_name in {p.lower() for p in OMNINODE_PACKAGES}:
                assert dep_name in full_deps, (
                    f"Internal package '{dep_name}' in optional group '{group_name}' "
                    f"is not listed in the 'full' extra."
                )
