# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Canonical experiment-telemetry models (OMN-13613).

The Shared Experiment Result Contract is the single result schema emitted by
all three Phase-3 experiment orchestrators of the SEA→canonical migration
(epic OMN-13604). No experiment node invents its own result schema; they all
import from here.

Callers should import concrete symbols from their modules directly, e.g.::

    from omnibase_core.models.experiment.model_experiment_result import (
        ModelExperimentResult,
    )
"""
