# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
ServiceRiskGate — enforce risk-level gating before CLI command dispatch.

The risk gate is the safety layer between argument parsing and command dispatch.
It MUST execute before any argument validation side effects and before any
call to ``ServiceCommandDispatcher.dispatch()``.

## Risk Level Semantics

    LOW    → GateResultProceed (no gate, dispatch immediately)
    MEDIUM → GateResultPromptConfirmation (confirmation prompt, default No)
    HIGH   → GateResultHITLRequired (one approval token required)
    CRITICAL → GateResultDualApprovalRequired (two distinct principal tokens)

## Integration Contract

    # In ServiceCommandDispatcher.dispatch():
    gate = ServiceRiskGate(validator=ServiceApprovalTokenValidator())
    result = gate.evaluate(command, parsed_args)
    if isinstance(result, GateResultProceed):
        # dispatch
    elif isinstance(result, GateResultPromptConfirmation):
        # prompt user for confirmation
    elif isinstance(result, GateResultHITLRequired):
        # request approval token from user
    elif isinstance(result, GateResultDualApprovalRequired):
        # request two approval tokens from two principals

## Logging

Every evaluate() call emits a structured log event recording:
    - command_ref
    - risk level
    - gate outcome
    - timestamp

This log is the audit trail required by the risk gate safety specification.

## Token Replay Prevention

ServiceRiskGate tracks used ``jti`` values in an in-process set. Tokens with
a previously seen ``jti`` are rejected with ``rejection_reason="Token replayed"``.
The replay set is scoped to the lifetime of the ServiceRiskGate instance.

## No Bypasses

There are no ``--force`` or ``--skip-risk-check`` flags. Risk gating is
unconditional. The only way to bypass gating is to modify the command's
``risk`` field in the contributing node's contract — which requires a signed
contract update from the publisher.

