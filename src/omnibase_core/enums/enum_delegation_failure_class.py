# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Delegation failure class enum for LLM cost routing taxonomy."""

from __future__ import annotations

from enum import StrEnum, unique


@unique
class EnumDelegationFailureClass(StrEnum):
    """Taxonomy of failure classes for LLM delegation escalation events."""

    MODEL_UNAVAILABLE = "model_unavailable"
    RATE_LIMITED = "rate_limited"
    TIMEOUT = "timeout"
    INVALID_JSON = "invalid_json"
    QUALITY_GATE_FAILED = "quality_gate_failed"
    RUBRIC_FAILED = "rubric_failed"
    CONTEXT_TOO_LARGE = "context_too_large"
    PRICING_UNKNOWN = "pricing_unknown"
    # The provider was reached and REJECTED the credential we presented: HTTP
    # 401/403, or a 200 body whose declared error names an auth condition. A
    # credential exists; the provider does not accept it.
    PROVIDER_AUTH_FAILED = "provider_auth_failed"
    # OMN-18696: the backend declares a credential and NO credential value could
    # be resolved for it, so no provider call was ever attempted. Distinct from
    # PROVIDER_AUTH_FAILED (a key exists and the provider rejected it) and from
    # MODEL_UNAVAILABLE (the route is unusable right now for reasons a retry may
    # clear). All three were previously indistinguishable on the bus-less local
    # path: a rejected key classified as MODEL_UNAVAILABLE, and an unresolvable
    # one fell through to UNKNOWN, so both were RETRYABLE and both escalated up
    # the tier ladder rather than refusing. A missing credential is a
    # configuration fact -- re-asking the same question, on this backend or a
    # higher one, cannot turn it into a present one.
    PROVIDER_CREDENTIAL_MISSING = "provider_credential_missing"
    # OMN-16419: the configured model_name is absent from the endpoint's live
    # GET /v1/models served ids. Distinct from MODEL_UNAVAILABLE (endpoint
    # unreachable/unhealthy) — this is a reachable, healthy endpoint serving a
    # DIFFERENT model than the one attributed in delegation receipts and
    # llm-call-completed events. Fails closed rather than silently attributing
    # to a model that is not running (e.g. SGLang echoing an unknown model
    # string back at HTTP 200).
    MODEL_ATTRIBUTION_MISMATCH = "model_attribution_mismatch"
    # OMN-18296: the process that owned an in-flight leg went away and the leg
    # was lost with it. Distinct from TIMEOUT, which is a provider that took too
    # long to answer a call we can still see: here no call is outstanding at all
    # — the inference command's consumer offset was already committed, so it is
    # never redelivered, and no response event, success or failure, will ever
    # arrive. Measured on the lab lane 2026-09-13: the effects pod was recreated
    # at 09:57:40Z with correlation a2fe0848 in flight since 09:55:04Z; the
    # request sat on the bus with no matching response, the FSM row stayed
    # ROUTED/in_flight, and the customer's delegation never terminalised.
    RUNTIME_RESTART_DURING_DELEGATION = "runtime_restart_during_delegation"
    # OMN-20157: the provider answered and said the MODEL this route names does
    # not exist or is not available to this key (HTTP 404, e.g. Google's "no
    # longer available to new users"). Distinct from MODEL_UNAVAILABLE, which is
    # the retryable "the endpoint could not be used right now" class: re-asking
    # the same backend for the same model cannot make it exist. A customer's
    # route re-resolves its model once from the provider's own model list, then
    # refuses with this class.
    PROVIDER_MODEL_NOT_FOUND = "provider_model_not_found"
    # OMN-20157: the provider answered and refused on the ACCOUNT's billing: HTTP
    # 402, or a body naming prepaid credits, a balance or billing (e.g. a new
    # Google project with no prepaid credits). On a customer's own key this is
    # the customer's bill (INV-098), so it is told to them plainly and never
    # retried: no retry and no other tier of theirs can add credit to an account.
    PROVIDER_BILLING = "provider_billing"
    UNKNOWN = "unknown"
