# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for architecture-handshakes/validator-requirements.yaml (OMN-9051).

This spec is the single source of truth for which validators every downstream
repo must have wired (pre-commit + CI + required-check). The handshake verifier
reads it and cross-references each downstream repo's config.

These tests lock the schema shape so changes to the spec cannot silently break
consumers. If you hit a failure here, read the comment at the top of the
schema file — the schema version MUST bump if you add/remove fields.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

SPEC_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "architecture-handshakes"
    / "validator-requirements.yaml"
)

# Minimum number of validators the DoD requires. The ticket asks for >= 10.
MIN_VALIDATORS = 10

REQUIRED_TOP_LEVEL_KEYS = {"schema_version", "required_validators", "metadata"}

REQUIRED_VALIDATOR_FIELDS = {
    "description",
    "central_source",
    "pre_commit",
    "ci_workflow",
    "required_check_on_main",
    "silent_skip_allowed",
    "excludes",
    "applies_to_repos",
    # OMN-9115: matcher fields used by the enforcement consumer so
    # .pre-commit-config.yaml / .github/workflows/*.yml scans are driven by
    # the spec rather than hardcoded in the consumer.
    "pre_commit_hook_ids",
    "ci_workflow_keywords",
}

VALID_SCOPE_VALUES = {"required", "optional"}

# Repos that are allowed as applies_to_repos targets. Keep in sync with
# omni_home/CLAUDE.md repository registry.
KNOWN_REPOS = {
    "omniclaude",
    "omnibase_compat",
    "omnibase_core",
    "omnibase_spi",
    "omnibase_infra",
    "omnidash",
    "omnimarket",
    "omniintelligence",
    "omnimemory",
    "omninode_infra",
    "omniweb",
    "onex_change_control",
}


@pytest.fixture(scope="module")
def spec() -> dict[str, Any]:
    assert SPEC_PATH.exists(), f"validator-requirements.yaml missing at {SPEC_PATH}"
    with SPEC_PATH.open() as fh:
        data = yaml.safe_load(fh)
    assert isinstance(data, dict), "spec root must be a mapping"
    return data


def test_top_level_schema_shape(spec: dict[str, Any]) -> None:
    """Spec file has exactly the top-level keys consumers expect."""
    assert set(spec.keys()) == REQUIRED_TOP_LEVEL_KEYS, (
        f"unexpected top-level keys: {set(spec.keys()) ^ REQUIRED_TOP_LEVEL_KEYS}"
    )


def test_schema_version_is_semver(spec: dict[str, Any]) -> None:
    """schema_version uses ModelSemVer mapping (major/minor/patch) per ONEX
    validator ``validate-string-versions`` — no string version literals."""
    version = spec["schema_version"]
    assert isinstance(version, dict), (
        f"schema_version must be a ModelSemVer mapping, got {type(version).__name__}"
    )
    assert set(version.keys()) == {"major", "minor", "patch"}, (
        f"schema_version keys must be {{major, minor, patch}}, got {set(version.keys())}"
    )
    for key, value in version.items():
        assert isinstance(value, int) and value >= 0, (
            f"schema_version.{key} must be a non-negative int, got {value!r}"
        )


def test_minimum_validator_count(spec: dict[str, Any]) -> None:
    """DoD: spec must enumerate at least 10 validators from the inventory."""
    validators = spec["required_validators"]
    assert isinstance(validators, dict), "required_validators must be a mapping"
    assert len(validators) >= MIN_VALIDATORS, (
        f"DoD requires >= {MIN_VALIDATORS} validators; found {len(validators)}"
    )


def test_every_validator_has_required_fields(spec: dict[str, Any]) -> None:
    """Each validator entry declares the full schema so the handshake verifier
    can rely on the fields being present without defensive defaults."""
    missing: dict[str, set[str]] = {}
    for name, entry in spec["required_validators"].items():
        entry_keys = set(entry.keys())
        gap = REQUIRED_VALIDATOR_FIELDS - entry_keys
        if gap:
            missing[name] = gap
    assert not missing, f"validators missing fields: {missing}"


def test_scope_fields_use_required_or_optional(spec: dict[str, Any]) -> None:
    for name, entry in spec["required_validators"].items():
        for scope_field in ("pre_commit", "ci_workflow"):
            value = entry[scope_field]
            assert value in VALID_SCOPE_VALUES, (
                f"{name}.{scope_field} must be one of {VALID_SCOPE_VALUES}, got {value!r}"
            )


def test_silent_skip_never_allowed(spec: dict[str, Any]) -> None:
    """feedback_no_informational_gates: every check blocks. Advisory modes are
    forbidden. The handshake must not tolerate a spec that opens a silent-skip
    escape hatch."""
    offenders = [
        name
        for name, entry in spec["required_validators"].items()
        if entry["silent_skip_allowed"] is not False
    ]
    assert not offenders, (
        f"silent_skip_allowed must be False for all validators; offenders: {offenders}"
    )


def test_required_check_context_is_string_or_null(spec: dict[str, Any]) -> None:
    for name, entry in spec["required_validators"].items():
        value = entry["required_check_on_main"]
        assert value is None or isinstance(value, str), (
            f"{name}.required_check_on_main must be str|None, got {type(value).__name__}"
        )


def test_excludes_shape(spec: dict[str, Any]) -> None:
    for name, entry in spec["required_validators"].items():
        excludes = entry["excludes"]
        assert isinstance(excludes, dict), f"{name}.excludes must be mapping"
        assert set(excludes.keys()) == {"allowed", "forbidden"}, (
            f"{name}.excludes must have exactly 'allowed' and 'forbidden' keys"
        )
        for bucket in ("allowed", "forbidden"):
            assert isinstance(excludes[bucket], list), (
                f"{name}.excludes.{bucket} must be a list"
            )
            for pat in excludes[bucket]:
                assert isinstance(pat, str), (
                    f"{name}.excludes.{bucket} entries must be strings"
                )


def test_applies_to_repos_is_all_or_known_list(spec: dict[str, Any]) -> None:
    """applies_to_repos is either the literal 'all' or a list of known repos.
    Unknown repo names silently skip coverage — this check blocks typos."""
    for name, entry in spec["required_validators"].items():
        value = entry["applies_to_repos"]
        if value == "all":
            continue
        assert isinstance(value, list), (
            f"{name}.applies_to_repos must be 'all' or a list, got {value!r}"
        )
        unknown = set(value) - KNOWN_REPOS
        assert not unknown, (
            f"{name}.applies_to_repos references unknown repos: {unknown}"
        )


def test_metadata_references_ticket(spec: dict[str, Any]) -> None:
    metadata = spec["metadata"]
    assert isinstance(metadata, dict), "metadata must be a mapping"
    related = metadata.get("related_tickets", [])
    assert "OMN-9051" in related, (
        "metadata.related_tickets must include OMN-9051 (this spec's owner)"
    )


def test_critical_validators_present(spec: dict[str, Any]) -> None:
    """Anchor check: these validators were flagged in the 2026-04-17 inventory
    as the blocking gaps. Removing any of them from the spec is a regression."""
    required_names = {
        "hardcoded-local-paths",
        "spdx-headers",
        "stub-implementations",
        "enum-governance",
        "naming-conventions",
        "mypy-type-check",
        "ruff-format-check",
        "detect-secrets",
    }
    present = set(spec["required_validators"].keys())
    missing = required_names - present
    assert not missing, f"critical validators missing from spec: {missing}"
