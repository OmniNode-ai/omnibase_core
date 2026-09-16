# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Every terminal topic a contract declares, with the outcome it declares it for.

A contract states its terminals in up to three places, and before OMN-18445 the
client-side awaiter read exactly one of them:

1. top-level ``terminal_event`` — a single SUCCESS topic,
2. top-level ``terminal_events`` — a mapping or a sequence,
3. ``runtime_dispatch.terminal_events`` — the address external clients dispatch
   through, and the site where a contract's FAILURE terminal is normally the
   only place it appears at all.

``RuntimeLocal`` subscribed to site 1 alone. ``node_delegate_skill_orchestrator``
declares its failure terminal at site 3 and nowhere else, so every lane-side
delegation failure published a terminal the caller was not listening to: the
caller waited out its whole ``--timeout`` and reported a timeout for a run the
lane had already answered (OMN-18445; five dogfood runs on the ``.201`` dev lane,
2026-09-16T16:45Z-16:49Z, each with the lane's failure-terminal publish inside
the caller's own 200s window).

The outcome travels WITH the topic rather than being re-derived from each
message, because the two answer different questions. A payload's ``status`` says
what the handler thinks happened; the contract's declaration says what the
publisher's own wiring committed to that address meaning. When the contract calls
a topic the failure terminal, a record delivered there is a failure even if its
payload declares no status at all — the raw, un-enveloped failure shape observed
under OMN-15468 has no ``status`` field to read, and reading its absence as
success is the defect this ordering exists to prevent.

Layering note: ``omnibase_infra.runtime.contract_terminal_events`` reads the same
three sites for the SERVER side (the Pattern B ingress broker). It cannot be
imported here — infra sits above core — so this module is the core-side home for
the question, and infra's reader should be re-homed onto it once a core release
carries this. Two readers of one declaration is the drift that module's own
docstring warns about; the fix for that is one reader in the lower layer, not a
second copy in the higher one.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping

from omnibase_core.enums.enum_terminal_outcome import EnumTerminalOutcome
from omnibase_core.models.runtime.model_contract_terminal_topic import (
    ModelContractTerminalTopic,
)

__all__ = ["resolve_terminal_topics"]

# Mapping keys a contract uses to name the half of the terminal pair. These are
# declaration-vocabulary, not topic names: no topic string is ever spelled here.
_SUCCESS_KEYS: frozenset[str] = frozenset({"success", "succeeded", "completed"})
_FAILURE_KEYS: frozenset[str] = frozenset({"failure", "failed", "error"})


def _as_topic(value: object) -> str | None:
    """Return a non-empty topic string, or ``None`` for anything else."""
    if isinstance(value, str):
        normalized = value.strip()
        return normalized or None
    return None


def _outcome_for_key(key: object) -> EnumTerminalOutcome:
    """Map a ``terminal_events`` mapping key onto the outcome it declares."""
    if not isinstance(key, str):
        return EnumTerminalOutcome.UNSPECIFIED
    normalized = key.strip().lower()
    if normalized in _SUCCESS_KEYS:
        return EnumTerminalOutcome.SUCCESS
    if normalized in _FAILURE_KEYS:
        return EnumTerminalOutcome.FAILURE
    return EnumTerminalOutcome.UNSPECIFIED


def _pairs_from_declaration(
    declaration: object,
) -> tuple[tuple[str, EnumTerminalOutcome], ...]:
    """Normalize one ``terminal_events`` declaration into (topic, outcome) pairs.

    A MAPPING declares its outcomes by key, and its success entry is emitted
    first regardless of YAML key order — leaving that to key order would make a
    terminal's completed-vs-failed meaning depend on how the contract author
    happened to sort two lines.

    A SEQUENCE declares no outcomes at all. Every entry is
    :attr:`EnumTerminalOutcome.UNSPECIFIED` and the payload decides, which is
    what the pre-OMN-18445 behaviour already did for the one topic it read.
    """
    if isinstance(declaration, Mapping):
        ordered: list[tuple[object, object]] = [
            (key, value)
            for key, value in declaration.items()
            if _outcome_for_key(key) is EnumTerminalOutcome.SUCCESS
        ]
        ordered.extend(
            (key, value)
            for key, value in declaration.items()
            if _outcome_for_key(key) is not EnumTerminalOutcome.SUCCESS
        )
        pairs: list[tuple[str, EnumTerminalOutcome]] = []
        for key, value in ordered:
            topic = _as_topic(value)
            if topic is not None:
                pairs.append((topic, _outcome_for_key(key)))
        return tuple(pairs)

    if isinstance(declaration, list | tuple):
        values: Iterable[object] = declaration
        return tuple(
            (topic, EnumTerminalOutcome.UNSPECIFIED)
            for topic in (_as_topic(value) for value in values)
            if topic is not None
        )

    return ()


def resolve_terminal_topics(
    contract: Mapping[str, object],
) -> tuple[ModelContractTerminalTopic, ...]:
    """Return every terminal topic the contract declares, success-first.

    Reads the three declaration sites in order, so the top-level
    ``terminal_event`` — the only site the awaiter read before OMN-18445 — stays
    first and its subscription keeps the consumer group it has always had.

    A topic declared at more than one site is emitted once, on its FIRST
    declaration. Because success-bearing sites are read first, a topic named
    both as the success terminal and again with no outcome keeps SUCCESS rather
    than being downgraded by a later, less specific mention.

    Returns an empty tuple when the contract declares no terminal at all; the
    caller decides whether that is an error, exactly as it did when this was a
    single ``contract.get("terminal_event")``.
    """
    collected: dict[str, EnumTerminalOutcome] = {}

    def _record(topic: str, outcome: EnumTerminalOutcome) -> None:
        if topic not in collected:
            collected[topic] = outcome

    terminal_event = _as_topic(contract.get("terminal_event"))
    if terminal_event is not None:
        _record(terminal_event, EnumTerminalOutcome.SUCCESS)

    for topic, outcome in _pairs_from_declaration(contract.get("terminal_events")):
        _record(topic, outcome)

    runtime_dispatch = contract.get("runtime_dispatch")
    if isinstance(runtime_dispatch, Mapping):
        for topic, outcome in _pairs_from_declaration(
            runtime_dispatch.get("terminal_events")
        ):
            _record(topic, outcome)

    return tuple(
        ModelContractTerminalTopic(topic=topic, outcome=outcome)
        for topic, outcome in collected.items()
    )
