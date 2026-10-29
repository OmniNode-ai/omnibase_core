# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure parsers for the event-registration sources the drift check compares (OMN-21416).

Every parser takes a ``(path, source)`` pair already read at the EFFECT
boundary and returns typed registrations plus error messages. A source that
cannot be read as declared is an error, never an empty result, so the check
reports ERROR instead of PASS on input it did not understand.

Sources:

* **Registration contract** — a wire contract that declares an
  ``event_registration`` block. The event type comes from
  ``producer.event_type``; the block declares the partition key (explicitly,
  ``null`` allowed), the fan-out topics and the required field names. The
  join is checked: the contract's own ``topic`` must be one of the fan-out
  topics, and every required field must be a field the wire contract declares
  under ``required_fields``. A wire contract without the block declares no
  registration and is skipped.
* **Registration document** — ``event_registrations:``, a list of
  ``{event_type, topics, partition_key_field, required_fields}``, for a
  producer whose registrations are exported rather than declared in contracts.
* **Emit registry** — an emit daemon's ``topics.yaml`` (``events:`` mapping of
  event type to ``partition_key_field``, ``required_fields`` and ``fan_out``).
  As in the registry's own drift check, only fan-out topics named in full
  (``onex.`` prefix) are compared.
* **Baseline** — ``<kind> <value>`` lines declaring intentional divergence.

