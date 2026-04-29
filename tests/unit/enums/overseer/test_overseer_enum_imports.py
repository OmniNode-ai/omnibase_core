# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Assert all 14 overseer enums exist at the new core path."""

import pytest


@pytest.mark.unit
class TestOverseerEnumImports:
    def test_enum_artifact_store_action_import(self) -> None:
        from omnibase_core.enums.overseer.enum_artifact_store_action import (
            EnumArtifactStoreAction,
        )

        assert EnumArtifactStoreAction.UPLOAD == "UPLOAD"
        assert EnumArtifactStoreAction.DOWNLOAD == "DOWNLOAD"
        assert EnumArtifactStoreAction.DELETE == "DELETE"
        assert EnumArtifactStoreAction.LIST == "LIST"
        assert EnumArtifactStoreAction.EXISTS == "EXISTS"
        assert EnumArtifactStoreAction.GET_METADATA == "GET_METADATA"
        assert EnumArtifactStoreAction.COPY == "COPY"
        assert EnumArtifactStoreAction.MOVE == "MOVE"

    def test_enum_capability_tier_import(self) -> None:
        from omnibase_core.enums.overseer.enum_capability_tier import EnumCapabilityTier

        assert EnumCapabilityTier.C0 == "C0"
        assert EnumCapabilityTier.C4 == "C4"
        assert EnumCapabilityTier.C0 < EnumCapabilityTier.C4

    def test_enum_code_repository_action_import(self) -> None:
        from omnibase_core.enums.overseer.enum_code_repository_action import (
            EnumCodeRepositoryAction,
        )

        assert EnumCodeRepositoryAction.CLONE == "CLONE"
        assert EnumCodeRepositoryAction.PUSH == "PUSH"
        assert EnumCodeRepositoryAction.CREATE_PULL_REQUEST == "CREATE_PULL_REQUEST"

    def test_enum_context_bundle_level_import(self) -> None:
        from omnibase_core.enums.overseer.enum_context_bundle_level import (
            EnumContextBundleLevel,
        )

        assert EnumContextBundleLevel.L0 == "L0"
        assert EnumContextBundleLevel.L4 == "L4"
        assert EnumContextBundleLevel.L0 < EnumContextBundleLevel.L4

    def test_enum_event_bus_action_import(self) -> None:
        from omnibase_core.enums.overseer.enum_event_bus_action import (
            EnumEventBusAction,
        )

        assert EnumEventBusAction.PUBLISH == "PUBLISH"
        assert EnumEventBusAction.SUBSCRIBE == "SUBSCRIBE"
        assert EnumEventBusAction.DRAIN == "DRAIN"

    def test_enum_failure_class_import(self) -> None:
        from omnibase_core.enums.overseer.enum_failure_class import EnumFailureClass

        assert EnumFailureClass.TRANSIENT == "transient"
        assert EnumFailureClass.PERMANENT == "permanent"
        assert EnumFailureClass.UNKNOWN == "unknown"

    def test_enum_llm_provider_action_import(self) -> None:
        from omnibase_core.enums.overseer.enum_llm_provider_action import (
            EnumLLMProviderAction,
        )

        assert EnumLLMProviderAction.COMPLETE == "COMPLETE"
        assert EnumLLMProviderAction.CHAT == "CHAT"
        assert EnumLLMProviderAction.EMBED == "EMBED"

    def test_enum_notification_action_import(self) -> None:
        from omnibase_core.enums.overseer.enum_notification_action import (
            EnumNotificationAction,
        )

        assert EnumNotificationAction.SEND == "SEND"
        assert EnumNotificationAction.SEND_ALERT == "SEND_ALERT"
        assert EnumNotificationAction.RESOLVE == "RESOLVE"

    def test_enum_process_runner_state_import(self) -> None:
        from omnibase_core.enums.overseer.enum_process_runner_state import (
            EnumProcessRunnerState,
        )

        assert EnumProcessRunnerState.IDLE == "idle"
        assert EnumProcessRunnerState.COMPLETED == "completed"
        assert EnumProcessRunnerState.FAILED_TERMINAL == "failed_terminal"

    def test_enum_provider_import(self) -> None:
        from omnibase_core.enums.overseer.enum_provider import EnumProvider

        assert EnumProvider.ANTHROPIC == "anthropic"
        assert EnumProvider.LOCAL == "local"
        assert EnumProvider.UNKNOWN == "unknown"

    def test_enum_retry_type_import(self) -> None:
        from omnibase_core.enums.overseer.enum_retry_type import EnumRetryType

        assert EnumRetryType.NONE == "none"
        assert EnumRetryType.BACKOFF == "backoff"
        assert EnumRetryType.ESCALATE == "escalate"

    def test_enum_risk_level_import(self) -> None:
        from omnibase_core.enums.overseer.enum_risk_level import EnumRiskLevel

        assert EnumRiskLevel.LOW == "low"
        assert EnumRiskLevel.CRITICAL == "critical"

    def test_enum_ticket_service_action_import(self) -> None:
        from omnibase_core.enums.overseer.enum_ticket_service_action import (
            EnumTicketServiceAction,
        )

        assert EnumTicketServiceAction.CREATE_ISSUE == "CREATE_ISSUE"
        assert EnumTicketServiceAction.TRANSITION_STATUS == "TRANSITION_STATUS"
        assert EnumTicketServiceAction.LINK_ISSUES == "LINK_ISSUES"

    def test_enum_verifier_verdict_import(self) -> None:
        from omnibase_core.enums.overseer.enum_verifier_verdict import (
            EnumVerifierVerdict,
        )

        assert EnumVerifierVerdict.PASS == "PASS"
        assert EnumVerifierVerdict.FAIL == "FAIL"
        assert EnumVerifierVerdict.ESCALATE == "ESCALATE"

    def test_overseer_namespace_init_imports(self) -> None:
        from omnibase_core.enums.overseer import (
            EnumArtifactStoreAction,
            EnumCapabilityTier,
            EnumCodeRepositoryAction,
            EnumContextBundleLevel,
            EnumEventBusAction,
            EnumFailureClass,
            EnumLLMProviderAction,
            EnumNotificationAction,
            EnumProcessRunnerState,
            EnumProvider,
            EnumRetryType,
            EnumRiskLevel,
            EnumTicketServiceAction,
            EnumVerifierVerdict,
        )

        assert EnumArtifactStoreAction.UPLOAD == "UPLOAD"
        assert EnumCapabilityTier.C0 == "C0"
        assert EnumCodeRepositoryAction.CLONE == "CLONE"
        assert EnumContextBundleLevel.L0 == "L0"
        assert EnumEventBusAction.PUBLISH == "PUBLISH"
        assert EnumFailureClass.TRANSIENT == "transient"
        assert EnumLLMProviderAction.COMPLETE == "COMPLETE"
        assert EnumNotificationAction.SEND == "SEND"
        assert EnumProcessRunnerState.IDLE == "idle"
        assert EnumProvider.ANTHROPIC == "anthropic"
        assert EnumRetryType.NONE == "none"
        assert EnumRiskLevel.LOW == "low"
        assert EnumTicketServiceAction.CREATE_ISSUE == "CREATE_ISSUE"
        assert EnumVerifierVerdict.PASS == "PASS"
