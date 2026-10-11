# SPDX-FileCopyrightText: 2026 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Topic constants for the Codex runtime request adapter."""

# OMN-12443: The stability runtime broker contract is the omnimarket Pattern B
# bridge. Keep explicit deployment overrides in runtime_client.py for older
# runtime targets, but default the Codex runbook path to the active broker.
TOPIC_CODEX_PATTERN_B_DISPATCH_COMMAND = "onex.cmd.omnimarket.pattern-b-dispatch.v1"  # onex-topic-allow: pending contract auto-wiring
TOPIC_CODEX_PATTERN_B_DISPATCH_COMPLETED = "onex.evt.omnimarket.pattern-b-dispatch-completed.v1"  # onex-topic-allow: pending contract auto-wiring
TOPIC_CODEX_DELEGATE_SKILL_COMMAND = "onex.cmd.omnimarket.delegate-skill.v1"  # onex-topic-allow: pending contract auto-wiring
TOPIC_CODEX_DELEGATE_SKILL_COMPLETED = "onex.evt.omnimarket.delegate-skill-completed.v1"  # onex-topic-allow: pending contract auto-wiring
TOPIC_CODEX_DELEGATE_SKILL_FAILED = "onex.evt.omnimarket.delegate-skill-failed.v1"  # onex-topic-allow: pending contract auto-wiring
