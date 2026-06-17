# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Regression guards for the OMN-13197 dead intent-publisher path removal.

OMN-13197 (A-followup of OMN-13188 / OMN-12803 topic-authority family) removed
the ``onex.runtime.intents`` hardcoded topic at its root by deleting the dead
publisher path that was its sole consumer:

* ``MixinIntentPublisher`` had ZERO production call sites (never instantiated
  outside tests) and ``onex.runtime.intents`` had ZERO Kafka consumers
  (``IntentExecutor`` is a synchronous in-memory runtime service, not a topic
  subscriber). The topic was architecturally dead from both producer and
  consumer sides.
* The dedicated ``TOPIC_EVENT_PUBLISH_INTENT`` constant was a duplicate of the
  canonical ``TOPIC_RUNTIME_INTENTS`` derivation, existing only to feed the dead
  mixin. It could not be contract-sourced: no contract declares the topic and
  ``ServiceTopicRegistry`` lives in ``omnibase_infra`` (core cannot import it
  per layering).

These guards fail closed if the dead symbols are reintroduced.
"""

import importlib

import pytest


@pytest.mark.unit
def test_mixin_intent_publisher_module_removed() -> None:
    """The dead MixinIntentPublisher module must not be reintroduced."""
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("omnibase_core.mixins.mixin_intent_publisher")


@pytest.mark.unit
def test_mixin_intent_publisher_not_exported() -> None:
    """MixinIntentPublisher must not be exported from the mixins package."""
    mixins = importlib.import_module("omnibase_core.mixins")
    assert not hasattr(mixins, "MixinIntentPublisher")
    assert "MixinIntentPublisher" not in getattr(mixins, "__all__", [])


@pytest.mark.unit
def test_topic_event_publish_intent_constant_removed() -> None:
    """The duplicate TOPIC_EVENT_PUBLISH_INTENT constant must be removed.

    The canonical ``TOPIC_RUNTIME_INTENTS`` derivation stays; the special-purpose
    duplicate that fed the dead mixin is gone.
    """
    taxonomy = importlib.import_module(
        "omnibase_core.constants.constants_topic_taxonomy"
    )
    assert not hasattr(taxonomy, "TOPIC_EVENT_PUBLISH_INTENT")
    assert "TOPIC_EVENT_PUBLISH_INTENT" not in taxonomy.__all__
    # Canonical taxonomy derivation is retained.
    assert taxonomy.TOPIC_RUNTIME_INTENTS == "onex.runtime.intents"


@pytest.mark.unit
def test_topic_event_publish_intent_not_reexported() -> None:
    """No package may re-export the removed TOPIC_EVENT_PUBLISH_INTENT alias."""
    for module_path in (
        "omnibase_core.constants",
        "omnibase_core.models.events",
        "omnibase_core.models.events.model_intent_events",
    ):
        module = importlib.import_module(module_path)
        assert not hasattr(module, "TOPIC_EVENT_PUBLISH_INTENT"), module_path
        assert "TOPIC_EVENT_PUBLISH_INTENT" not in getattr(module, "__all__", [])


@pytest.mark.unit
def test_intent_publish_result_model_removed() -> None:
    """ModelIntentPublishResult (only used by the deleted mixin) is removed."""
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module(
            "omnibase_core.models.reducer.model_intent_publish_result"
        )
    reducer_pkg = importlib.import_module("omnibase_core.models.reducer")
    assert not hasattr(reducer_pkg, "ModelIntentPublishResult")
    assert "ModelIntentPublishResult" not in getattr(reducer_pkg, "__all__", [])


@pytest.mark.unit
def test_model_event_publish_intent_retained() -> None:
    """ModelEventPublishIntent stays — it has a live consumer (util_payload_migration)."""
    events = importlib.import_module("omnibase_core.models.events")
    assert hasattr(events, "ModelEventPublishIntent")
