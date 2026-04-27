# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ValidatorRuntimeProfiles -- enforce runtime_profiles on command-consuming contracts.

Plan source: ``docs/plans/2026-04-26-runtime-lifecycle-hardening-plan.md`` (Task 4,
Wave 1 core). Linear: OMN-9886.

A node contract is "command-consuming" if its ``event_bus`` block subscribes
to at least one topic matching ``onex.cmd.*``. The validator fails when such
a contract has empty/absent ``runtime_profiles`` and the node id is not in
the explicit allowlist.

Both contract shapes for ``runtime_profiles`` are accepted (mirrors the
canonical extractor in
``omnibase_infra.runtime.auto_wiring.discovery._extract_runtime_profiles``):

- top-level ``runtime_profiles: [str, ...]``
- ``descriptor.runtime_profiles: [str, ...]``

Both subscription shapes are accepted (Task 6 adds a typed parser; this
validator must not under-detect command consumers in the meantime):

- classic: ``event_bus.subscribe_topics: [str, ...]``
- nested: ``event_bus.subscribe: [{topic: str, ...}, ...]``

The allowlist is loaded from
``src/omnibase_core/validation/runtime_profiles_allowlist.yaml``. Every
entry MUST carry a non-empty ``reason`` string; the loader raises
``ValueError`` on a blank reason so a "drop in to silence the gate" PR
cannot land. Per-call overrides via the ``allowlist`` constructor argument
are intended for tests.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import ClassVar

import yaml

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.validation.validator_base import ValidatorBase
from omnibase_core.validation.validator_topic_suffix import TOPIC_PREFIX

RULE_RUNTIME_PROFILES_MISSING = "runtime_profiles_missing"
ALLOWLIST_REASON_REQUIRED = (
    "every allowlist entry must declare a non-empty 'reason' explaining why "
    "the node is exempt from runtime_profiles enforcement"
)

_DEFAULT_ALLOWLIST_PATH = Path(__file__).parent / "runtime_profiles_allowlist.yaml"


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


class ValidatorRuntimeProfiles(ValidatorBase):
    """Reject command-consuming node contracts that omit runtime_profiles."""

    validator_id: ClassVar[str] = "runtime_profiles"

    def __init__(
        self,
        contract: ModelValidatorSubcontract | None = None,
        allowlist: set[str] | None = None,
        allowlist_path: Path | None = None,
    ) -> None:
        super().__init__(contract=contract)
        if allowlist is not None:
            self._allowlist: frozenset[str] = frozenset(allowlist)
        else:
            self._allowlist = frozenset(load_default_allowlist(allowlist_path).keys())

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

        if not _is_command_consuming(raw):
            return ()
        if _extract_runtime_profiles(raw):
            return ()

        node_id = raw.get("name")
        if isinstance(node_id, str) and node_id in self._allowlist:
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


if __name__ == "__main__":
    sys.exit(ValidatorRuntimeProfiles.main())
