# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ValidatorRuntimeProfiles -- enforce runtime_profiles on command-consuming contracts.

Plan source: ``docs/plans/2026-04-26-runtime-lifecycle-hardening-plan.md`` (Task 4,
Wave 1 core). Linear: OMN-9886.

A node contract is "command-consuming" if its ``event_bus`` block subscribes
to at least one topic matching ``onex.cmd.*``. The validator fails when such
a contract has empty/absent ``runtime_profiles`` and the node id is not in
the explicit allowlist.

Three rules (OMN-9886 + OMN-12957):

- ``runtime_profiles_missing`` (OMN-9886) — a command-consuming contract that
  declares no ``runtime_profiles`` and is not allowlisted.
- ``runtime_profile_unregistered`` (OMN-12957) — a contract declares a
  ``runtime_profiles`` value not in the canonical
  ``omnibase_core.constants.constants_runtime_profiles.REGISTERED_RUNTIME_PROFILES``.
  A nonexistent profile name silently orphans the node: the runtime never wires
  its subscriptions to any process, so it has zero consumers and zero errors.
- ``runtime_profile_no_consumer_lane`` (OMN-12957) — a REDUCER or EFFECT
  contract that subscribes to topics but names *only* profiles that do not run
  a standalone consumer (``CONSUMER_ATTACHED_RUNTIME_PROFILES``). The name is
  registered (passes the subset check) but no process ever drains the
  subscriptions — the second, subtler class of silent orphaning flagged in
  operator review: manifest-declares-node ≠ consumer-attached.

Both contract shapes for ``runtime_profiles`` are accepted (mirrors the
canonical extractor in
``omnibase_infra.runtime.auto_wiring.discovery._extract_runtime_profiles``):

- top-level ``runtime_profiles: [str, ...]``
- ``descriptor.runtime_profiles: [str, ...]``

Both subscription shapes are accepted (Task 6 adds a typed parser; this
validator must not under-detect command consumers in the meantime):

- classic: ``event_bus.subscribe_topics: [str, ...]``
- nested: ``event_bus.subscribe: [{topic: str, ...}, ...]``

The base allowlist is loaded from
``src/omnibase_core/validation/runtime_profiles_allowlist.yaml``. When the
validator scans a consumer repo, it additionally discovers that repo's frozen
baseline allowlist at ``<repo>/validation/runtime_profiles_allowlist.yaml`` by
walking up from each scanned contract to the repo root (the directory holding
``pyproject.toml``). No environment variable is consulted — discovery is
deterministic from the contract path. The effective allowlist for a contract is
``the union of core_default and repo_baseline``. Every entry MUST carry a non-empty ``reason``
string; the loader raises on a blank reason so a "drop in to silence the gate"
PR cannot land. Per-call overrides via the ``allowlist`` constructor argument
are intended for tests (and disable repo discovery for isolation).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import ClassVar

import yaml

from omnibase_core.constants.constants_runtime_profiles import (
    CONSUMER_ATTACHED_RUNTIME_PROFILES,
    REGISTERED_RUNTIME_PROFILES,
)
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.validation.validator_base import ValidatorBase
from omnibase_core.validation.validator_topic_suffix import TOPIC_PREFIX

RULE_RUNTIME_PROFILES_MISSING = "runtime_profiles_missing"
RULE_RUNTIME_PROFILE_UNREGISTERED = "runtime_profile_unregistered"
RULE_RUNTIME_PROFILE_NO_CONSUMER_LANE = "runtime_profile_no_consumer_lane"
ALLOWLIST_REASON_REQUIRED = (
    "every allowlist entry must declare a non-empty 'reason' explaining why "
    "the node is exempt from runtime_profiles enforcement"
)

_DEFAULT_ALLOWLIST_PATH = Path(__file__).parent / "runtime_profiles_allowlist.yaml"

# Consumer repos vendor a frozen baseline allowlist at this repo-relative path.
# The validator discovers it deterministically by walking up from each scanned
# contract to the repo root (no env var, no config-via-env). Pre-existing
# orphans are frozen here so the gate blocks NEW orphans without forcing a mass
# remediation; the drain is tracked separately (OMN-12982).
_REPO_ALLOWLIST_RELPATH = Path("validation") / "runtime_profiles_allowlist.yaml"


