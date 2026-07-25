## OMN-13197 — Remove the `onex.runtime.intents` hardcoded topic + dead intent-publisher path

A-followup of **OMN-13188** (the **OMN-12803** "all topics/URLs from contracts only" family). Tracked separately per Q3 of the platform-debt plan so it does not block the A1–A5 sequence.

### Decision (per DoD: contract-source the topic OR confirm-and-delete the dead path)

**Confirm-and-delete the dead path.** The topic could **not** be contract-sourced:

- No contract anywhere declares `onex.runtime.intents` (`find ... contract.yaml -exec grep onex.runtime.intents` → no matches). The `contracts/intent_publisher.yaml` referenced in the mixin docstring was **never authored** (phantom reference).
- `ServiceTopicRegistry` (the contract-topic resolution mechanism) lives in `omnibase_infra`; `omnibase_core` cannot import it (repo layering: compat → core → spi → infra).

The mechanism was **architecturally dead from both sides** (verified in OMN-13188 / OMN-13192):

- `MixinIntentPublisher` — the **sole** publisher — had **ZERO production call sites** (never instantiated outside tests).
- `onex.runtime.intents` had **ZERO Kafka consumers**: `IntentExecutor` is a synchronous in-memory runtime service called from `ServiceDispatchResultApplier`, not a topic subscriber.

Per doctrine, a dead mechanism is debt to **delete**, not park / guard / migrate.

### Changed

**Removed**
- `TOPIC_EVENT_PUBLISH_INTENT` — a duplicate of the canonical `TOPIC_RUNTIME_INTENTS` (both `= topic_name(DOMAIN_RUNTIME, TOPIC_TYPE_INTENTS)`), existing only to feed the dead mixin — plus all re-exports (`constants/__init__.py`, `models/events/__init__.py`, `models/events/model_intent_events.py`).
- `MixinIntentPublisher` (`mixins/mixin_intent_publisher.py`) + its capability-mapping and metadata-census entries + mixins `__init__` export.
- `ModelIntentPublishResult` (`models/reducer/model_intent_publish_result.py`) — only consumer was the deleted mixin — + reducer `__init__` export.
- Dead tests + fixtures (`test_mixin_intent_publisher.py`, `test_intent_publisher_integration.py`, `test_model_intent_publish_result.py`, `fixture_intent_publisher.py`, `INTENT_PUBLISHER_TEST_SUMMARY.md`).
- Intent-publisher guide docs that documented the removed mechanism (`09_TESTING_INTENT_PUBLISHER.md`, `INTENT_PUBLISHER_TESTING_DOCUMENTATION.md`) + all inbound links (node-building tutorials, guides README, topic-taxonomy standard).

**Retained**
- `TOPIC_RUNTIME_INTENTS` — the canonical taxonomy derivation (`onex.runtime.intents`), part of the public `__all__`.
- `ModelEventPublishIntent` — has a live consumer in `utils/util_payload_migration.py`; docstring examples retargeted to `TOPIC_RUNTIME_INTENTS`.

**Added**
- `tests/unit/mixins/test_intent_publisher_removed.py` — regression guard asserting the dead symbols stay removed and the retained ones survive (TDD: red → green).

### dod_evidence
- `uv run ruff format src/ tests/` → 5567 files unchanged; `uv run ruff check --fix src/ tests/` → All checks passed.
- `uv run mypy src/ --strict` → 0 errors on all changed files. (6 pre-existing errors remain in untouched files: `contract_loader.py`, `cli_install.py`, `model_onex_container.py` — verified present on `dev` base, not introduced here.)
- Focused tests: `test_intent_publisher_removed.py` + `test_constants_topic_taxonomy.py` + `test_validator_hardcoded_topics.py` + `test_model_event_publish_intent.py` → **171 passed**. Full collection of `tests/unit/models` + reducer + events + intents → **1389 tests collected, 0 import errors**.
- `pre-commit run` on all changed files → **all hooks PASS** (markdown-link validation PASS after doc cleanup; deterministic-skill-routing PASS against the omniclaude `main` snapshot — the only fail was a sibling-clone-on-dev artifact unrelated to this diff).

### Receipt / OCC
- Evidence-Source: `2322a07e139c35bbd85f131395ce07ec44200713`
- Evidence-Ticket: OMN-13197

Paired OCC receipt PR: contracts/OMN-13197.yaml + drift/dod_receipts/OMN-13197/... (linked below).

Cross-reference: OMN-12803, OMN-13188, OMN-13192.


Paired OCC receipt PR: https://github.com/OmniNode-ai/onex_change_control/pull/2706
