# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for the canonical consumer-group derivation utility (OMN-15639).

The authorization-conformance assertions live in
``tests/gates/test_consumer_group_name_authorization.py``. This module covers the
derivation mechanics themselves: normalization, truncation determinism, idempotent
scope infixes, and byte-compatibility with the ``omnibase_infra`` implementation this
module replaces as the single canonical home.
"""

from __future__ import annotations

import hashlib
from uuid import UUID

import pytest

from omnibase_core.enums.enum_consumer_group_purpose import EnumConsumerGroupPurpose
from omnibase_core.enums.enum_reserved_group_prefix import EnumReservedGroupPrefix
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.event_bus.util_consumer_group import (
    DEFAULT_ENVIRONMENT,
    KAFKA_CONSUMER_GROUP_MAX_LENGTH,
    apply_instance_discriminator,
    apply_topic_discriminator,
    compute_consumer_group_id,
    compute_pattern_set_digest,
    derive_consumer_group_id,
    derive_prefixed_group_id,
    derive_service_group_id,
    normalize_kafka_identifier,
    resolve_environment_token,
)
from omnibase_core.models.event_bus.model_consumer_group_scope import (
    ModelConsumerGroupScope,
)

_CORRELATION = UUID("9f2c0000-0000-4000-8000-000000000000")


def _identity(**overrides: str) -> dict[str, str]:
    """The four canonical identity components, as keyword arguments."""
    fields = {
        "env": "onex-dev",
        "service": "omnimarket",
        "node_name": "delegate_skill",
        "version": "v1",
    }
    fields.update(overrides)
    return fields


# ---------------------------------------------------------------------------
# normalize_kafka_identifier
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("My Service!!", "my_service"),
        ("foo..bar__baz", "foo.bar_baz"),
        ("  UPPER_Case-Test  ", "upper_case-test"),
        ("valid.consumer-group_id", "valid.consumer-group_id"),
        ("---leading-and-trailing---", "leading-and-trailing"),
    ],
)
def test_normalize_matches_documented_rules(raw: str, expected: str) -> None:
    assert normalize_kafka_identifier(raw) == expected


@pytest.mark.unit
@pytest.mark.parametrize("raw", ["", "@#$%^&*()", "..."])
def test_normalize_rejects_empty_result(raw: str) -> None:
    with pytest.raises(ModelOnexError):
        normalize_kafka_identifier(raw)


@pytest.mark.unit
def test_normalize_truncation_is_deterministic_and_hashes_the_raw_input() -> None:
    """Truncation hashes the PRE-normalization value.

    Byte-compatible with the infra implementation this replaces. Hashing the
    normalized form instead would collide two distinct inputs that normalize to the
    same 246-char prefix.
    """
    raw = "A" * 300
    result = normalize_kafka_identifier(raw)
    assert len(result) == KAFKA_CONSUMER_GROUP_MAX_LENGTH
    expected_suffix = hashlib.sha256(raw.encode()).hexdigest()[:8]
    assert result == f"{'a' * 246}_{expected_suffix}"
    assert normalize_kafka_identifier(raw) == result


# ---------------------------------------------------------------------------
# compute_consumer_group_id
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_canonical_format_and_component_order() -> None:
    assert (
        compute_consumer_group_id(**_identity())
        == "onex-dev.omnimarket.delegate_skill.consume.v1"
    )


@pytest.mark.unit
def test_purpose_is_a_component() -> None:
    assert (
        compute_consumer_group_id(
            **_identity(), purpose=EnumConsumerGroupPurpose.INTROSPECTION
        )
        == "onex-dev.omnimarket.delegate_skill.introspection.v1"
    )


@pytest.mark.unit
def test_components_are_normalized() -> None:
    assert (
        compute_consumer_group_id(
            **_identity(env="DEV", service="Omni Intelligence", version="V1.0.0")
        )
        == "dev.omni_intelligence.delegate_skill.consume.v1.0.0"
    )


@pytest.mark.unit
def test_long_identity_truncates_with_pipe_joined_hash() -> None:
    """Truncation hash input is ``env|service|node|purpose|version``.

    Pinned because ``omnibase_infra`` used exactly this input; a different join would
    silently rename every over-long group when infra switches to this module.
    """
    identity = _identity(env="development", service="a" * 150, node_name="b" * 150)
    result = compute_consumer_group_id(**identity)
    assert len(result) == KAFKA_CONSUMER_GROUP_MAX_LENGTH
    expected_suffix = hashlib.sha256(
        f"development|{'a' * 150}|{'b' * 150}|consume|v1".encode()
    ).hexdigest()[:8]
    assert result.endswith(f"_{expected_suffix}")


# ---------------------------------------------------------------------------
# scope infixes
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_instance_discriminator_is_idempotent() -> None:
    base = "onex-dev.svc.node.consume.v1"
    once = apply_instance_discriminator(base, "pod-7")
    assert once == f"{base}.__i.pod-7"
    assert apply_instance_discriminator(once, "pod-7") == once


@pytest.mark.unit
@pytest.mark.parametrize("blank", [None, "", "   "])
def test_blank_discriminators_are_no_ops(blank: str | None) -> None:
    base = "onex-dev.svc.node.consume.v1"
    assert apply_instance_discriminator(base, blank) == base
    assert apply_topic_discriminator(base, blank) == base


@pytest.mark.unit
def test_topic_and_instance_scopes_compose_in_a_fixed_order() -> None:
    derived = derive_consumer_group_id(
        **_identity(),
        scope=ModelConsumerGroupScope(
            topic="onex.cmd.omnimarket.delegate-skill.v1",
            ephemeral_tag="terminal",
            correlation_id=_CORRELATION,
        ),
    )
    assert derived == (
        "onex-dev.omnimarket.delegate_skill.consume.v1"
        ".__t.onex.cmd.omnimarket.delegate-skill.v1"
        f".__i.terminal-{_CORRELATION}"
    )


@pytest.mark.unit
def test_scope_none_and_empty_scope_agree() -> None:
    assert derive_consumer_group_id(**_identity()) == derive_consumer_group_id(
        **_identity(), scope=ModelConsumerGroupScope()
    )


@pytest.mark.unit
def test_discriminator_tokens_skip_blanks_and_keep_order() -> None:
    scope = ModelConsumerGroupScope(
        ephemeral_tag="  terminal  ",
        correlation_id=_CORRELATION,
        instance_token="",
    )
    assert scope.discriminator_tokens() == ("terminal", str(_CORRELATION))
    assert not scope.is_empty()
    assert ModelConsumerGroupScope().is_empty()


# ---------------------------------------------------------------------------
# reserved prefixes
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_reserved_prefix_reproduces_the_seam_example() -> None:
    assert (
        derive_prefixed_group_id(
            EnumReservedGroupPrefix.PATTERN_B_BROKER,
            ModelConsumerGroupScope(
                ephemeral_tag="terminal", correlation_id=_CORRELATION
            ),
        )
        == f"pattern-b-broker-terminal-{_CORRELATION}"
    )


@pytest.mark.unit
def test_dotted_reserved_prefix_uses_a_dot_separator() -> None:
    assert (
        derive_prefixed_group_id(
            EnumReservedGroupPrefix.LOCAL_RUNTIME_CONFIG,
            ModelConsumerGroupScope(ephemeral_tag="ingress"),
        )
        == "local.runtime_config.ingress"
    )


@pytest.mark.unit
def test_reserved_prefix_requires_scope() -> None:
    with pytest.raises(ModelOnexError, match="requires a non-empty scope"):
        derive_prefixed_group_id(
            EnumReservedGroupPrefix.PHASE5_MSK_SMOKE, ModelConsumerGroupScope()
        )


# ---------------------------------------------------------------------------
# environment resolution
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_environment_defaults_to_local_when_unset_or_blank(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An unset ENVIRONMENT must not masquerade as a managed environment."""
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    assert resolve_environment_token() == DEFAULT_ENVIRONMENT
    monkeypatch.setenv("ENVIRONMENT", "   ")
    assert resolve_environment_token() == DEFAULT_ENVIRONMENT


@pytest.mark.unit
def test_environment_is_read_and_normalized(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "ONEX-Dev")
    assert resolve_environment_token() == "onex-dev"
    assert derive_service_group_id("node", service="svc").startswith("onex-dev.")


# ---------------------------------------------------------------------------
# pin digest
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_pattern_set_digest_has_no_trailing_newline() -> None:
    """Pinned because the digest is the drift detector for the IAM mirror."""
    patterns = ("a", "b")
    assert compute_pattern_set_digest(patterns) == (hashlib.sha256(b"a\nb").hexdigest())