def load_default_allowlist(
    path: Path | None = None,
) -> dict[str, str]:
    """Return mapping of allowlisted node id -> reason.

    Raises ``ValueError`` if any entry is missing a non-empty ``reason``.
    Returns an empty dict if the file does not exist (bootstrap-friendly so
    new repos can adopt the validator before adding exemptions).
    """
    target = path or _DEFAULT_ALLOWLIST_PATH
    if not target.is_file():
        return {}
    raw = yaml.safe_load(target.read_text(encoding="utf-8")) or {}
    entries = raw.get("allowlist") if isinstance(raw, dict) else None
    if not isinstance(entries, list):
        return {}
    out: dict[str, str] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise ModelOnexError(
                message=(
                    f"runtime_profiles allowlist entries must be mappings; "
                    f"got {entry!r}"
                ),
                error_code=EnumCoreErrorCode.INVALID_CONFIGURATION,
                context={"allowlist_path": str(target)},
            )
        node_id = entry.get("node_id")
        reason = entry.get("reason")
        if not isinstance(node_id, str) or not node_id.strip():
            raise ModelOnexError(
                message="runtime_profiles allowlist entry missing non-empty 'node_id'",
                error_code=EnumCoreErrorCode.INVALID_CONFIGURATION,
                context={"allowlist_path": str(target)},
            )
        if not isinstance(reason, str) or not reason.strip():
            raise ModelOnexError(
                message=(
                    f"runtime_profiles allowlist entry {node_id!r}: "
                    f"{ALLOWLIST_REASON_REQUIRED}"
                ),
                error_code=EnumCoreErrorCode.INVALID_CONFIGURATION,
                context={
                    "allowlist_path": str(target),
                    "node_id": node_id,
                },
            )
        out[node_id.strip()] = reason.strip()
    return out


def _discover_repo_allowlist_path(contract_path: Path) -> Path | None:
    """Walk up from a contract path to a repo-root baseline allowlist.

    A repo declares a frozen baseline at ``<repo>/validation/runtime_profiles_
    allowlist.yaml``. The repo root is identified by the presence of a
    ``pyproject.toml`` (every ONEX package has one). Returns the allowlist path
    if it exists at that root, else ``None``. Deterministic, no env var.
    """
    try:
        current = contract_path.resolve().parent
    except OSError:
        return None
    seen: set[Path] = set()
    while current not in seen:
        seen.add(current)
        if (current / "pyproject.toml").is_file():
            candidate = current / _REPO_ALLOWLIST_RELPATH
            return candidate if candidate.is_file() else None
        parent = current.parent
        if parent == current:
            break
        current = parent
    return None


def _extract_runtime_profiles(raw: dict[str, object]) -> tuple[str, ...]:
    """Return declared runtime_profiles from either supported location."""
    profiles_raw = raw.get("runtime_profiles")
    descriptor_raw = raw.get("descriptor")
    if profiles_raw is None and isinstance(descriptor_raw, dict):
        profiles_raw = descriptor_raw.get("runtime_profiles")
    if profiles_raw is None:
        return ()
    if isinstance(profiles_raw, str):
        candidates: tuple[object, ...] = (profiles_raw,)
    elif isinstance(profiles_raw, (list, tuple)):
        candidates = tuple(profiles_raw)
    else:
        return ()
    return tuple(
        str(p).strip().lower() for p in candidates if isinstance(p, str) and p.strip()
    )


def _iter_subscribe_topics(raw: dict[str, object]) -> tuple[str, ...]:
    """Return all subscribed topics across both supported event_bus shapes."""
    event_bus = raw.get("event_bus")
    if not isinstance(event_bus, dict):
        return ()
    topics: list[str] = []
    classic = event_bus.get("subscribe_topics")
    if isinstance(classic, list):
        topics.extend(t for t in classic if isinstance(t, str))
    nested = event_bus.get("subscribe")
    if isinstance(nested, list):
        for item in nested:
            if isinstance(item, dict):
                topic = item.get("topic")
                if isinstance(topic, str):
                    topics.append(topic)
            elif isinstance(item, str):
                topics.append(item)
    return tuple(topics)


_COMMAND_TOPIC_PREFIX = f"{TOPIC_PREFIX}.cmd."


def _is_command_consuming(raw: dict[str, object]) -> bool:
    return any(t.startswith(_COMMAND_TOPIC_PREFIX) for t in _iter_subscribe_topics(raw))