Pure — no filesystem access, no clock, no global state.
"""

from __future__ import annotations

from typing import Final

import yaml

from omnibase_core.models.event_registry_drift.model_event_registration import (
    ModelEventRegistration,
)
from omnibase_core.models.event_registry_drift.model_event_registry_drift_baseline import (
    ModelEventRegistryDriftBaseline,
)
from omnibase_core.utils.util_safe_yaml_loader import (
    load_yaml_mapping_no_duplicates,
)

__all__ = [
    "BASELINE_KINDS",
    "parse_baseline",
    "parse_emit_registry",
    "parse_registration_contract",
    "parse_registration_document",
]

_TOPIC_PREFIX: Final[str] = "onex."

BASELINE_KINDS: Final[tuple[str, ...]] = (
    "event_source_only",
    "event_registry_only",
    "source_only",
    "registry_only",
)

_Parsed = tuple[tuple[ModelEventRegistration, ...], tuple[str, ...]]


def _load_mapping(path: str, source: str) -> tuple[dict[object, object] | None, str]:
    try:
        return load_yaml_mapping_no_duplicates(source, source=path), ""
    except (yaml.YAMLError, ValueError) as exc:
        return None, f"{path}: cannot be read as a YAML mapping: {exc}"


def _name_list(value: object) -> tuple[str, ...] | None:
    """A list of distinct non-empty strings, or ``None`` when it is not one."""
    if not isinstance(value, list):
        return None
    names = tuple(item for item in value if isinstance(item, str) and item)
    if len(names) != len(value) or len(set(names)) != len(names):
        return None
    return names


def _partition_key(block: dict[object, object], where: str) -> tuple[str | None, str]:
    if "partition_key_field" not in block:
        return None, f"{where}: partition_key_field is not declared (use null for none)"
    value = block["partition_key_field"]
    if value is None or (isinstance(value, str) and value):
        return value, ""
    return None, f"{where}: partition_key_field must be a non-empty string or null"


def parse_registration_contract(
    path: str, source: str
) -> tuple[ModelEventRegistration | None, tuple[str, ...]]:
    """Parse one wire contract; ``(None, ())`` when it declares no registration."""
    doc, error = _load_mapping(path, source)
    if doc is None:
        return None, (error,)
    if "event_registration" not in doc:
        return None, ()
    block = doc["event_registration"]
    if not isinstance(block, dict):
        return None, (f"{path}: event_registration must be a mapping",)

    errors: list[str] = []
    producer = doc.get("producer")
    event_type = producer.get("event_type") if isinstance(producer, dict) else None
    if not isinstance(event_type, str) or not event_type:
        errors.append(f"{path}: producer.event_type is not declared")

    partition_key_field, key_error = _partition_key(block, path)
    if key_error:
        errors.append(key_error)

    fan_out = block.get("fan_out")
    topics: list[str] = []
    if not isinstance(fan_out, list) or not fan_out:
        errors.append(f"{path}: event_registration.fan_out must be a non-empty list")
    else:
        for rule in fan_out:
            topic = rule.get("topic") if isinstance(rule, dict) else None
            if not isinstance(topic, str) or not topic.startswith(_TOPIC_PREFIX):
                errors.append(
                    f"{path}: every fan_out rule needs a full topic name ({_TOPIC_PREFIX}...)"
                )
            else:
                topics.append(topic)
        if len(set(topics)) != len(topics):
            errors.append(f"{path}: event_registration.fan_out repeats a topic")
        wire_topic = doc.get("topic")
        if wire_topic not in topics:
            errors.append(
                f"{path}: the contract's topic {wire_topic!r} is not one of its fan_out topics"
            )

    required_fields = _name_list(block.get("required_fields"))
    if required_fields is None:
        errors.append(
            f"{path}: event_registration.required_fields must be a list of distinct names"
        )
    else:
        wire_fields = doc.get("required_fields")
        declared = (
            {
                item.get("name")
                for item in wire_fields
                if isinstance(item, dict) and isinstance(item.get("name"), str)
            }
            if isinstance(wire_fields, list)
            else None
        )
        if declared is None:
            errors.append(f"{path}: the wire contract declares no required_fields list")
        else:
            undeclared = sorted(set(required_fields) - declared)
            if undeclared:
                errors.append(
                    f"{path}: event_registration.required_fields names fields the wire "
                    f"contract does not declare: {undeclared}"
                )

    if errors:
        return None, tuple(errors)
    assert isinstance(event_type, str) and required_fields is not None
    return (
        ModelEventRegistration(
            event_type=event_type,
            topics=tuple(topics),
            partition_key_field=partition_key_field,
            required_fields=required_fields,
            source=path,
        ),
        (),
    )


def parse_registration_document(path: str, source: str) -> _Parsed:
    """Parse an ``event_registrations:`` document."""
    doc, error = _load_mapping(path, source)
    if doc is None:
        return (), (error,)
    entries = doc.get("event_registrations")
    if not isinstance(entries, list) or not entries:
        return (), (f"{path}: event_registrations must be a non-empty list",)

    registrations: list[ModelEventRegistration] = []
    errors: list[str] = []
    for index, entry in enumerate(entries):
        where = f"{path}: event_registrations[{index}]"
        if not isinstance(entry, dict):
            errors.append(f"{where} must be a mapping")
            continue
        event_type = entry.get("event_type")
        topics = _name_list(entry.get("topics"))
        required_fields = _name_list(entry.get("required_fields"))
        partition_key_field, key_error = _partition_key(entry, where)
        entry_errors = [key_error] if key_error else []
        if not isinstance(event_type, str) or not event_type:
            entry_errors.append(f"{where}: event_type is not declared")
        if not topics or not all(t.startswith(_TOPIC_PREFIX) for t in topics):
            entry_errors.append(
                f"{where}: topics must be a non-empty list of full topic names"
            )
        if required_fields is None:
            entry_errors.append(
                f"{where}: required_fields must be a list of distinct names"
            )
        if entry_errors:
            errors.extend(entry_errors)
            continue
        assert isinstance(event_type, str) and topics and required_fields is not None
        registrations.append(
            ModelEventRegistration(
                event_type=event_type,
                topics=topics,
                partition_key_field=partition_key_field,
                required_fields=required_fields,
                source=path,
            )
        )
    if errors:
        return (), tuple(errors)
    return tuple(registrations), ()


def parse_emit_registry(path: str, source: str) -> _Parsed:
    """Parse an emit daemon's ``topics.yaml`` ``events:`` mapping."""
    doc, error = _load_mapping(path, source)
    if doc is None:
        return (), (error,)
    events = doc.get("events")
    if not isinstance(events, dict) or not events:
        return (), (f"{path}: events must be a non-empty mapping",)

    registrations: list[ModelEventRegistration] = []
    errors: list[str] = []
    for event_type, event_def in events.items():
        where = f"{path}: events.{event_type}"
        if not isinstance(event_type, str) or not isinstance(event_def, dict):
            errors.append(f"{where} must be a mapping keyed by event type")
            continue
        fan_out = event_def.get("fan_out", [])
        if not isinstance(fan_out, list) or not all(
            isinstance(r, dict) for r in fan_out
        ):
            errors.append(f"{where}.fan_out must be a list of mappings")
            continue
        topics = sorted(
            {
                rule["topic"]
                for rule in fan_out
                if isinstance(rule.get("topic"), str)
                and rule["topic"].startswith(_TOPIC_PREFIX)
            }
        )
        partition_key_field = event_def.get("partition_key_field")
        if partition_key_field is not None and not isinstance(partition_key_field, str):
            errors.append(f"{where}.partition_key_field must be a string or null")
            continue
        required_raw = event_def.get("required_fields", [])
        if not isinstance(required_raw, list):
            errors.append(f"{where}.required_fields must be a list")
            continue
        registrations.append(
            ModelEventRegistration(
                event_type=event_type,
                topics=tuple(topics),
                partition_key_field=partition_key_field,
                required_fields=tuple(str(item) for item in required_raw),
                source=path,
            )
        )
    if errors:
        return (), tuple(errors)
    return tuple(registrations), ()


def parse_baseline(
    path: str, source: str
) -> tuple[ModelEventRegistryDriftBaseline | None, tuple[str, ...]]:
    """Parse ``<kind> <value>`` baseline lines; ``#`` starts a comment."""
    entries: dict[str, set[str]] = {kind: set() for kind in BASELINE_KINDS}
    errors: list[str] = []
    for line_number, raw in enumerate(source.splitlines(), start=1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) != 2 or parts[0] not in entries:
            errors.append(
                f"{path}:{line_number}: expected '<kind> <value>' with kind one of "
                f"{', '.join(BASELINE_KINDS)}"
            )
            continue
        entries[parts[0]].add(parts[1])
    if errors:
        return None, tuple(errors)
    return (
        ModelEventRegistryDriftBaseline(
            event_source_only=frozenset(entries["event_source_only"]),
            event_registry_only=frozenset(entries["event_registry_only"]),
            source_only_topics=frozenset(entries["source_only"]),
            registry_only_topics=frozenset(entries["registry_only"]),
        ),
        (),
    )
