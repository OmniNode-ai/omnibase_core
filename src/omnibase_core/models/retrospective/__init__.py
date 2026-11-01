# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed models of the weekly retrospective and its deterministic evaluator (OMN-21627).

One model per crossing of the retrospective graph, written before any handler
(contracts and seams first, operator ruling about 2026-10-31T02:25Z):

* run open (command into the orchestrator) and collect request (orchestrator to collector);
* skill run result (R1, R2, R3 skill into its seam) and evidence record (seam to collector);
* success contract and evidence snapshot (collector to evaluator);
* experiment verdict and verdict set (evaluator to reducer);
* run state (reducer to projection) and run projected (projection to orchestrator);
* digest request (orchestrator to digest) and digest with experiment cards (digest out).

Import concrete symbols from their modules directly.
"""
