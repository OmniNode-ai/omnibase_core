# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Scan inputs of check-hardcoded-model-config-compute: files, git reads, literal rules, report.

The I/O the runtime hands to the pure handler (OMN-19252, OMN-21537): which files are
scanned, the tracked-file list and the baseline as git holds it, the rule rows and
repository facts of families O, G, F, P, S, H and B, and the canonical validation report
written through the container's report writer.
"""

from __future__ import annotations

import subprocess
from collections import Counter
from collections.abc import Callable
from importlib import resources
from importlib.resources.abc import Traversable

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.dependency_direction.model_repo_layer_map import (
    ModelRepoLayerMap,
)
from omnibase_core.models.validation.model_hardcoded_literal_rule_set import (
    ModelHardcodedLiteralRuleSet,
)
from omnibase_core.models.version_drift.model_internal_sibling_pins_contract import (
    ModelInternalSiblingPinsContract,
)
from omnibase_core.utils.util_safe_yaml_loader import load_yaml_content_as_model
from omnibase_core.validation.checker_hardcoded_model_literals import load_rule_set
from omnibase_core.validation.checker_hardcoded_model_views import file_suffix
from omnibase_core.validation.checker_rule_parameters import rule_string
from omnibase_core.validation.hardcoded_model_config.handler import content_sha1
from omnibase_core.validation.hardcoded_model_config.models import (
    ModelHardcodedModelConfigBaselineEntry,
    ModelHardcodedModelConfigPolicy,
)
from omnibase_core.validation.validator_hardcoded_model_literals import (
    ValidatorHardcodedModelLiterals,
)

__all__ = [
    "InputError",
    "is_scanned",
    "load_literal_rule_set",
    "read_baseline_at_ref",
    "read_file_at_ref",
    "split_growth",
    "tracked_files",
    "unjudged_families",
]


class InputError(Exception):
    """An input the gate cannot read. The gate fails closed on it."""


def unjudged_families(
    policy: ModelHardcodedModelConfigPolicy,
    literals: ModelHardcodedLiteralRuleSet | None = None,
) -> frozenset[str]:
    """Families this run cannot detect, whose baseline entries it must not judge.

    D needs the private vocabulary's lab hosts or ports; H needs its lab hosts; G needs
    the first-party organisation and P the registry repositories; a family whose rule
    row is disabled judges nothing.
    """
    unjudged: set[str] = set()
    if not (policy.lab_host_names or policy.lab_ports):
        unjudged.add("D")
    literal_families = frozenset("OGFPSHB")
    if literals is None:
        return frozenset(unjudged | literal_families)
    unjudged |= literal_families - literals.families()
    if not literals.g_org:
        unjudged.add("G")
    if not literals.p_names:
        unjudged.add("P")
    if not literals.h_host_names:
        unjudged.add("H")
    return frozenset(unjudged)


def read_package_text(root: Traversable, relative: str) -> str:
    node = root
    for part in relative.split("/"):
        node = node.joinpath(part)
    try:
        return node.read_text("utf-8")
    except OSError as exc:
        raise InputError(f"{relative}: unreadable: {exc}") from exc


def load_literal_rule_set(
    policy: ModelHardcodedModelConfigPolicy, root: Traversable | None = None
) -> ModelHardcodedLiteralRuleSet:
    """Read the rule rows of families O, G, F, P, S, H and B and the three facts they use.

    The rows are ``validation/contracts/hardcoded_model_literals.validation.yaml``; the
    organisation and the registry repositories come from the package contracts the G and
    P rows name, the lab hosts from ``policy`` (the private vocabulary). An invalid
    contract raises ``InputError`` instead of passing.
    """
    try:
        contract = ValidatorHardcodedModelLiterals().contract
        rules = contract.rules
        by_family = {rule_string(rule, "family"): rule for rule in rules}
        package = root or resources.files("omnibase_core")
        organisation = load_yaml_content_as_model(
            read_package_text(package, rule_string(by_family["G"], "org_contract")),
            ModelInternalSiblingPinsContract,
        ).github_org
        layer_map = load_yaml_content_as_model(
            read_package_text(
                package, rule_string(by_family["P"], "registry_contract")
            ),
            ModelRepoLayerMap,
        )
        return load_rule_set(
            rules,
            github_org=organisation,
            repository_names=[entry.repo for entry in layer_map.repos],
            host_names=policy.lab_host_names,
            python_suffixes=policy.python_suffixes,
            slash_comment_suffixes=policy.slash_comment_suffixes,
            no_comment_suffixes=policy.no_comment_suffixes,
            exclude_patterns=contract.exclude_patterns,
        )
    except (ModelOnexError, ValueError, KeyError) as exc:
        raise InputError(
            f"hardcoded_model_literals contract is invalid: {exc}"
        ) from exc


def is_scanned(path: str, policy: ModelHardcodedModelConfigPolicy) -> bool:
    """Whether the gate scans ``path``: its name or suffix is one the policy lists."""
    name = path.rsplit("/", 1)[-1]
    if name in policy.scanned_names or name.startswith(".env"):
        return True
    return file_suffix(path) in policy.scanned_suffixes


def tracked_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "-z"], capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        raise InputError(f"git ls-files failed: {result.stderr.strip()}")
    return [p for p in result.stdout.split("\0") if p]


def read_baseline_at_ref(ref: str, path: str) -> str | None:
    """Return the baseline text at ``ref``, or None when the file is absent there.

    An unresolvable ref is an error, never an absent file.
    """
    verify = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"],
        capture_output=True,
        text=True,
        check=False,
    )
    if verify.returncode != 0:
        raise InputError(f"--base {ref!r} does not resolve to a commit")
    exists = subprocess.run(
        ["git", "cat-file", "-e", f"{ref}:{path}"],
        capture_output=True,
        text=True,
        check=False,
    )
    if exists.returncode != 0:
        return None
    show = subprocess.run(
        ["git", "show", f"{ref}:{path}"], capture_output=True, text=True, check=False
    )
    if show.returncode != 0:
        raise InputError(f"git show {ref}:{path} failed: {show.stderr.strip()}")
    return show.stdout


def read_file_at_ref(ref: str, path: str) -> str | None:
    """Return ``path``'s text at ``ref``, or None when it is absent there."""
    show = subprocess.run(
        ["git", "show", f"{ref}:{path}"], capture_output=True, text=True, check=False
    )
    return show.stdout if show.returncode == 0 else None


def split_growth(
    ref: str,
    grown: list[ModelHardcodedModelConfigBaselineEntry],
    head: list[ModelHardcodedModelConfigBaselineEntry],
    read_file: Callable[[str, str], str | None],
) -> tuple[
    list[ModelHardcodedModelConfigBaselineEntry],
    list[ModelHardcodedModelConfigBaselineEntry],
]:
    """Split grown entries into (lines that already stood at ``ref``, new lines).

    A grown entry is pre-existing only while its file at ``ref`` holds at least
    as many lines with its content hash as the head baseline lists for its key,
    so a copy of an old line that the change adds is still new.
    """
    head_counts = Counter(e.key() for e in head)
    at_ref: dict[str, Counter[str]] = {}
    old: list[ModelHardcodedModelConfigBaselineEntry] = []
    new: list[ModelHardcodedModelConfigBaselineEntry] = []
    for entry in grown:
        if entry.path not in at_ref:
            text = read_file(ref, entry.path) or ""
            at_ref[entry.path] = Counter(content_sha1(ln) for ln in text.splitlines())
        held = at_ref[entry.path][entry.content_sha1]
        (old if held >= head_counts[entry.key()] else new).append(entry)
    return old, new