def _node_kind(raw: dict[str, object]) -> str:
    """Return normalized node archetype: 'reducer' | 'effect' | 'compute' | ...

    Accepts both the bare form (``node_type: effect``) and the generic-suffix
    form (``node_type: EFFECT_GENERIC``), plus ``descriptor.node_archetype``.
    Returns an empty string when the archetype cannot be determined.
    """
    candidates: list[object] = [raw.get("node_type")]
    descriptor = raw.get("descriptor")
    if isinstance(descriptor, dict):
        candidates.append(descriptor.get("node_archetype"))
    for candidate in candidates:
        if isinstance(candidate, str) and candidate.strip():
            token = candidate.strip().lower()
            # Strip the "_generic" suffix on the canonical contract form.
            return token.removesuffix("_generic")
    return ""


# Archetypes whose subscriptions must be drained by a standalone consumer lane.
_CONSUMER_REQUIRING_KINDS: frozenset[str] = frozenset({"reducer", "effect"})


class ValidatorRuntimeProfiles(ValidatorBase):
    """Reject command-consuming node contracts that omit runtime_profiles."""

    validator_id: ClassVar[str] = "runtime_profiles"

    def __init__(
        self,
        contract: ModelValidatorSubcontract | None = None,
        allowlist: set[str] | None = None,
        allowlist_path: Path | None = None,
        discover_repo_allowlist: bool = True,
    ) -> None:
        super().__init__(contract=contract)
        # Base allowlist: explicit set (tests) > explicit path > core default.
        if allowlist is not None:
            self._base_allowlist: frozenset[str] = frozenset(allowlist)
        else:
            self._base_allowlist = frozenset(
                load_default_allowlist(allowlist_path).keys()
            )
        # When True (default), each scanned contract additionally consults the
        # repo-root baseline allowlist discovered by walking up to pyproject.toml.
        # Tests that pass an explicit allowlist disable discovery for isolation.
        self._discover_repo_allowlist = discover_repo_allowlist and allowlist is None
        # Cache discovered repo allowlists keyed by resolved allowlist-file path.
        self._repo_allowlist_cache: dict[Path, frozenset[str]] = {}

    def _allowlist_for(self, contract_path: Path) -> frozenset[str]:
        """Return the effective allowlist (base union repo baseline) for a file."""
        if not self._discover_repo_allowlist:
            return self._base_allowlist
        repo_allowlist_path = _discover_repo_allowlist_path(contract_path)
        if repo_allowlist_path is None:
            return self._base_allowlist
        cached = self._repo_allowlist_cache.get(repo_allowlist_path)
        if cached is None:
            cached = frozenset(load_default_allowlist(repo_allowlist_path).keys())
            self._repo_allowlist_cache[repo_allowlist_path] = cached
        return self._base_allowlist | cached

    def _validate_file(
        self,
        path: Path,
        contract: ModelValidatorSubcontract,
    ) -> tuple[ModelValidationIssue, ...]:
        if path.name != "contract.yaml" and path.name != "handler_contract.yaml":
            return ()
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            return ()
        try:
            raw = yaml.safe_load(text)
        except yaml.YAMLError:
            return ()
        if not isinstance(raw, dict):
            return ()

        node_id = raw.get("name")
        # An allowlisted node is a frozen baseline entry: it is exempt from ALL
        # runtime_profiles rules (missing, unregistered, no-consumer-lane). This
        # is how consumer repos adopt the gate without remediating every
        # pre-existing violator at once (drain tracked per-repo). NEW nodes are
        # not in any allowlist, so the gate still blocks new orphans. The
        # effective allowlist is the core default unioned with the repo-root
        # baseline discovered next to the scanned contract.
        if isinstance(node_id, str) and node_id in self._allowlist_for(path):
            return ()

        declared_profiles = _extract_runtime_profiles(raw)

        issues: list[ModelValidationIssue] = []
        issues.extend(self._check_missing(raw, path, node_id, contract))
        issues.extend(
            self._check_unregistered(declared_profiles, path, node_id, contract)
        )
        issues.extend(
            self._check_no_consumer_lane(
                raw, declared_profiles, path, node_id, contract
            )
        )
        return tuple(issues)

    def _check_missing(
        self,
        raw: dict[str, object],
        path: Path,
        node_id: object,
        contract: ModelValidatorSubcontract,
    ) -> tuple[ModelValidationIssue, ...]:
        """OMN-9886: command-consuming contract with no declared profiles.

        Allowlist exemption is handled by the caller (frozen-baseline
        short-circuit), so this method assumes the node is not allowlisted.
        """
        if not _is_command_consuming(raw):
            return ()
        if _extract_runtime_profiles(raw):
            return ()
        enabled, severity = self._get_rule_config(
            RULE_RUNTIME_PROFILES_MISSING, contract
        )
        if not enabled:
            return ()
        message = (
            "runtime_profiles missing on command-consuming contract "
            f"{node_id!r}: declare 'runtime_profiles: [<profile>]' at the top "
            "level or under 'descriptor', or add the node id to "
            "validation/runtime_profiles_allowlist.yaml with a reason."
        )
        return (
            ModelValidationIssue(
                severity=severity,
                message=message,
                code=RULE_RUNTIME_PROFILES_MISSING,
                file_path=path,
                line_number=1,
                rule_name=RULE_RUNTIME_PROFILES_MISSING,
            ),
        )

    def _check_unregistered(
        self,
        declared_profiles: tuple[str, ...],
        path: Path,
        node_id: object,
        contract: ModelValidatorSubcontract,
    ) -> tuple[ModelValidationIssue, ...]:
        """OMN-12957: declared profile not in the canonical registry."""
        unknown = tuple(
            p for p in declared_profiles if p not in REGISTERED_RUNTIME_PROFILES
        )
        if not unknown:
            return ()
        enabled, severity = self._get_rule_config(
            RULE_RUNTIME_PROFILE_UNREGISTERED, contract
        )
        if not enabled:
            return ()
        known = ", ".join(sorted(REGISTERED_RUNTIME_PROFILES))
        message = (
            f"runtime_profiles on contract {node_id!r} names unregistered "
            f"profile(s) {', '.join(repr(p) for p in unknown)}: a nonexistent "
            "profile silently orphans the node (no runtime process wires its "
            f"subscriptions). Use one of the registered profiles: {known}."
        )
        return (
            ModelValidationIssue(
                severity=severity,
                message=message,
                code=RULE_RUNTIME_PROFILE_UNREGISTERED,
                file_path=path,
                line_number=1,
                rule_name=RULE_RUNTIME_PROFILE_UNREGISTERED,
            ),
        )

    def _check_no_consumer_lane(
        self,
        raw: dict[str, object],
        declared_profiles: tuple[str, ...],
        path: Path,
        node_id: object,
        contract: ModelValidatorSubcontract,
    ) -> tuple[ModelValidationIssue, ...]:
        """OMN-12957: subscribing REDUCER/EFFECT names no consumer-attached lane.

        The declared profile names may all be registered yet none of them runs a
        standalone consumer, so the subscriptions are never drained. Only fires
        for REDUCER/EFFECT archetypes that actually subscribe to topics and
        declare a (registered) profile set — the missing-profiles case is owned
        by ``_check_missing`` and unregistered names by ``_check_unregistered``.
        Allowlist exemption is handled by the caller (frozen-baseline
        short-circuit).
        """
        if _node_kind(raw) not in _CONSUMER_REQUIRING_KINDS:
            return ()
        if not _iter_subscribe_topics(raw):
            return ()
        # Only registered profiles count toward consumer-lane membership; an
        # unregistered name is already reported and must not mask this rule.
        registered_declared = tuple(
            p for p in declared_profiles if p in REGISTERED_RUNTIME_PROFILES
        )
        if not registered_declared:
            return ()
        if any(p in CONSUMER_ATTACHED_RUNTIME_PROFILES for p in registered_declared):
            return ()
        enabled, severity = self._get_rule_config(
            RULE_RUNTIME_PROFILE_NO_CONSUMER_LANE, contract
        )
        if not enabled:
            return ()
        consumer_lanes = ", ".join(sorted(CONSUMER_ATTACHED_RUNTIME_PROFILES))
        message = (
            f"subscribing {_node_kind(raw)} contract {node_id!r} names only "
            f"runtime_profiles {list(registered_declared)} that run no standalone "
            "consumer, so its subscriptions are never drained (silent orphan). "
            f"Name at least one consumer-attached profile: {consumer_lanes}."
        )
        return (
            ModelValidationIssue(
                severity=severity,
                message=message,
                code=RULE_RUNTIME_PROFILE_NO_CONSUMER_LANE,
                file_path=path,
                line_number=1,
                rule_name=RULE_RUNTIME_PROFILE_NO_CONSUMER_LANE,
            ),
        )


if __name__ == "__main__":
    sys.exit(ValidatorRuntimeProfiles.main())