.. versionadded:: 0.20.0  (OMN-2562)
"""

from __future__ import annotations

import threading
from argparse import Namespace
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from omnibase_core.enums.enum_cli_command_risk import EnumCliCommandRisk
from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.enums.enum_risk_gate_outcome import EnumRiskGateOutcome
from omnibase_core.logging.logging_structured import (
    emit_log_event_sync as emit_log_event,
)
from omnibase_core.models.cli.model_gate_result_dual_approval_required import (
    GateResultDualApprovalRequired,
)
from omnibase_core.models.cli.model_gate_result_hitl_required import (
    GateResultHITLRequired,
)
from omnibase_core.models.cli.model_gate_result_proceed import GateResultProceed
from omnibase_core.models.cli.model_gate_result_prompt_confirmation import (
    GateResultPromptConfirmation,
)
from omnibase_core.models.cli.model_risk_gate_result import GateResult

if TYPE_CHECKING:
    from omnibase_core.models.contracts.model_cli_command_entry import (
        ModelCliCommandEntry,
    )
    from omnibase_core.services.cli.service_approval_token_validator import (
        ServiceApprovalTokenValidator,
    )

__all__ = ["ServiceRiskGate"]

# Approval challenge displayed to users requesting HIGH/CRITICAL-risk commands.
_HITL_CHALLENGE_MESSAGE = (
    "This command is classified HIGH-risk and requires an approval token.\n"
    "To obtain an approval token:\n"
    "  1. Visit the ONEX approval portal or use your approval workflow.\n"
    "  2. Request approval for command: {command_ref}\n"
    "  3. Provide the token via: --approval-token <token>\n"
    "     or when prompted interactively."
)

_DUAL_APPROVAL_CHALLENGE_MESSAGE = (
    "This command is classified CRITICAL-risk and requires two separate approval tokens\n"
    "from two distinct principals.\n"
    "To obtain approval tokens:\n"
    "  1. Each approver must independently request a token for: {command_ref}\n"
    "  2. Provide both tokens via:\n"
    "     --approval-token <token1> --approval-token2 <token2>\n"
    "     or when prompted interactively."
)


class ServiceRiskGate:
    """Enforce risk-level gating before CLI command dispatch.

    Stateful: tracks used token JTIs in memory to reject replayed tokens.
    The JTI set is scoped to the lifetime of this instance.

    Args:
        validator: Approval token validator. If not provided, a new
            ``ServiceApprovalTokenValidator`` is instantiated with default
            (Phase 1) configuration.

    Thread Safety:
        ``evaluate()`` is thread-safe — JTI tracking uses a mutex.

    Example::

        gate = ServiceRiskGate()
        result = gate.evaluate(command_entry, parsed_args)
        if isinstance(result, GateResultProceed):
            dispatcher.dispatch(command_entry, parsed_args)
        elif isinstance(result, GateResultPromptConfirmation):
            answer = input(result.prompt_message + " [y/N] ").strip().lower()
            if answer == "y":
                dispatcher.dispatch(command_entry, parsed_args)

    .. versionadded:: 0.20.0  (OMN-2562)
    """

    def __init__(
        self,
        validator: ServiceApprovalTokenValidator | None = None,
    ) -> None:
        """Initialize ServiceRiskGate.

        Args:
            validator: Token validator. Defaults to ``ServiceApprovalTokenValidator()``.
        """
        if validator is None:
            from omnibase_core.services.cli.service_approval_token_validator import (
                ServiceApprovalTokenValidator,
            )

            validator = ServiceApprovalTokenValidator()

        self._validator = validator
        self._used_jtis: set[str] = set()
        self._lock = threading.Lock()

    def evaluate(
        self,
        command: ModelCliCommandEntry,
        parsed_args: Namespace,
    ) -> GateResult:
        """Evaluate the risk gate for a command invocation.

        This is the primary entry point. The dispatcher MUST call this before
        any dispatch attempt.

        Args:
            command: The command entry from the catalog.
            parsed_args: The parsed argument namespace from ``ArgumentParser``.

        Returns:
            A ``GateResult`` variant describing what the CLI must do next:
            - ``GateResultProceed``: dispatch immediately.
            - ``GateResultPromptConfirmation``: show y/N prompt.
            - ``GateResultHITLRequired``: collect and validate one token.
            - ``GateResultDualApprovalRequired``: collect and validate two tokens.
        """
        risk = command.risk
        command_ref = command.id

        if risk == EnumCliCommandRisk.LOW:
            result: GateResult = GateResultProceed(
                command_ref=command_ref,
                risk=risk,
            )
            self._log_gate_decision(command_ref, risk, EnumRiskGateOutcome.PROCEED)
            return result

        if risk == EnumCliCommandRisk.MEDIUM:
            result = GateResultPromptConfirmation(
                command_ref=command_ref,
                risk=risk,
                prompt_message=(
                    f"Command '{command_ref}' is classified MEDIUM-risk. Proceed?"
                ),
            )
            self._log_gate_decision(
                command_ref, risk, EnumRiskGateOutcome.CONFIRMATION_REQUIRED
            )
            return result

        if risk == EnumCliCommandRisk.HIGH:
            # Check if approval token provided in args
            approval_token: str | None = getattr(parsed_args, "approval_token", None)
            if approval_token:
                return self._validate_single_token(
                    command_ref=command_ref,
                    risk=risk,
                    token=approval_token,
                )

            result = GateResultHITLRequired(
                command_ref=command_ref,
                risk=risk,
                challenge_message=_HITL_CHALLENGE_MESSAGE.format(
                    command_ref=command_ref
                ),
            )
            self._log_gate_decision(
                command_ref, risk, EnumRiskGateOutcome.HITL_TOKEN_REQUIRED
            )
            return result

        if risk == EnumCliCommandRisk.CRITICAL:
            # Check if two approval tokens provided in args
            approval_token1: str | None = getattr(parsed_args, "approval_token", None)
            approval_token2: str | None = getattr(parsed_args, "approval_token2", None)
            if approval_token1 and approval_token2:
                return self._validate_dual_tokens(
                    command_ref=command_ref,
                    risk=risk,
                    token1=approval_token1,
                    token2=approval_token2,
                )

            result = GateResultDualApprovalRequired(
                command_ref=command_ref,
                risk=risk,
                challenge_message=_DUAL_APPROVAL_CHALLENGE_MESSAGE.format(
                    command_ref=command_ref
                ),
            )
            self._log_gate_decision(
                command_ref, risk, EnumRiskGateOutcome.DUAL_APPROVAL_REQUIRED
            )
            return result

        # Unreachable if EnumCliCommandRisk is exhaustive, but defensive fallthrough
        self._log_gate_decision(command_ref, risk, EnumRiskGateOutcome.PROCEED)
        return GateResultProceed(command_ref=command_ref, risk=risk)

    def evaluate_confirmation_response(
        self,
        command: ModelCliCommandEntry,
        confirmed: bool,
    ) -> GateResult:
        """Process user response to a MEDIUM-risk confirmation prompt.

        Called after displaying the ``GateResultPromptConfirmation`` message
        and collecting the user's response.

        Args:
            command: The command entry from the catalog.
            confirmed: ``True`` if the user responded "yes"; ``False`` otherwise.

        Returns:
            ``GateResultProceed`` if confirmed, ``GateResultPromptConfirmation``
            with an updated outcome if rejected.
        """
        command_ref = command.id
        risk = command.risk

        if confirmed:
            self._log_gate_decision(command_ref, risk, EnumRiskGateOutcome.CONFIRMED)
            return GateResultProceed(command_ref=command_ref, risk=risk)

        self._log_gate_decision(command_ref, risk, EnumRiskGateOutcome.REJECTED)
        return GateResultPromptConfirmation(
            command_ref=command_ref,
            risk=risk,
            prompt_message="Cancelled by user.",
            outcome=EnumRiskGateOutcome.REJECTED,
        )

    def validate_hitl_token(
        self,
        command: ModelCliCommandEntry,
        token: str,
    ) -> GateResult:
        """Validate a single HITL approval token for a HIGH-risk command.

        Called after the user provides the approval token in response to
        a ``GateResultHITLRequired`` result.

        Args:
            command: The command entry from the catalog.
            token: The approval token string provided by the user.

        Returns:
            ``GateResultProceed`` if the token is valid,
            ``GateResultHITLRequired`` with updated outcome if invalid.
        """
        return self._validate_single_token(
            command_ref=command.id,
            risk=command.risk,
            token=token,
        )

    def validate_dual_approval_tokens(
        self,
        command: ModelCliCommandEntry,
        token1: str,
        token2: str,
    ) -> GateResult:
        """Validate two HITL approval tokens for a CRITICAL-risk command.

        Both tokens must be valid and from distinct principals.

        Args:
            command: The command entry from the catalog.
            token1: First approval token.
            token2: Second approval token.

        Returns:
            ``GateResultProceed`` if both tokens are valid and from distinct
            principals. ``GateResultDualApprovalRequired`` with updated outcome
            if validation fails.
        """
        return self._validate_dual_tokens(
            command_ref=command.id,
            risk=command.risk,
            token1=token1,
            token2=token2,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _validate_single_token(
        self,
        *,
        command_ref: str,
        risk: EnumCliCommandRisk,
        token: str,
    ) -> GateResult:
        """Validate one approval token and return the gate result.

        Args:
            command_ref: Command reference being gated.
            risk: Risk level (must be HIGH).
            token: The approval token to validate.

        Returns:
            ``GateResultProceed`` on success or ``GateResultHITLRequired``
            with outcome ``HITL_TOKEN_INVALID`` on failure.
        """
        result = self._validator.validate(token=token, command_ref=command_ref)

        if not result.valid:
            self._log_gate_decision(
                command_ref, risk, EnumRiskGateOutcome.HITL_TOKEN_INVALID
            )
            return GateResultHITLRequired(
                command_ref=command_ref,
                risk=risk,
                challenge_message=(
                    f"Token rejected: {result.rejection_reason}\n"
                    "Please obtain a new approval token and try again."
                ),
                outcome=EnumRiskGateOutcome.HITL_TOKEN_INVALID,
            )

        # Replay check
        if result.token_jti is not None:
            with self._lock:
                if result.token_jti in self._used_jtis:
                    self._log_gate_decision(
                        command_ref, risk, EnumRiskGateOutcome.HITL_TOKEN_INVALID
                    )
                    return GateResultHITLRequired(
                        command_ref=command_ref,
                        risk=risk,
                        challenge_message=(
                            "Token already used (replay detected). "
                            "Obtain a new approval token."
                        ),
                        outcome=EnumRiskGateOutcome.HITL_TOKEN_INVALID,
                    )
                self._used_jtis.add(result.token_jti)

        self._log_gate_decision(command_ref, risk, EnumRiskGateOutcome.HITL_TOKEN_VALID)
        return GateResultProceed(command_ref=command_ref, risk=risk)

    def _validate_dual_tokens(
        self,
        *,
        command_ref: str,
        risk: EnumCliCommandRisk,
        token1: str,
        token2: str,
    ) -> GateResult:
        """Validate two approval tokens for a CRITICAL-risk command.

        Both tokens must be valid, from distinct principals, and not replayed.

        Args:
            command_ref: Command reference being gated.
            risk: Risk level (must be CRITICAL).
            token1: First approval token.
            token2: Second approval token.

        Returns:
            ``GateResultProceed`` on success or ``GateResultDualApprovalRequired``
            with outcome ``DUAL_APPROVAL_INVALID`` on failure.
        """
        result1 = self._validator.validate(token=token1, command_ref=command_ref)
        result2 = self._validator.validate(token=token2, command_ref=command_ref)

        # Both must be valid
        if not result1.valid:
            self._log_gate_decision(
                command_ref, risk, EnumRiskGateOutcome.DUAL_APPROVAL_INVALID
            )
            return GateResultDualApprovalRequired(
                command_ref=command_ref,
                risk=risk,
                challenge_message=(
                    f"First approval token rejected: {result1.rejection_reason}"
                ),
                outcome=EnumRiskGateOutcome.DUAL_APPROVAL_INVALID,
            )

        if not result2.valid:
            self._log_gate_decision(
                command_ref, risk, EnumRiskGateOutcome.DUAL_APPROVAL_INVALID
            )
            return GateResultDualApprovalRequired(
                command_ref=command_ref,
                risk=risk,
                challenge_message=(
                    f"Second approval token rejected: {result2.rejection_reason}"
                ),
                outcome=EnumRiskGateOutcome.DUAL_APPROVAL_INVALID,
            )

        # Both principals must be distinct
        if result1.principal == result2.principal:
            self._log_gate_decision(
                command_ref, risk, EnumRiskGateOutcome.DUAL_APPROVAL_INVALID
            )
            return GateResultDualApprovalRequired(
                command_ref=command_ref,
                risk=risk,
                challenge_message=(
                    "Both tokens are from the same principal. "
                    "CRITICAL commands require two distinct approvers."
                ),
                outcome=EnumRiskGateOutcome.DUAL_APPROVAL_INVALID,
            )

        # Replay check for both tokens
        jtis_to_check = {
            jti for jti in [result1.token_jti, result2.token_jti] if jti is not None
        }
        with self._lock:
            for jti in jtis_to_check:
                if jti in self._used_jtis:
                    self._log_gate_decision(
                        command_ref, risk, EnumRiskGateOutcome.DUAL_APPROVAL_INVALID
                    )
                    return GateResultDualApprovalRequired(
                        command_ref=command_ref,
                        risk=risk,
                        challenge_message=(
                            f"Token with jti '{jti}' already used (replay detected). "
                            "Obtain new approval tokens."
                        ),
                        outcome=EnumRiskGateOutcome.DUAL_APPROVAL_INVALID,
                    )
            self._used_jtis.update(jtis_to_check)

        self._log_gate_decision(
            command_ref, risk, EnumRiskGateOutcome.DUAL_APPROVAL_VALID
        )
        return GateResultProceed(command_ref=command_ref, risk=risk)

    @staticmethod
    def _log_gate_decision(
        command_ref: str,
        risk: EnumCliCommandRisk,
        outcome: EnumRiskGateOutcome,
    ) -> None:
        """Emit a structured log event recording the gate decision.

        This is the audit trail for risk gate decisions. Every evaluate()
        call produces exactly one log event.

        Args:
            command_ref: The command reference being evaluated.
            risk: The risk level of the command.
            outcome: The gate outcome.
        """
        emit_log_event(
            LogLevel.INFO,
            f"Risk gate decision: command={command_ref} risk={risk.value} outcome={outcome.value}",
            {
                "component": "ServiceRiskGate",
                "command_ref": command_ref,
                "risk_level": risk.value,
                "gate_outcome": outcome.value,
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )
