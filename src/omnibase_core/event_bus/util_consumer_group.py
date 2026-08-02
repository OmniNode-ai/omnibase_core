# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Canonical Kafka consumer-group derivation and IAM authorization checking.

This module is the **single** home for consumer-group name derivation across the
platform (operator ruling 2026-08-02, option (c) on OMN-15639). ``omnibase_infra``
imports from here; it does not keep its own copy, and neither does
``event_bus_inmemory``. Three independent derivations previously existed and drifted:

- ``omnibase_infra.utils.util_consumer_group`` (the original, OMN-1602),
- ``omnibase_core.event_bus.event_bus_inmemory._compute_consumer_group_id`` (inlined
  to avoid an infra dependency),
- ad-hoc f-string literals at individual call sites.

The third class is what caused OMN-15639: ``runtime_local.py`` minted
``runtime-local-<handler>`` and ``cli_run_node.py`` minted
``onex-run-node-<correlation_id>``, neither of which is matched by any pattern in the
MSK IAM policy. Every ``onex delegate --bus kafka`` submission on onex-dev died with
``GroupAuthorizationFailedError`` *before* publishing.

Authorization model
-------------------
The MSK IAM policy authorizes ``AlterGroup``/``DescribeGroup`` on a fixed set of
whole-name glob patterns, pinned in ``omnibase_core/contracts/consumer_group_iam_patterns.yaml``.
Two derivation shapes are authorized by construction:

1. **Identity-derived** — :func:`compute_consumer_group_id` renders
   ``{env}.{service}.{node_name}.{purpose}.{version}``. Because the environment token
   leads, the name is authorized whenever ``"<env>."`` is matched by some pattern
   (``onex-dev.*`` for the managed environment).
2. **Reserved-prefix** — :func:`derive_prefixed_group_id` renders
   ``<reserved-prefix><sep><scope>`` for the handful of lanes that own an IAM prefix
   outright (pattern-B broker, phase-5 smoke, runtime-config ingress).

:func:`is_authorized_group_name` implements the glob semantics **exactly**: a pattern
is anchored at both ends and ``*`` is the only metacharacter. A substring test would
wrongly accept the OMN-15639 defect name (which *contains* ``onex.`` but does not
*begin* with it) and is a vacuous implementation of this contract.

.. versionadded:: OMN-15639
"""

from __future__ import annotations

import hashlib
import os
import re
from functools import lru_cache
from importlib import resources
from typing import Final

import yaml

from omnibase_core.enums.enum_consumer_group_purpose import EnumConsumerGroupPurpose
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_reserved_group_prefix import EnumReservedGroupPrefix
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.event_bus.model_consumer_group_iam_patterns import (
    ModelConsumerGroupIamPatterns,
)
from omnibase_core.models.event_bus.model_consumer_group_scope import (
    ModelConsumerGroupScope,
)

# Kafka's hard limit on consumer group ID length.
KAFKA_CONSUMER_GROUP_MAX_LENGTH: Final[int] = (
    255  # env-var-ok: Kafka wire-protocol limit, not configuration
)

# Infix markers. `.__t.` scopes a group to one topic; `.__i.` scopes it to one
# instance/correlation. Both preserve the leading environment token.
TOPIC_SCOPE_INFIX: Final[str] = ".__t."
INSTANCE_SCOPE_INFIX: Final[str] = ".__i."

# Environment variable naming the deployment environment. Allowlisted in
# omnibase_core.validators.no_new_os_environ.
ENVIRONMENT_ENV_VAR: Final[str] = "ENVIRONMENT"
DEFAULT_ENVIRONMENT: Final[str] = "local"

_IAM_PATTERNS_PACKAGE: Final[str] = "omnibase_core.contracts"
_IAM_PATTERNS_RESOURCE: Final[str] = "consumer_group_iam_patterns.yaml"

_INVALID_CHAR_PATTERN: Final[re.Pattern[str]] = re.compile(r"[^a-z0-9._-]")
_CONSECUTIVE_SEPARATOR_PATTERN: Final[re.Pattern[str]] = re.compile(r"[._-]{2,}")
_EDGE_SEPARATOR_PATTERN: Final[re.Pattern[str]] = re.compile(r"^[._-]+|[._-]+$")


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------


def normalize_kafka_identifier(value: str) -> str:
    """Normalize a string for use as a Kafka consumer-group component.

    Applies, in order: lowercase, replace characters outside ``[a-z0-9._-]`` with
    ``_``, collapse runs of separators to the first separator in the run, strip
    leading/trailing separators, then truncate to 255 with a deterministic 8-hex-char
    suffix if still too long.

    Args:
        value: The raw component.

    Returns:
        A Kafka-safe identifier.

    Raises:
        ModelOnexError: ``VALIDATION_ERROR`` if ``value`` is empty or normalizes away
            to the empty string.

    Example:
        >>> normalize_kafka_identifier("My Service!!")
        'my_service'
        >>> normalize_kafka_identifier("foo..bar__baz")
        'foo.bar_baz'
        >>> normalize_kafka_identifier("  UPPER_Case-Test  ")
        'upper_case-test'
    """
    if not value:
        raise ModelOnexError(
            "Kafka consumer group component cannot be empty",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        )

    result = value.lower()
    result = _INVALID_CHAR_PATTERN.sub("_", result)
    result = _CONSECUTIVE_SEPARATOR_PATTERN.sub(lambda m: m.group(0)[0], result)
    result = _EDGE_SEPARATOR_PATTERN.sub("", result)

    if not result:
        raise ModelOnexError(
            f"Input {value!r} results in empty string after normalization",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        )

    return _truncate_with_hash(result, hash_input=value)


def _truncate_with_hash(value: str, *, hash_input: str) -> str:
    """Truncate to the Kafka limit, appending ``_<8 hex>`` derived from ``hash_input``.

    The hash is taken over the *pre-normalization* input so that two distinct inputs
    that normalize to the same 246-char prefix still produce distinct group IDs.
    """
    if len(value) <= KAFKA_CONSUMER_GROUP_MAX_LENGTH:
        return value
    suffix = hashlib.sha256(hash_input.encode()).hexdigest()[:8]
    return f"{value[: KAFKA_CONSUMER_GROUP_MAX_LENGTH - 9]}_{suffix}"


def resolve_environment_token() -> str:
    """Resolve the environment token that leads every identity-derived group ID.

    Reads ``ENVIRONMENT`` and normalizes it. Falls back to ``"local"``, which is
    deliberately NOT an MSK-managed environment: an unset ``ENVIRONMENT`` must not
    silently masquerade as a managed one.

    Returns:
        The normalized environment token.
    """
    raw = os.environ.get(ENVIRONMENT_ENV_VAR, "").strip() or DEFAULT_ENVIRONMENT
    return normalize_kafka_identifier(raw)


# ---------------------------------------------------------------------------
# Derivation
# ---------------------------------------------------------------------------


def compute_consumer_group_id(
    *,
    env: str,
    service: str,
    node_name: str,
    version: str,
    purpose: EnumConsumerGroupPurpose = EnumConsumerGroupPurpose.CONSUME,
) -> str:
    """Compute the canonical identity-derived consumer group ID.

    Format: ``{env}.{service}.{node_name}.{purpose}.{version}``, each component
    normalized. The environment token leads, which is what makes the result
    authorizable by an ``"<env>.*"`` IAM pattern.

    Takes the four identity components explicitly rather than a
    ``ProtocolNodeIdentity`` object. That is deliberate: the OMN-14340 import-layering
    ratchet hard-fails any NEW core module that imports the ``protocols`` hub, and a
    protocol-typed parameter would need exactly that import. Callers holding an
    identity object (``ModelEmitterIdentity`` in core, ``ModelNodeIdentity`` in infra)
    unpack it at the call site, which also keeps this module free of any model or
    protocol coupling.

    Args:
        env: Environment token. Leads the group ID and decides IAM authorization.
        service: Owning service name.
        node_name: Node or handler name.
        version: Identity version.
        purpose: Consumer-group purpose. Defaults to ``CONSUME``.

    Returns:
        The canonical group ID, truncated with a deterministic hash suffix if it
        would exceed 255 characters.

    Example:
        >>> compute_consumer_group_id(
        ...     env="onex-dev",
        ...     service="omnimarket",
        ...     node_name="delegate_skill",
        ...     version="v1",
        ... )
        'onex-dev.omnimarket.delegate_skill.consume.v1'
    """
    group_id = ".".join(
        [
            normalize_kafka_identifier(env),
            normalize_kafka_identifier(service),
            normalize_kafka_identifier(node_name),
            normalize_kafka_identifier(purpose.value),
            normalize_kafka_identifier(version),
        ]
    )
    hash_input = f"{env}|{service}|{node_name}|{purpose.value}|{version}"
    return _truncate_with_hash(group_id, hash_input=hash_input)


def apply_topic_discriminator(group_id: str, topic: str | None) -> str:
    """Append a ``.__t.<topic>`` scope infix, idempotently.

    Args:
        group_id: Base group ID.
        topic: Topic name, or None/blank for no topic scoping.

    Returns:
        The topic-scoped group ID, or ``group_id`` unchanged when ``topic`` is empty.

    Example:
        >>> apply_topic_discriminator("onex-dev.svc.node.consume.v1", "example.evt.foo.v1")
        'onex-dev.svc.node.consume.v1.__t.example.evt.foo.v1'
        >>> apply_topic_discriminator("onex-dev.svc.node.consume.v1", None)
        'onex-dev.svc.node.consume.v1'
    """
    return _apply_infix(group_id, TOPIC_SCOPE_INFIX, topic)


def apply_instance_discriminator(group_id: str, instance_token: str | None) -> str:
    """Append a ``.__i.<instance>`` scope infix, idempotently.

    In multi-container environments, containers sharing an identity also share a
    consumer group and split partitions. This infix gives each instance its own group.

    Args:
        group_id: Base group ID.
        instance_token: Instance discriminator (typically ``KAFKA_INSTANCE_ID``), or
            None/blank for no instance scoping.

    Returns:
        The instance-scoped group ID, or ``group_id`` unchanged when ``instance_token``
        is empty.

    Note:
        ``instance_token`` is normalized before append, and the idempotency check uses
        the normalized form. Callers must NOT pre-normalize.

    Example:
        >>> apply_instance_discriminator("onex-dev.svc.node.consume.v1", "pod-7")
        'onex-dev.svc.node.consume.v1.__i.pod-7'
        >>> apply_instance_discriminator(
        ...     "onex-dev.svc.node.consume.v1.__i.pod-7", "pod-7"
        ... )
        'onex-dev.svc.node.consume.v1.__i.pod-7'
    """
    return _apply_infix(group_id, INSTANCE_SCOPE_INFIX, instance_token)


def _apply_infix(group_id: str, infix: str, raw_value: str | None) -> str:
    """Idempotently append ``<infix><normalized raw_value>`` within the length limit."""
    if raw_value is None or not raw_value.strip():
        return group_id
    normalized = normalize_kafka_identifier(raw_value.strip())
    suffix = f"{infix}{normalized}"
    if group_id.endswith(suffix):
        return group_id
    return _truncate_with_hash(
        f"{group_id}{suffix}", hash_input=f"{group_id}|{normalized}"
    )


def derive_consumer_group_id(
    *,
    env: str,
    service: str,
    node_name: str,
    version: str,
    purpose: EnumConsumerGroupPurpose = EnumConsumerGroupPurpose.CONSUME,
    scope: ModelConsumerGroupScope | None = None,
) -> str:
    """Derive the fully-scoped consumer group ID for an identity.

    This is the call sites' entry point: identity + declared scope in, authorized
    name out. Composition order is identity -> topic scope -> instance scope, so the
    environment token always leads and IAM authorization is preserved.

    Args:
        env: Environment token.
        service: Owning service name.
        node_name: Node or handler name.
        version: Identity version.
        purpose: Consumer-group purpose. Defaults to ``CONSUME``.
        scope: Optional declared scope. ``None`` means the shared, undiscriminated
            group for this identity.

    Returns:
        The derived group ID.

    Example:
        >>> from uuid import UUID
        >>> derive_consumer_group_id(
        ...     env="onex-dev",
        ...     service="omnibase_core",
        ...     node_name="cli_run_node",
        ...     version="v1",
        ...     scope=ModelConsumerGroupScope(
        ...         correlation_id=UUID("9f2c0000-0000-4000-8000-000000000000")
        ...     ),
        ... )
        'onex-dev.omnibase_core.cli_run_node.consume.v1.__i.9f2c0000-0000-4000-8000-000000000000'
    """
    group_id = compute_consumer_group_id(
        env=env,
        service=service,
        node_name=node_name,
        version=version,
        purpose=purpose,
    )
    if scope is None:
        return group_id
    group_id = apply_topic_discriminator(group_id, scope.topic)
    tokens = scope.discriminator_tokens()
    if tokens:
        group_id = apply_instance_discriminator(group_id, "-".join(tokens))
    return group_id


def derive_service_group_id(
    node_name: str,
    *,
    service: str,
    version: str = "v1",
    purpose: EnumConsumerGroupPurpose = EnumConsumerGroupPurpose.CONSUME,
    scope: ModelConsumerGroupScope | None = None,
) -> str:
    """Derive a group ID for a service-owned consumer, resolving env from the process.

    Convenience wrapper over :func:`derive_consumer_group_id` for the common call-site
    shape where the environment comes from :func:`resolve_environment_token` and the
    remaining identity components are compile-time constants. Using this keeps call
    sites free of group-name string literals, which is what the OMN-15639 AC3 gate
    enforces statically.

    Args:
        node_name: Node or handler name.
        service: Owning service (e.g. ``"omnibase_core"``).
        version: Identity version. Defaults to ``"v1"``.
        purpose: Consumer-group purpose. Defaults to ``CONSUME``.
        scope: Optional declared scope.

    Returns:
        The derived, environment-qualified group ID.
    """
    return derive_consumer_group_id(
        env=resolve_environment_token(),
        service=service,
        node_name=node_name,
        version=version,
        purpose=purpose,
        scope=scope,
    )


def derive_prefixed_group_id(
    prefix: EnumReservedGroupPrefix,
    scope: ModelConsumerGroupScope,
) -> str:
    """Derive a consumer group ID under a reserved IAM prefix.

    Args:
        prefix: The reserved prefix this lane owns.
        scope: Declared scope. Must carry at least one discriminator token.

    Returns:
        ``<prefix><separator><scope tokens joined by '-'>``, optionally topic-scoped.

    Raises:
        ModelOnexError: ``VALIDATION_ERROR`` when ``scope`` carries no discriminator
            token. This is not defensive padding: the IAM glob is
            ``pattern-b-broker-*``, so the bare prefix ``pattern-b-broker`` (no
            trailing separator, no scope) is **unauthorized** and would fail at the
            broker with ``GroupAuthorizationFailedError``. Failing here, at mint time,
            is the fail-closed behaviour.

    Example:
        >>> from uuid import UUID
        >>> derive_prefixed_group_id(
        ...     EnumReservedGroupPrefix.PATTERN_B_BROKER,
        ...     ModelConsumerGroupScope(
        ...         ephemeral_tag="terminal",
        ...         correlation_id=UUID("9f2c0000-0000-4000-8000-000000000000"),
        ...     ),
        ... )
        'pattern-b-broker-terminal-9f2c0000-0000-4000-8000-000000000000'
    """
    tokens = scope.discriminator_tokens()
    if not tokens:
        raise ModelOnexError(
            f"Reserved consumer-group prefix {prefix.value!r} requires a non-empty "
            f"scope: the authorized IAM glob is {prefix.authorized_glob()!r}, which "
            f"does not match the bare prefix.",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        )
    joined = normalize_kafka_identifier("-".join(tokens))
    group_id = f"{prefix.value}{prefix.separator()}{joined}"
    group_id = _truncate_with_hash(group_id, hash_input=f"{prefix.value}|{joined}")
    return apply_topic_discriminator(group_id, scope.topic)


# ---------------------------------------------------------------------------
# IAM authorization
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def load_iam_pattern_document() -> ModelConsumerGroupIamPatterns:
    """Load, validate, and digest-check the pinned MSK IAM pattern document.

    Returns:
        The validated document. Shape errors surface as Pydantic validation errors
        (``extra="forbid"``, non-empty constraints) rather than as a silently-empty
        authorized set.

    Raises:
        ModelOnexError: ``VALIDATION_ERROR`` when ``pattern_set_sha256`` does not
            match the digest recomputed from ``authorized_patterns``. This is the
            drift detector: it makes an un-receipted edit to the pattern list a hard
            failure rather than a silent widening of what CI considers authorized.
    """
    # Two-step: yaml.safe_load() -> model_validate(). The raw mapping is never used
    # unvalidated. Same shape as the sibling aislop_rule_loader / antipattern_registry_loader,
    # and allowlisted alongside them in .yaml-validation-allowlist.yaml. Loading through
    # omnibase_core.utils instead would add a new importer to the `utils` hub, which the
    # OMN-14340 ratchet tracks and this module has no reason to deepen.
    raw = (
        resources.files(_IAM_PATTERNS_PACKAGE)
        .joinpath(_IAM_PATTERNS_RESOURCE)
        .read_text(encoding="utf-8")
    )
    document = ModelConsumerGroupIamPatterns.model_validate(yaml.safe_load(raw))

    actual_digest = compute_pattern_set_digest(document.authorized_patterns)
    if document.pattern_set_sha256 != actual_digest:
        raise ModelOnexError(
            f"{_IAM_PATTERNS_RESOURCE}: pattern_set_sha256 drift — declared "
            f"{document.pattern_set_sha256!r}, recomputed {actual_digest!r}. "
            f"Re-verify the terraform source before updating the digest.",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        )

    return document


def compute_pattern_set_digest(patterns: tuple[str, ...]) -> str:
    """Return the sha256 of ``patterns`` joined by ``\\n`` with no trailing newline."""
    return hashlib.sha256("\n".join(patterns).encode()).hexdigest()


def load_authorized_group_patterns() -> tuple[str, ...]:
    """Return the pinned MSK IAM authorized consumer-group patterns, in source order."""
    return load_iam_pattern_document().authorized_patterns


def load_managed_environments() -> tuple[str, ...]:
    """Return the environment tokens whose brokers are MSK (and thus IAM-gated)."""
    return load_iam_pattern_document().managed_environments


@lru_cache(maxsize=256)
def _compile_iam_glob(pattern: str) -> re.Pattern[str]:
    """Compile an IAM resource glob into an anchored regex.

    ``*`` matches any run of characters (including none); ``?`` matches exactly one.
    Every other character — crucially ``.`` — is a literal. The result is anchored with
    ``^``/``\\Z``, so matching is whole-name, never substring, and never tolerates a
    trailing newline the way ``$`` would.
    """
    compiled = "".join(
        ".*" if char == "*" else "." if char == "?" else re.escape(char)
        for char in pattern
    )
    # \Z, not $: in Python `$` also matches immediately BEFORE a trailing newline,
    # so `^onex-dev\..*$` would authorize "onex-dev.svc\n". MSK matches the whole
    # name with no such allowance. Derived names cannot contain a newline
    # (normalize_kafka_identifier strips it), but is_authorized_group_name is also
    # the gate's matcher for arbitrary caller-supplied names, so the anchor must be
    # exact rather than rely on an upstream invariant.
    return re.compile(f"^{compiled}\\Z")


def is_authorized_group_name(group_name: str) -> bool:
    """Return True iff ``group_name`` is matched by at least one pinned IAM pattern.

    Implements MSK IAM resource-pattern semantics: whole-name glob match, ``*`` as the
    only wildcard, ``.`` literal.

    Example:
        >>> is_authorized_group_name("onex-dev.omnimarket.delegate.consume.v1")
        True
        >>> is_authorized_group_name("pattern-b-broker-terminal-9f2c")
        True

        The OMN-15639 defect name contains ``onex.`` but does not begin with it, so a
        substring matcher would wrongly accept it:

        >>> is_authorized_group_name(
        ...     "runtime-local-HandlerDelegateSkill.__t."
        ...     "onex.cmd.omnimarket.delegate-skill.v1"
        ... )
        False
        >>> is_authorized_group_name("runtime-local-terminal")
        False

        The bare reserved prefix lacks the trailing separator the glob requires:

        >>> is_authorized_group_name("pattern-b-broker")
        False
    """
    if not group_name:
        return False
    return any(
        _compile_iam_glob(pattern).match(group_name) is not None
        for pattern in load_authorized_group_patterns()
    )


__all__: list[str] = [
    "DEFAULT_ENVIRONMENT",
    "ENVIRONMENT_ENV_VAR",
    "INSTANCE_SCOPE_INFIX",
    "KAFKA_CONSUMER_GROUP_MAX_LENGTH",
    "TOPIC_SCOPE_INFIX",
    "apply_instance_discriminator",
    "apply_topic_discriminator",
    "compute_consumer_group_id",
    "compute_pattern_set_digest",
    "derive_consumer_group_id",
    "derive_prefixed_group_id",
    "derive_service_group_id",
    "is_authorized_group_name",
    "load_authorized_group_patterns",
    "load_iam_pattern_document",
    "load_managed_environments",
    "normalize_kafka_identifier",
    "resolve_environment_token",
]
